
"""
HOTSPOT - Etapa 11

Autocorrelacion espacial de residuos
del modelo binomial negativo ATUS-DENUE.

Salidas:
11_residuos_municipales_nb2.csv
11_moran_global_atus_nb2.csv
11_moran_permutaciones.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd


# ============================================
# 1. RUTAS Y PARAMETROS
# ============================================

RAIZ = Path(__file__).resolve().parent.parent
PROCESADA = RAIZ / "Data Procesada"

N_PERMUTACIONES = 1999
SEMILLA = 20261111


def leer_csv(nombre, **opciones):

    ruta = PROCESADA / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe: {ruta}\n"
            "Si falta la adyacencia, ejecuta "
            "08_construir_grafo.py primero."
        )

    return pd.read_csv(
        ruta,
        encoding="utf-8-sig",
        **opciones
    )


# ============================================
# 2. LEER MATRIZ DE ADYACENCIA
# ============================================

A = leer_csv(
    "08_matriz_adyacencia.csv",
    index_col=0
)

A.index = A.index.map(str)
A.columns = A.columns.map(str)

if (
    not A.index.is_unique
    or not A.columns.is_unique
):
    raise ValueError(
        "Hay claves municipales repetidas."
    )

if set(A.index) != set(A.columns):
    raise ValueError(
        "Filas y columnas no coinciden."
    )

A = A.loc[A.index, A.index].astype(float)

M = A.to_numpy()

if not np.isfinite(M).all():
    raise ValueError(
        "La adyacencia tiene valores no finitos."
    )

if not np.isin(M, [0.0, 1.0]).all():
    raise ValueError(
        "La adyacencia no es binaria."
    )

if not np.allclose(M, M.T):
    raise ValueError(
        "La matriz no es simetrica."
    )

if not np.allclose(np.diag(M), 0):
    raise ValueError(
        "La diagonal debe ser cero."
    )


# ============================================
# 3. LEER RESULTADOS ATUS-DENUE
# ============================================

municipios = leer_csv(
    "10_atus_denue_2025.csv",
    dtype={"cvegeo": "string"}
)

municipios["cvegeo"] = (
    municipios["cvegeo"].str.strip()
)

if (
    municipios["cvegeo"].isna().any()
    or municipios["cvegeo"].duplicated().any()
):
    raise ValueError(
        "Claves vacias o duplicadas."
    )

claves = municipios["cvegeo"].tolist()

faltantes = sorted(
    set(claves) - set(A.index)
)

if faltantes:
    raise ValueError(
        f"Claves sin geometria: {faltantes}"
    )


# ============================================
# 4. RECUPERAR ALPHA DE NB2
# ============================================

coef = leer_csv(
    "10_coeficientes_modelos.csv"
)

filtro = (
    (
        coef["analisis"]
        == "atus_denue_municipal_2025"
    )
    & (
        coef["modelo"]
        == "Binomial_negativa_NB2"
    )
    & (coef["variable"] == "alpha")
)

seleccion = coef.loc[filtro, "beta"]

if len(seleccion) != 1:
    raise ValueError(
        "No se encontro un unico alpha NB2."
    )

alpha = float(seleccion.iloc[0])

if not np.isfinite(alpha) or alpha < 0:
    raise ValueError(
        "El parametro alpha no es valido."
    )


# ============================================
# 5. CALCULAR RESIDUOS NB2
# ============================================

y = pd.to_numeric(
    municipios["registros_atus_2025"],
    errors="coerce"
).to_numpy(float)

mu = pd.to_numeric(
    municipios["esperado_nb2"],
    errors="coerce"
).to_numpy(float)

if (
    not np.isfinite(y).all()
    or not np.isfinite(mu).all()
    or (y < 0).any()
    or (mu <= 0).any()
):
    raise ValueError(
        "Conteos o predicciones invalidas."
    )

# Varianza condicional NB2.
varianza_nb2 = (
    mu + alpha * mu**2
)

# Residuo Pearson apropiado para NB2.
residuos = (
    (y - mu) / np.sqrt(varianza_nb2)
)

municipios["residuo_pearson_nb2"] = residuos


# ============================================
# 6. SUBGRAFO DE MUNICIPIOS CON ATUS
# ============================================

# Solo utilizamos las claves municipales
# presentes en nuestro modelo ATUS-DENUE.

W_todos = A.loc[
    claves, claves
].to_numpy(dtype=float)

grados = W_todos.sum(axis=1)

municipios["vecinos_con_atus"] = (
    grados.astype(int)
)

municipios["aislado_en_subgrafo"] = (
    grados == 0
)

# Los municipios sin vecinos observados
# se conservan en el reporte,
# pero no participan en Moran.

indices = np.flatnonzero(grados > 0)

if len(indices) < 4:
    raise ValueError(
        "No hay suficientes municipios "
        "con vecinos observados."
    )

W = W_todos[np.ix_(
    indices, indices
)]

r = residuos[indices]

n = len(r)
S0 = W.sum()

if S0 <= 0:
    raise ValueError(
        "El subgrafo no tiene aristas."
    )


# ============================================
# 7. CALCULAR I DE MORAN
# ============================================

z = r - r.mean()

denominador = float(z @ z)

if denominador <= 1e-12:
    raise ValueError(
        "Los residuos tienen varianza "
        "insuficiente para Moran."
    )


def moran(zvalores):

    numerador = (
        zvalores @ W @ zvalores
    )

    denominador = (
        zvalores @ zvalores
    )

    return float(
        (n / S0)
        * (numerador / denominador)
    )


I_observada = moran(z)


# ============================================
# 8. PRUEBA DE PERMUTACIONES
# ============================================

generador = np.random.default_rng(
    SEMILLA
)

I_permutadas = np.empty(
    N_PERMUTACIONES,
    dtype=float
)

for k in range(N_PERMUTACIONES):

    z_aleatorio = (
        generador.permutation(z)
    )

    I_permutadas[k] = moran(
        z_aleatorio
    )

centro_nulo = float(
    I_permutadas.mean()
)

# Contraste exploratorio de agrupamiento
# espacial positivo.
p_positivo = (
    1 + np.count_nonzero(
        I_permutadas >= I_observada
    )
) / (N_PERMUTACIONES + 1)

# Contraste bilateral centrado en
# la media de las permutaciones.
p_bilateral = (
    1 + np.count_nonzero(
        np.abs(I_permutadas - centro_nulo)
        >= abs(I_observada - centro_nulo)
    )
) / (N_PERMUTACIONES + 1)


# ============================================
# 9. EXPORTAR RESULTADOS
# ============================================

municipios.to_csv(
    PROCESADA
    / "11_residuos_municipales_nb2.csv",
    index=False,
    encoding="utf-8-sig"
)

resumen = pd.DataFrame([{
    "analisis": "atus_denue_municipal_2025",
    "modelo": "Binomial_negativa_NB2",
    "n_municipios_con_atus": len(municipios),
    "n_utilizados_moran": n,
    "n_aislados": int(
        (grados == 0).sum()
    ),
    "aristas_subgrafo": int(S0 / 2),
    "alpha_nb2": alpha,
    "I_moran": I_observada,
    "media_permutaciones": centro_nulo,
    "p_agrupamiento_positivo": p_positivo,
    "p_bilateral_exploratorio": p_bilateral,
    "n_permutaciones": N_PERMUTACIONES,
    "semilla": SEMILLA
}])

resumen.to_csv(
    PROCESADA
    / "11_moran_global_atus_nb2.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame({
    "permutacion": np.arange(
        1, N_PERMUTACIONES + 1
    ),
    "I_moran_simulada": I_permutadas
}).to_csv(
    PROCESADA
    / "11_moran_permutaciones.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 10. MOSTRAR RESULTADOS
# ============================================

print(
    "\n=== ETAPA 11: "
    "AUTOCORRELACION ESPACIAL ==="
)

print(
    "Municipios con ATUS:",
    len(municipios)
)

print(
    "Municipios incluidos en Moran:",
    n
)

print(
    "Municipios aislados:",
    int((grados == 0).sum())
)

print(
    "Aristas del subgrafo:",
    int(S0 / 2)
)

print(
    "Alpha NB2:",
    round(alpha, 6)
)

print(
    "I de Moran:",
    round(I_observada, 6)
)

print(
    "Media de permutaciones:",
    round(centro_nulo, 6)
)

print(
    "p agrupamiento positivo:",
    round(p_positivo, 6)
)

print(
    "p bilateral exploratorio:",
    round(p_bilateral, 6)
)

print(
    "\nArchivos 11_*.csv "
    "creados en Data Procesada."
)

print(
    "AVISO: la prueba es exploratoria "
    "y no establece causalidad."
)
