
"""
HOTSPOT - ETAPA 13
Analisis espectral del grafo municipal.

Entradas:
    08_matriz_adyacencia.csv
    07_matriz_municipal_geografica.csv

Salidas:
    13_autovalores_laplaciano.csv
    13_embedding_espectral.csv
    13_energia_espectral_denue.csv
    13_resumen_espectral.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

# ==========================================
# 1. CONFIGURACION
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent
PROCESADA = RAIZ / "Data Procesada"

TAU = 0.75
TOL = 1e-8


def leer_csv(nombre, **kwargs):

    ruta = PROCESADA / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe {ruta}. "
            "Ejecuta los scripts previos."
        )

    return pd.read_csv(
        ruta,
        encoding="utf-8-sig",
        **kwargs
    )


# ==========================================
# 2. LEER MATRICES Y MUNICIPIOS
# ==========================================

adyacencia = leer_csv(
    "08_matriz_adyacencia.csv",
    index_col=0
)

adyacencia.index = adyacencia.index.map(str)
adyacencia.columns = adyacencia.columns.map(str)

municipios = leer_csv(
    "07_matriz_municipal_geografica.csv",
    dtype={"cvegeo": "string"}
)

municipios["cvegeo"] = (
    municipios["cvegeo"].str.strip()
)

municipios = (
    municipios.sort_values("cvegeo")
    .reset_index(drop=True)
)

claves = municipios["cvegeo"].tolist()

if len(claves) != 125 or len(set(claves)) != 125:
    raise ValueError(
        "Se esperaban 125 municipios unicos."
    )

if (
    adyacencia.index.has_duplicates
    or adyacencia.columns.has_duplicates
    or set(adyacencia.index) != set(claves)
    or set(adyacencia.columns) != set(claves)
):
    raise ValueError(
        "Las claves municipales no coinciden."
    )

A = adyacencia.loc[
    claves, claves
].to_numpy(dtype=float)

if (
    not np.isfinite(A).all()
    or not np.allclose(A, A.T)
    or not np.all(np.isin(A, [0.0, 1.0]))
    or not np.allclose(np.diag(A), 0)
):
    raise ValueError(
        "La adyacencia no es valida."
    )


# ==========================================
# 3. CONSTRUIR LAPLACIANO
# ==========================================

grados = A.sum(axis=1)

D = np.diag(grados)

L = D - A


# ==========================================
# 4. DESCOMPOSICION ESPECTRAL
# ==========================================

autovalores, U = np.linalg.eigh(L)

orden = np.argsort(autovalores)

autovalores = autovalores[orden]
U = U[:, orden]


# ==========================================
# 5. VALIDAR MATEMATICA
# ==========================================

error_filas = np.max(
    np.abs(L.sum(axis=1))
)

error_ortogonalidad = np.max(
    np.abs(
        U.T @ U - np.eye(len(claves))
    )
)

error_autopares = np.max(
    np.abs(
        L @ U - U * autovalores
    )
)

ceros = int(
    np.count_nonzero(
        np.abs(autovalores) < TOL
    )
)

if (
    error_filas > 1e-8
    or error_ortogonalidad > 1e-8
    or error_autopares > 1e-7
    or ceros != 1
):
    raise ValueError(
        "Fallo la validacion espectral."
    )


# ==========================================
# 6. COORDENADAS ESPECTRALES
# ==========================================

# El primer autovector es constante.
# Utilizamos el segundo, tercero y cuarto.

coordenadas = U[:, 1:4].copy()

for j in range(coordenadas.shape[1]):

    i_ref = int(
        np.argmax(
            np.abs(coordenadas[:, j])
        )
    )

    # Fijar una orientacion reproducible.
    if coordenadas[i_ref, j] < 0:
        coordenadas[:, j] *= -1


# ==========================================
# 7. INCORPORAR DENUE
# ==========================================

denue = pd.to_numeric(
    municipios[
        "establecimientos_denue_mayo_2025"
    ],
    errors="coerce"
).to_numpy(float)

area = pd.to_numeric(
    municipios["area_km2"],
    errors="coerce"
).to_numpy(float)

if (
    not np.isfinite(denue).all()
    or not np.isfinite(area).all()
    or (denue < 0).any()
    or (area <= 0).any()
):
    raise ValueError(
        "DENUE o superficies invalidas."
    )

# Establecimientos por km2.
densidad = denue / area

# Transformacion logaritmica.
senal = np.log1p(densidad)


# ==========================================
# 8. ENERGIA ESPECTRAL
# ==========================================

energia_original = float(
    senal @ L @ senal
)

coef_espectrales = U.T @ senal

energia_modos = (
    autovalores
    * coef_espectrales**2
)

energia_reconstruida = float(
    energia_modos.sum()
)

if not np.isclose(
    energia_original,
    energia_reconstruida,
    rtol=1e-7,
    atol=1e-7
):
    raise ValueError(
        "No coincide la energia espectral."
    )


# ==========================================
# 9. DIFUSION MEDIANTE KERNEL DE CALOR
# ==========================================

factores_calor = np.exp(
    -TAU * np.maximum(autovalores, 0)
)

senal_suavizada = (
    U @ (
        factores_calor
        * coef_espectrales
    )
)


# ==========================================
# 10. EXPORTAR AUTOVALORES
# ==========================================

pd.DataFrame({
    "modo": np.arange(
        1, len(claves) + 1
    ),
    "autovalor": autovalores
}).to_csv(
    PROCESADA
    / "13_autovalores_laplaciano.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 11. EXPORTAR EMBEDDING
# ==========================================

embedding = municipios[[
    "cvegeo",
    "municipio_cartografia",
    "region_iieg",
    "area_km2",
    "establecimientos_denue_mayo_2025",
    "registros_atus_2025"
]].copy()

embedding["grado_vecindad"] = (
    grados.astype(int)
)

embedding["espectral_x"] = (
    coordenadas[:, 0]
)

embedding["espectral_y"] = (
    coordenadas[:, 1]
)

embedding["espectral_z"] = (
    coordenadas[:, 2]
)

embedding["denue_por_km2"] = densidad

embedding["log1p_denue_por_km2"] = senal

embedding["log1p_denue_suavizado"] = (
    senal_suavizada
)

embedding.to_csv(
    PROCESADA
    / "13_embedding_espectral.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 12. EXPORTAR ENERGIA POR MODO
# ==========================================

pd.DataFrame({
    "modo": np.arange(
        1, len(claves) + 1
    ),
    "autovalor": autovalores,
    "energia_modo_denue": energia_modos
}).to_csv(
    PROCESADA
    / "13_energia_espectral_denue.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 13. EXPORTAR RESUMEN
# ==========================================

resumen = pd.DataFrame([{
    "n_municipios": len(claves),
    "n_aristas": int(A.sum() / 2),
    "componentes_conexas_espectrales": ceros,
    "lambda_2_conectividad_algebraica":
        float(autovalores[1]),
    "lambda_3": float(autovalores[2]),
    "lambda_4": float(autovalores[3]),
    "error_filas_laplaciano":
        float(error_filas),
    "error_ortogonalidad":
        float(error_ortogonalidad),
    "error_autopares":
        float(error_autopares),
    "energia_denue": energia_original,
    "energia_espectral_reconstruida":
        energia_reconstruida,
    "tau_difusion_ejemplo": TAU
}])

resumen.to_csv(
    PROCESADA
    / "13_resumen_espectral.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 14. MOSTRAR RESULTADOS
# ==========================================

print(
    "\n=== ETAPA 13: "
    "ANALISIS ESPECTRAL HOTSPOT ==="
)

print("Nodos:", len(claves))
print("Aristas:", int(A.sum() / 2))

print(
    "Componentes conexas:",
    ceros
)

print(
    "Lambda 2:",
    round(
        float(autovalores[1]), 8
    )
)

print(
    "Lambda 3:",
    round(
        float(autovalores[2]), 8
    )
)

print(
    "Lambda 4:",
    round(
        float(autovalores[3]), 8
    )
)

print(
    "Error maximo autovectores:",
    f"{error_autopares:.3e}"
)

print(
    "Energia territorial DENUE:",
    round(energia_original, 6)
)

print(
    "\nArchivos 13_*.csv guardados "
    "en Data Procesada."
)

print(
    "AVISO: embedding y suavizado "
    "no son estimaciones de riesgo."
)
