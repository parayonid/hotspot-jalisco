
"""
HOTSPOT - 08_construir_grafo.py

Construye un grafo municipal de Jalisco
mediante fronteras compartidas.

Salidas:
    08_aristas_municipales.csv
    08_matriz_adyacencia.csv
    08_matriz_laplaciana.csv
    08_nodos_municipales.csv
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
from shapely import wkb


# ==========================================
# 1. RUTAS
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent

CRUDA = RAIZ / "Data Cruda"
PROCESADA = RAIZ / "Data Procesada"

archivos = list(
    CRUDA.rglob("limite_municipal_jalisco_iieg.gpkg")
)

if len(archivos) != 1:
    raise FileNotFoundError(
        "Se esperaba exactamente un GeoPackage."
    )

RUTA_GPKG = archivos[0]

RUTA_ESTADISTICA = (
    PROCESADA / "07_matriz_municipal_geografica.csv"
)


# ==========================================
# 2. DECODIFICAR GEOMETRIA GEOPACKAGE
# ==========================================

def leer_geometria_gpkg(blob):
    """
    Un GeoPackage almacena las geometrias
    como una cabecera GPKG seguida de WKB.

    Esta funcion separa ambos elementos.
    """

    if blob is None or len(blob) < 9:
        raise ValueError("Geometria vacia o incompleta")

    if bytes(blob[:2]) != b"GP":
        raise ValueError("Cabecera GeoPackage invalida")

    flags = blob[3]

    # Bits 1-3: tipo de envolvente espacial.
    tipo_envolvente = (flags >> 1) & 7

    tamanios = {
        0: 0,
        1: 32,
        2: 48,
        3: 48,
        4: 64,
    }

    if tipo_envolvente not in tamanios:
        raise ValueError(
            "Tipo de envolvente no reconocido"
        )

    inicio_wkb = 8 + tamanios[tipo_envolvente]

    return wkb.loads(
        bytes(blob[inicio_wkb:])
    )


# ==========================================
# 3. LEER POLIGONOS MUNICIPALES
# ==========================================

with sqlite3.connect(str(RUTA_GPKG)) as conexion:

    registros = conexion.execute("""
        SELECT clave_geo, nombre, geom
        FROM limite_municipal
        ORDER BY clave_geo
    """).fetchall()

    srs = conexion.execute("""
        SELECT srs_id
        FROM gpkg_geometry_columns
        WHERE table_name = 'limite_municipal'
    """).fetchone()[0]


claves = []
nombres = []
geometrias = []

for clave, nombre, blob in registros:

    geometria = leer_geometria_gpkg(blob)

    if geometria.is_empty:
        raise ValueError(
            f"Geometria vacia: {clave}"
        )

    if not geometria.is_valid:
        raise ValueError(
            f"Geometria invalida: {clave}"
        )

    claves.append(str(clave).strip())
    nombres.append(nombre)
    geometrias.append(geometria)


# ==========================================
# 4. VALIDAR MUNICIPIOS
# ==========================================

estadisticas = pd.read_csv(
    RUTA_ESTADISTICA,
    dtype={"cvegeo": "string"}
)

if len(set(claves)) != len(claves):
    raise ValueError("Claves duplicadas en cartografia")

if len(registros) != 125:
    raise ValueError(
        f"Se esperaban 125 municipios, hay {len(registros)}"
    )

if set(claves) != set(estadisticas["cvegeo"]):
    raise ValueError(
        "Las claves no coinciden con la matriz 07"
    )

print("\n=== GRAFO DE JALISCO ===")
print("Municipios:", len(claves))
print("Sistema de referencia:", srs)


# ==========================================
# 5. CONSTRUIR MATRIZ DE ADYACENCIA
# ==========================================

n = len(claves)

A = np.zeros(
    (n, n),
    dtype=int
)

aristas = []

# Calculamos anticipadamente las fronteras.
fronteras = [
    geom.boundary for geom in geometrias
]

# Cajas envolventes para descartar
# pares de municipios muy alejados.
cajas = [
    geom.bounds for geom in geometrias
]

for i in range(n):

    for j in range(i + 1, n):

        x1_min, y1_min, x1_max, y1_max = cajas[i]
        x2_min, y2_min, x2_max, y2_max = cajas[j]

        # Si las cajas no se intersectan,
        # los municipios no comparten frontera.
        separadas = (
            x1_max < x2_min
            or x2_max < x1_min
            or y1_max < y2_min
            or y2_max < y1_min
        )

        if separadas:
            continue

        frontera_compartida = (
            fronteras[i].intersection(fronteras[j])
        )

        # Rook: compartir un tramo de frontera.
        if frontera_compartida.length > 0:

            A[i, j] = 1
            A[j, i] = 1

            aristas.append({
                "cvegeo_origen": claves[i],
                "municipio_origen": nombres[i],
                "cvegeo_destino": claves[j],
                "municipio_destino": nombres[j]
            })


# ==========================================
# 6. CONSTRUIR LAPLACIANO
# ==========================================

grados = A.sum(axis=1)

D = np.diag(grados)

L = D - A


# ==========================================
# 7. VALIDACIONES MATEMATICAS
# ==========================================

# La matriz de adyacencia debe ser simetrica.
assert np.array_equal(A, A.T)

# Un municipio no es vecino de si mismo.
assert np.all(np.diag(A) == 0)

# El laplaciano tambien es simetrico.
assert np.array_equal(L, L.T)

# Cada fila del laplaciano suma cero.
assert np.all(L.sum(axis=1) == 0)


# ==========================================
# 8. IDENTIFICAR COMPONENTES CONEXAS
# ==========================================

visitados = set()
componentes = []

for inicio in range(n):

    if inicio in visitados:
        continue

    pila = [inicio]
    visitados.add(inicio)
    componente = []

    while pila:

        actual = pila.pop()
        componente.append(actual)

        vecinos = np.flatnonzero(
            A[actual]
        )

        for vecino in vecinos:

            vecino = int(vecino)

            if vecino not in visitados:
                visitados.add(vecino)
                pila.append(vecino)

    componentes.append(componente)


# ==========================================
# 9. EXPORTAR ARISTAS
# ==========================================

pd.DataFrame(
    aristas,
    columns=[
        "cvegeo_origen",
        "municipio_origen",
        "cvegeo_destino",
        "municipio_destino"
    ]
).to_csv(
    PROCESADA / "08_aristas_municipales.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 10. EXPORTAR MATRICES
# ==========================================

pd.DataFrame(
    A,
    index=claves,
    columns=claves
).to_csv(
    PROCESADA / "08_matriz_adyacencia.csv",
    encoding="utf-8-sig",
    index_label="cvegeo"
)

pd.DataFrame(
    L,
    index=claves,
    columns=claves
).to_csv(
    PROCESADA / "08_matriz_laplaciana.csv",
    encoding="utf-8-sig",
    index_label="cvegeo"
)


# ==========================================
# 11. ENRIQUECER NODOS CON ESTADISTICAS
# ==========================================

tabla_grados = pd.DataFrame({
    "cvegeo": pd.Series(claves, dtype="string"),
    "grado_vecindad": grados
})

nodos = estadisticas.merge(
    tabla_grados,
    on="cvegeo",
    how="inner",
    validate="one_to_one"
)

nodos.to_csv(
    PROCESADA / "08_nodos_municipales.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 12. RESULTADOS
# ==========================================

print("\n=== RESULTADOS DEL GRAFO ===")

print("Nodos:", n)
print("Aristas:", len(aristas))
print("Componentes conexas:", len(componentes))

print(
    "Municipios aislados:",
    int((grados == 0).sum())
)

print(
    "Grado promedio:",
    round(float(grados.mean()), 2)
)

print("\nMunicipios con mas vecinos:")

print(
    nodos[
        [
            "municipio_cartografia",
            "grado_vecindad"
        ]
    ]
    .sort_values(
        "grado_vecindad",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)

print("\nValidaciones matematicas correctas.")
print("Archivos guardados en Data Procesada.")
