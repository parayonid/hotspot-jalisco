
"""
HOTSPOT | ETAPA 15
Preparar los resultados cientificos para el frontend.

Entradas:
- Matriz municipal 2025
- Embedding espectral
- Matriz de adyacencia
- GeoPackage municipal
- GeoJSON de Siniestralimap
- Series de Seguridad
- Resultados estadisticos

Salidas en hotspot-mvp/datos:
- municipios.json
- municipios.geojson
- siniestros.geojson
- seguridad.json
- modelos.json
- grafo.json

No recalcula modelos ni inventa ubicaciones.
"""

# ============================================
# 1. IMPORTAR BIBLIOTECAS
# ============================================

from pathlib import Path
import json
import shutil
import sqlite3

import numpy as np
import pandas as pd

from shapely import wkb
from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer


# ============================================
# 2. CONFIGURAR RUTAS
# ============================================

RAIZ = Path(__file__).resolve().parent.parent

PROCESADA = RAIZ / "Data Procesada"
CRUDA = RAIZ / "Data Cruda"

SALIDA = Path(__file__).resolve().parent / "datos"

SALIDA.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================
# 3. FUNCIONES AUXILIARES
# ============================================

def leer_csv(nombre, **opciones):

    ruta = PROCESADA / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"Falta {ruta}. "
            "Ejecuta las etapas anteriores."
        )

    return pd.read_csv(
        ruta,
        encoding="utf-8-sig",
        **opciones
    )


def registros(tabla):
    """
    Convierte un DataFrame a registros JSON.

    Los valores faltantes de pandas
    se convierten en null.
    """

    contenido = tabla.to_json(
        orient="records",
        force_ascii=False,
        double_precision=15
    )

    return json.loads(contenido)


def guardar_json(nombre, contenido):

    ruta = SALIDA / nombre

    with ruta.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        )

    print(
        f"Generado: {ruta.name} "
        f"({ruta.stat().st_size:,} bytes)"
    )


# ============================================
# 4. LEER LA MATRIZ MUNICIPAL
# ============================================

municipios = leer_csv(
    "08_matriz_municipal_2025.csv",
    dtype={"cvegeo": "string"}
)

embedding = leer_csv(
    "13_embedding_espectral.csv",
    dtype={"cvegeo": "string"}
)

for tabla, nombre in [
    (municipios, "Matriz 08"),
    (embedding, "Embedding 13")
]:

    tabla["cvegeo"] = (
        tabla["cvegeo"].str.strip()
    )

    if (
        tabla["cvegeo"].isna().any()
        or tabla["cvegeo"].duplicated().any()
    ):
        raise ValueError(
            f"Claves invalidas: {nombre}"
        )

if (
    len(municipios) != 125
    or set(municipios.cvegeo)
    != set(embedding.cvegeo)
):
    raise ValueError(
        "Las etapas 08 y 13 deben contener "
        "los mismos 125 municipios."
    )


# ============================================
# 5. AGREGAR COORDENADAS ESPECTRALES
# ============================================

columnas_embedding = [
    "cvegeo",
    "espectral_x",
    "espectral_y",
    "espectral_z",
    "denue_por_km2",
    "log1p_denue_suavizado"
]

municipios = municipios.merge(
    embedding[columnas_embedding],
    on="cvegeo",
    how="left",
    validate="one_to_one"
)

municipios = (
    municipios
    .sort_values("cvegeo")
    .reset_index(drop=True)
)

claves = municipios["cvegeo"].tolist()

columnas_necesarias = [
    "registros_atus_2025",
    "siniestros_registrados_2025",
    "establecimientos_denue_mayo_2025"
]

for columna in columnas_necesarias:

    if columna not in municipios.columns:
        raise ValueError(
            f"Falta la columna: {columna}"
        )


# ============================================
# 6. LOCALIZAR EL GEOPACKAGE
# ============================================

coincidencias = list(
    CRUDA.rglob(
        "limite_municipal_jalisco_iieg.gpkg"
    )
)

if len(coincidencias) != 1:
    raise FileNotFoundError(
        "Se esperaba exactamente un "
        "GeoPackage municipal."
    )


# ============================================
# 7. DECODIFICAR GEOMETRIAS
# ============================================

def decodificar_gpkg(blob):

    if (
        blob is None
        or len(blob) < 9
        or bytes(blob[:2]) != b"GP"
    ):
        raise ValueError(
            "Geometria GeoPackage invalida."
        )

    tipo_envolvente = (
        blob[3] >> 1
    ) & 7

    tamanios = {
        0: 0,
        1: 32,
        2: 48,
        3: 48,
        4: 64
    }

    if tipo_envolvente not in tamanios:
        raise ValueError(
            "Envolvente desconocida."
        )

    inicio = (
        8 + tamanios[tipo_envolvente]
    )

    return wkb.loads(
        bytes(blob[inicio:])
    )


# ============================================
# 8. LEER MUNICIPIOS DESDE SQLITE
# ============================================

with sqlite3.connect(
    coincidencias[0]
) as conexion:

    fila_srs = conexion.execute("""
        SELECT srs_id
        FROM gpkg_geometry_columns
        WHERE table_name = 'limite_municipal'
    """).fetchone()

    if fila_srs is None:
        raise ValueError(
            "No se encontro el sistema "
            "de referencia."
        )

    srs_id = int(fila_srs[0])

    geometrias_gpkg = conexion.execute("""
        SELECT clave_geo, geom
        FROM limite_municipal
    """).fetchall()


# ============================================
# 9. TRANSFORMAR COORDENADAS A WGS84
# ============================================

# El GeoPackage original usa EPSG:6368.
# Los mapas web utilizan longitud/latitud.

convertidor = Transformer.from_crs(
    f"EPSG:{srs_id}",
    "EPSG:4326",
    always_xy=True
)

formas = {}
puntos = {}

for clave, blob in geometrias_gpkg:

    clave = str(clave).strip()

    geom_original = decodificar_gpkg(
        blob
    )

    if (
        geom_original.is_empty
        or not geom_original.is_valid
    ):
        raise ValueError(
            f"Poligono invalido: {clave}"
        )

    geom_wgs84 = transform(
        convertidor.transform,
        geom_original
    )

    punto = (
        geom_wgs84.representative_point()
    )

    if not (
        -106 <= punto.x <= -101
        and 18 <= punto.y <= 23
    ):
        raise ValueError(
            f"Coordenada fuera de Jalisco: {clave}"
        )

    if clave in formas:
        raise ValueError(
            f"Municipio repetido: {clave}"
        )

    formas[clave] = mapping(
        geom_wgs84
    )

    puntos[clave] = [
        round(punto.x, 7),
        round(punto.y, 7)
    ]


if set(formas) != set(claves):
    raise ValueError(
        "Las claves de cartografia "
        "no coinciden con la matriz."
    )


# ============================================
# 10. EXPORTAR MUNICIPIOS.JSON
# ============================================

municipios[
    "punto_referencia_lon"
] = [
    puntos[c][0] for c in claves
]

municipios[
    "punto_referencia_lat"
] = [
    puntos[c][1] for c in claves
]

mun_list = registros(municipios)

guardar_json(
    "municipios.json",
    {
        "meta": {
            "anio_atus": 2025,
            "corte_denue": "2025-05",
            "anio_siniestralimap": 2025,
            "n_municipios": len(claves),
            "crs_puntos": "EPSG:4326",
            "advertencia": (
                "ATUS faltante es null. "
                "Cero Siniestralimap significa "
                "cero registros asignados, "
                "no necesariamente cero accidentes."
            )
        },
        "municipios": mun_list
    }
)


# ============================================
# 11. EXPORTAR POLIGONOS GEOJSON
# ============================================

propiedades = {
    m["cvegeo"]: m
    for m in mun_list
}

features = []

for clave in claves:

    m = propiedades[clave]

    features.append({
        "type": "Feature",
        "id": clave,
        "geometry": formas[clave],
        "properties": {
            "cvegeo": clave,
            "nombre": m[
                "municipio_cartografia"
            ],
            "region_iieg": m[
                "region_iieg"
            ],
            "atus_2025": m[
                "registros_atus_2025"
            ],
            "denue_mayo_2025": m[
                "establecimientos_denue_mayo_2025"
            ],
            "siniestralimap_asignados_2025": m[
                "siniestros_registrados_2025"
            ]
        }
    })

guardar_json(
    "municipios.geojson",
    {
        "type": "FeatureCollection",
        "features": features
    }
)


# ============================================
# 12. EXPORTAR SINIESTRALIMAP
# ============================================

ruta_puntos = (
    PROCESADA
    / "03_siniestros_puntos.geojson"
)

if not ruta_puntos.is_file():
    raise FileNotFoundError(
        f"Falta {ruta_puntos}"
    )

with ruta_puntos.open(
    "r",
    encoding="utf-8"
) as archivo:

    puntos_siniestros = json.load(
        archivo
    )

if (
    puntos_siniestros.get("type")
    != "FeatureCollection"
):
    raise ValueError(
        "GeoJSON de Siniestralimap invalido."
    )

# Se conserva el historial 2015-2025,
# no solamente el corte de 2025.

shutil.copyfile(
    ruta_puntos,
    SALIDA / "siniestros.geojson"
)

print(
    "Generado: siniestros.geojson",
    f"({len(puntos_siniestros['features']):,} puntos)"
)


# ============================================
# 13. EXPORTAR SEGURIDAD
# ============================================

seguridad = leer_csv(
    "05_seguridad_controlada.csv"
)

columnas_seguridad = [
    "region",
    "periodo",
    "delito",
    "medida",
    "cantidad",
    "control_regional",
    "es_resumen"
]

if not set(columnas_seguridad).issubset(
    seguridad.columns
):
    raise ValueError(
        "Faltan columnas del control "
        "de calidad de Seguridad."
    )

if seguridad.duplicated([
    "region",
    "periodo",
    "delito",
    "medida"
]).any():
    raise ValueError(
        "Hay indicadores regionales duplicados."
    )

seguridad["cantidad"] = pd.to_numeric(
    seguridad["cantidad"],
    errors="raise"
)

seguridad["es_resumen"] = (
    seguridad["es_resumen"]
    .astype("string")
    .str.lower()
    .isin(["true", "1"])
)

guardar_json(
    "seguridad.json",
    {
        "meta": {
            "escala": "regional y mensual",
            "regiones": [
                "ESTADO",
                "AMG",
                "INTERIOR"
            ],
            "advertencia": (
                "No contiene ubicaciones "
                "individuales de delitos. "
                "No sumar totales y categorias "
                "que se superponen."
            )
        },
        "registros": registros(
            seguridad[columnas_seguridad]
        )
    }
)


# ============================================
# 14. RECUPERAR MATRIZ DE ADYACENCIA
# ============================================

matriz = leer_csv(
    "08_matriz_adyacencia.csv",
    index_col=0
)

matriz.index = matriz.index.map(str)
matriz.columns = matriz.columns.map(str)

if (
    set(matriz.index) != set(claves)
    or set(matriz.columns) != set(claves)
):
    raise ValueError(
        "Las claves de adyacencia "
        "no coinciden."
    )

A = matriz.loc[
    claves,
    claves
].to_numpy(dtype=float)

if (
    not np.isfinite(A).all()
    or not np.allclose(A, A.T)
    or not np.isin(A, [0, 1]).all()
    or not np.allclose(np.diag(A), 0)
):
    raise ValueError(
        "Matriz de adyacencia invalida."
    )

indices_i, indices_j = np.where(
    np.triu(A, k=1) == 1
)


# ============================================
# 15. EXPORTAR GRAFO.JSON
# ============================================

grafo_nodos = []

for i, m in enumerate(mun_list):

    clave = m["cvegeo"]

    grafo_nodos.append({
        "id": clave,
        "nombre": m[
            "municipio_cartografia"
        ],
        "geografico_lonlat": puntos[clave],
        "espectral_xyz": [
            m["espectral_x"],
            m["espectral_y"],
            m["espectral_z"]
        ],
        "grado": int(A[i].sum())
    })


grafo_aristas = [
    {
        "source": claves[int(i)],
        "target": claves[int(j)]
    }
    for i, j in zip(
        indices_i,
        indices_j
    )
]

guardar_json(
    "grafo.json",
    {
        "meta": {
            "nodos": len(grafo_nodos),
            "aristas": len(grafo_aristas),
            "tipo": (
                "vecindad por frontera compartida"
            ),
            "geografico_crs": "EPSG:4326"
        },
        "nodos": grafo_nodos,
        "aristas": grafo_aristas
    }
)


# ============================================
# 16. EXPORTAR MODELOS ESTADISTICOS
# ============================================

diagnosticos = registros(
    leer_csv(
        "10_diagnosticos_modelos.csv"
    )
)

coeficientes = registros(
    leer_csv(
        "10_coeficientes_modelos.csv"
    )
)

moran = registros(
    leer_csv(
        "11_moran_global_atus_nb2.csv"
    )
)

espectral = registros(
    leer_csv(
        "13_resumen_espectral.csv"
    )
)

energia = registros(
    leer_csv(
        "14_resumen_energia_denue.csv"
    )
)

guardar_json(
    "modelos.json",
    {
        "meta": {
            "interpretacion": (
                "Resultados exploratorios, "
                "no indicadores de riesgo "
                "validados ni evidencia causal."
            ),
            "precauciones": [
                (
                    "Siniestralimap presenta "
                    "cobertura territorial limitada."
                ),
                (
                    "ATUS tiene municipios "
                    "sin registros disponibles."
                ),
                (
                    "El modelo temporal de homicidios "
                    "presenta autocorrelacion residual."
                )
            ]
        },
        "diagnosticos": diagnosticos,
        "coeficientes": coeficientes,
        "moran_atus": moran,
        "analisis_espectral": espectral,
        "energia_denue": energia
    }
)


# ============================================
# 17. RESULTADOS FINALES
# ============================================

print(
    "\n=== ETAPA 15: "
    "DATOS PARA FRONTEND ==="
)

print(
    "Municipios:",
    len(mun_list)
)

print(
    "Aristas:",
    len(grafo_aristas)
)

print(
    "Siniestros georreferenciados:",
    len(puntos_siniestros["features"])
)

print(
    "Observaciones de Seguridad:",
    len(seguridad)
)

print(
    "Carpeta:",
    SALIDA
)

print(
    "\nAVISO: No se modificaron los "
    "datos cientificos originales."
)
