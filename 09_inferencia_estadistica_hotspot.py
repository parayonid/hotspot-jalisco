
"""
HOTSPOT - 09_inferencia_estadistica_hotspot.py

Objetivo:
Realizar inferencia estadistica utilizando
las cuatro fuentes de datos de Hotspot.

Fuentes:
    ATUS
    DENUE
    Siniestralimap
    Plataforma de Seguridad

Analisis:
    1. Auditoria de siniestros
    2. Correlaciones de Spearman
    3. Regresion de Poisson municipal
    4. Binomial negativa municipal
    5. Regresion temporal de criminalidad
    6. Diagnosticos estadisticos

Salidas:
    09_correlaciones.csv
    09_modelos_diagnosticos.csv
    09_modelos_coeficientes.csv
    09_predicciones_municipales.csv
    09_predicciones_seguridad.csv
"""

# ============================================
# 1. IMPORTAR BIBLIOTECAS
# ============================================

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy.stats import spearmanr

from statsmodels.discrete.discrete_model import (
    NegativeBinomial
)

from statsmodels.stats.diagnostic import (
    acorr_ljungbox
)


# ============================================
# 2. CONFIGURAR RUTAS
# ============================================

RAIZ = Path(__file__).resolve().parent.parent

PROCESADA = RAIZ / "Data Procesada"


# ============================================
# 3. FUNCION PARA LEER ARCHIVOS
# ============================================

def leer(nombre, **kwargs):

    ruta = PROCESADA / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"Falta el archivo: {ruta}. "
            "Ejecuta las etapas anteriores."
        )

    return pd.read_csv(
        ruta,
        encoding="utf-8-sig",
        **kwargs
    )


# ============================================
# 4. VALIDAR CONTEOS
# ============================================

def validar_conteos(datos, columnas):

    for columna in columnas:

        valores = pd.to_numeric(
            datos[columna],
            errors="coerce"
        )

        # Un conteo debe ser:
        # numerico, entero y no negativo.
        invalidos = (
            valores.isna()
            | (valores < 0)
            | (valores != np.floor(valores))
        )

        if invalidos.any():
            raise ValueError(
                f"Conteos invalidos en {columna}"
            )

        datos[columna] = valores.astype(int)


# ============================================
# 5. FUNCION PARA AJUSTAR MODELOS
# ============================================

def ajustar(
    nombre,
    y,
    X,
    coeficientes,
    diagnosticos
):

    # ----------------------------------------
    # A. REGRESION DE POISSON
    # ----------------------------------------

    poisson = sm.GLM(
        y,
        X,
        family=sm.families.Poisson()
    ).fit(
        cov_type="HC0"
    )

    # Conteos esperados segun Poisson.
    mu = np.asarray(
        poisson.predict(X),
        dtype=float
    )

    # ----------------------------------------
    # B. DISPERSION DE PEARSON
    # ----------------------------------------

    dispersion = float(
        np.sum(
            (np.asarray(y) - mu) ** 2
            / np.maximum(mu, 1e-8)
        )
        / poisson.df_resid
    )

    diagnosticos.append({
        "analisis": nombre,
        "modelo": "Poisson_HC0",
        "n": len(y),
        "aic": float(poisson.aic),
        "dispersion_pearson": dispersion,
        "convergencia": True
    })

    # ----------------------------------------
    # C. COEFICIENTES E INTERVALOS
    # ----------------------------------------

    for variable in X.columns:

        intervalo = (
            poisson.conf_int()
            .loc[variable]
        )

        coeficientes.append({
            "analisis": nombre,
            "modelo": "Poisson_HC0",
            "variable": variable,
            "beta": float(
                poisson.params[variable]
            ),
            "error_estandar": float(
                poisson.bse[variable]
            ),
            "p_valor": float(
                poisson.pvalues[variable]
            ),
            "ic95_inferior": float(
                intervalo.iloc[0]
            ),
            "ic95_superior": float(
                intervalo.iloc[1]
            )
        })

    # ----------------------------------------
    # D. BINOMIAL NEGATIVA
    # ----------------------------------------

    try:

        with warnings.catch_warnings():

            warnings.simplefilter(
                "ignore",
                RuntimeWarning
            )

            nb = NegativeBinomial(
                y,
                X,
                loglike_method="nb2"
            ).fit(
                disp=False,
                maxiter=300
            )

        convergio = bool(
            nb.mle_retvals.get(
                "converged", False
            )
        )

        diagnosticos.append({
            "analisis": nombre,
            "modelo": "Binomial_negativa_NB2",
            "n": len(y),
            "aic": float(nb.aic),
            "dispersion_pearson": np.nan,
            "convergencia": convergio
        })

        if convergio:

            intervalos = nb.conf_int()

            # Incluye los coeficientes
            # de regresion y alpha.
            for variable in nb.params.index:

                intervalo = (
                    intervalos.loc[variable]
                )

                coeficientes.append({
                    "analisis": nombre,
                    "modelo": "Binomial_negativa_NB2",
                    "variable": variable,
                    "beta": float(
                        nb.params[variable]
                    ),
                    "error_estandar": float(
                        nb.bse[variable]
                    ),
                    "p_valor": float(
                        nb.pvalues[variable]
                    ),
                    "ic95_inferior": float(
                        intervalo.iloc[0]
                    ),
                    "ic95_superior": float(
                        intervalo.iloc[1]
                    )
                })

        else:
            print(
                f"ADVERTENCIA: NB2 no convergio "
                f"para {nombre}."
            )

    except (
        ValueError,
        ArithmeticError,
        np.linalg.LinAlgError
    ) as error:

        print(
            f"ADVERTENCIA: NB2 no pudo "
            f"ajustarse para {nombre}: {error}"
        )

    return poisson, mu, dispersion


# ============================================
# 6. LEER MATRIZ MUNICIPAL
# ============================================

municipal = leer(
    "08_matriz_municipal_2025.csv",
    dtype={"cvegeo": "string"}
)

if (
    len(municipal) != 125
    or municipal["cvegeo"].duplicated().any()
):
    raise ValueError(
        "Se esperan 125 municipios "
        "sin claves duplicadas."
    )


# ============================================
# 7. VALIDAR ATUS, DENUE Y SINIESTRALIMAP
# ============================================

validar_conteos(
    municipal,
    [
        "siniestros_registrados_2025",
        "establecimientos_denue_mayo_2025"
    ]
)

# ATUS puede tener valores faltantes.
# Debemos conservarlos como NA.

municipal["registros_atus_2025"] = (
    pd.to_numeric(
        municipal["registros_atus_2025"],
        errors="coerce"
    )
)

sin_asignar = leer(
    "08_siniestros_sin_asignar_2025.csv"
)

registrados = int(
    municipal[
        "siniestros_registrados_2025"
    ].sum()
)

no_asignados = len(sin_asignar)

print("\n=== AUDITORIA SINIESTRALIMAP 2025 ===")

print(
    "Asignados a municipio:",
    registrados
)

print(
    "Sin asignar:",
    no_asignados
)

print(
    "Total de eventos conservados:",
    registrados + no_asignados
)

print(
    "Municipios con dato ATUS:",
    municipal[
        "registros_atus_2025"
    ].notna().sum()
)


# ============================================
# 8. CORRELACIONES DE SPEARMAN
# ============================================

correlaciones = []

pares = [
    (
        "Siniestralimap_vs_DENUE",
        "siniestros_registrados_2025",
        "establecimientos_denue_mayo_2025"
    ),
    (
        "Siniestralimap_vs_ATUS",
        "siniestros_registrados_2025",
        "registros_atus_2025"
    )
]

for etiqueta, columna_a, columna_b in pares:

    # Eliminar pares con valores faltantes.
    muestra = municipal[
        [columna_a, columna_b]
    ].dropna()

    # Verificar que exista variabilidad.
    suficientes = (
        len(muestra) > 2
        and muestra[columna_a].nunique() > 1
        and muestra[columna_b].nunique() > 1
    )

    if suficientes:

        rho, p_valor = spearmanr(
            muestra[columna_a],
            muestra[columna_b]
        )

        correlaciones.append({
            "comparacion": etiqueta,
            "n": len(muestra),
            "rho_spearman": float(rho),
            "p_valor_exploratorio": float(p_valor)
        })

    else:

        print(
            f"No se puede calcular Spearman: "
            f"{etiqueta}"
        )


# ============================================
# 9. MODELO MUNICIPAL DE POISSON
# ============================================

# Variable dependiente:
# siniestros registrados en cada municipio.

y_municipal = municipal[
    "siniestros_registrados_2025"
].to_numpy(dtype=float)

# Variable explicativa:
# cantidad de establecimientos DENUE.

X_municipal = pd.DataFrame({
    "const": np.ones(
        len(municipal)
    ),
    "log1p_denue": np.log1p(
        municipal[
            "establecimientos_denue_mayo_2025"
        ].to_numpy(dtype=float)
    )
})

# Listas para guardar resultados.
coeficientes = []
diagnosticos = []

modelo_municipal, pred_municipal, dispersion_mun = (
    ajustar(
        "siniestralidad_municipal_2025",
        y_municipal,
        X_municipal,
        coeficientes,
        diagnosticos
    )
)

# ----------------------------------------
# RESIDUOS DEL MODELO MUNICIPAL
# ----------------------------------------

municipal["esperado_poisson"] = (
    pred_municipal
)

municipal["residuo_pearson"] = (
    y_municipal - pred_municipal
) / np.sqrt(
    np.maximum(
        pred_municipal,
        1e-8
    )
)


# ============================================
# 10. LEER DATOS DE SEGURIDAD
# ============================================

# Serie historica completa.
seguridad = leer(
    "05_seguridad_controlada.csv"
)

# Corte 2025 creado en la etapa 08.
corte_2025 = leer(
    "08_seguridad_region_mes_2025.csv"
)


# ============================================
# 11. VALIDAR EL CORTE DE SEGURIDAD
# ============================================

claves = [
    "region",
    "periodo",
    "delito",
    "medida"
]

comparacion = corte_2025[
    claves + ["cantidad"]
].merge(
    seguridad[
        claves + ["cantidad"]
    ],
    on=claves,
    how="outer",
    suffixes=(
        "_corte",
        "_fuente"
    ),
    validate="one_to_one",
    indicator=True
)

comparacion = comparacion[
    comparacion["periodo"]
    .astype("string")
    .str.startswith(
        "2025-",
        na=False
    )
]

if (
    (comparacion["_merge"] != "both").any()
    or not (
        comparacion["cantidad_corte"]
        == comparacion["cantidad_fuente"]
    ).all()
):
    raise ValueError(
        "El corte 2025 no coincide con "
        "la serie original de Seguridad."
    )


# ============================================
# 12. SELECCIONAR INDICADOR DELICTIVO
# ============================================

# Primer experimento:
# Homicidio doloso estatal, medido en eventos.

selector = (
    (seguridad["region"] == "ESTADO")
    & (
        seguridad["delito"]
        == "HOMICIDIO DOLOSO"
    )
    & (
        seguridad["medida"]
        == "EVENTOS"
    )
)

serie = seguridad.loc[
    selector
].copy()

if (
    serie.empty
    or serie["periodo"].duplicated().any()
):
    raise ValueError(
        "Serie de homicidio doloso "
        "ausente o duplicada."
    )


# ============================================
# 13. PREPARAR SERIE TEMPORAL
# ============================================

serie["fecha"] = pd.to_datetime(
    serie["periodo"] + "-01",
    format="%Y-%m-%d"
)

serie = (
    serie.sort_values("fecha")
    .reset_index(drop=True)
)

validar_conteos(
    serie,
    ["cantidad"]
)

# Verificar que no falten meses.
esperados = pd.period_range(
    serie["fecha"].min(),
    serie["fecha"].max(),
    freq="M"
)

fechas_observadas = (
    serie["fecha"]
    .dt.to_period("M")
    .to_numpy()
)

if (
    len(serie) != len(esperados)
    or not (
        fechas_observadas
        == esperados.to_numpy()
    ).all()
):
    raise ValueError(
        "Hay meses ausentes en Seguridad. "
        "No deben rellenarse con ceros."
    )

if len(serie) < 24:
    raise ValueError(
        "Se requieren al menos 24 meses."
    )


# ============================================
# 14. VARIABLES TEMPORALES
# ============================================

inicio = serie["fecha"].iloc[0]

# Tiempo expresado en meses.
t = (
    (
        serie["fecha"].dt.year
        - inicio.year
    ) * 12
    +
    (
        serie["fecha"].dt.month
        - inicio.month
    )
).to_numpy(dtype=float)

# Estacionalidad anual.
angulo = (
    2 * np.pi
    * serie["fecha"].dt.month.to_numpy()
    / 12
)

X_seguridad = pd.DataFrame({
    "const": np.ones(len(serie)),
    "t_meses": t,
    "sin_anual": np.sin(angulo),
    "cos_anual": np.cos(angulo)
})

y_seguridad = serie[
    "cantidad"
].to_numpy(dtype=float)


# ============================================
# 15. AJUSTAR MODELO TEMPORAL
# ============================================

modelo_seguridad, pred_seguridad, dispersion_seg = (
    ajustar(
        "homicidio_estatal_mensual",
        y_seguridad,
        X_seguridad,
        coeficientes,
        diagnosticos
    )
)


# ============================================
# 16. CALCULAR RESIDUOS TEMPORALES
# ============================================

residuos_seguridad = (
    y_seguridad - pred_seguridad
) / np.sqrt(
    np.maximum(
        pred_seguridad,
        1e-8
    )
)


# ============================================
# 17. PRUEBA DE LJUNG-BOX
# ============================================

# Evaluar autocorrelacion temporal
# de los residuos de Pearson.

rezago = min(
    12,
    len(serie) // 4
)

resultado_lb = acorr_ljungbox(
    residuos_seguridad,
    lags=[rezago],
    return_df=True
)

p_ljung_box = float(
    resultado_lb[
        "lb_pvalue"
    ].iloc[0]
)

serie["esperado_poisson"] = (
    pred_seguridad
)

serie["residuo_pearson"] = (
    residuos_seguridad
)


# ============================================
# 18. EXPORTAR RESULTADOS
# ============================================

pd.DataFrame(
    correlaciones
).to_csv(
    PROCESADA / "09_correlaciones.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    diagnosticos
).to_csv(
    PROCESADA / "09_modelos_diagnosticos.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    coeficientes
).to_csv(
    PROCESADA / "09_modelos_coeficientes.csv",
    index=False,
    encoding="utf-8-sig"
)

municipal.to_csv(
    PROCESADA / "09_predicciones_municipales.csv",
    index=False,
    encoding="utf-8-sig"
)

serie.to_csv(
    PROCESADA / "09_predicciones_seguridad.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 19. MOSTRAR RESULTADOS
# ============================================

print("\n=== INFERENCIA ESTADISTICA ===")

print(
    "Municipios en modelo:",
    len(municipal)
)

print(
    "Dispersion Pearson municipal:",
    round(dispersion_mun, 3)
)

print(
    "Meses en modelo delictivo:",
    len(serie)
)

print(
    "Dispersion Pearson temporal:",
    round(dispersion_seg, 3)
)

print(
    f"Ljung-Box, lag {rezago}, "
    f"p exploratorio: {p_ljung_box:.4g}"
)

print("\nCorrelaciones exploratorias:")

print(
    pd.DataFrame(
        correlaciones
    ).to_string(index=False)
)

print("\nDiagnosticos y AIC:")

print(
    pd.DataFrame(
        diagnosticos
    ).to_string(index=False)
)

print(
    "\nArchivos 09_*.csv "
    "guardados en Data Procesada."
)

print(
    "NOTA: HC0 no corrige dependencia "
    "temporal ni espacial."
)

print(
    "NOTA: conteos registrados no "
    "equivalen a tasas de riesgo."
)

print(
    "NOTA: asociacion no implica causalidad."
)
