
"""
HOTSPOT | Etapa 10

Modelado de conteos y validacion de cobertura.

Fuentes:
1. Siniestralimap: panel 2015-2025
2. ATUS: accidentes municipales 2025
3. DENUE: establecimientos mayo 2025
4. Seguridad: homicidios mensuales

Modelos exploratorios.
No estiman causalidad ni riesgo individual.
"""

# ============================================
# 1. BIBLIOTECAS
# ============================================

from pathlib import Path
import unicodedata
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from statsmodels.discrete.discrete_model import (
    NegativeBinomial
)

from scipy.stats import spearmanr

from statsmodels.stats.diagnostic import (
    acorr_ljungbox
)


# ============================================
# 2. CONFIGURACION
# ============================================

RAIZ = Path(__file__).resolve().parent.parent

PROCESADA = RAIZ / "Data Procesada"

PROCESADA.mkdir(
    parents=True,
    exist_ok=True
)

# Municipios con series recurrentes
# de Siniestralimap entre 2015 y 2025.

CORE = [
    "Guadalajara",
    "Zapopan",
    "San Pedro Tlaquepaque",
    "Tlajomulco de Zúñiga",
    "Tonalá",
    "El Salto",
]

ANIOS = list(range(2015, 2026))


# ============================================
# 3. FUNCIONES DE LECTURA Y VALIDACION
# ============================================

def leer(nombre, **opciones):

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


def nombre_normalizado(valor):

    if pd.isna(valor):
        return ""

    texto = unicodedata.normalize(
        "NFKD",
        str(valor).upper().strip()
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    return " ".join(texto.split())


def validar_conteos(serie, etiqueta):

    valores = pd.to_numeric(
        serie,
        errors="coerce"
    )

    invalidos = (
        valores.isna()
        | (valores < 0)
        | (valores != np.floor(valores))
    )

    if invalidos.any():
        raise ValueError(
            f"Valores invalidos en {etiqueta}"
        )

    return valores.astype(int)


# ============================================
# 4. FUNCION ESTADISTICA GENERAL
# ============================================

diagnosticos = []
coeficientes = []


def ajustar_modelos(
    nombre,
    tabla,
    formula,
    respuesta
):

    # ----------------------------------------
    # A. REGRESION DE POISSON
    # ----------------------------------------

    poisson = smf.glm(
        formula,
        data=tabla,
        family=sm.families.Poisson()
    ).fit(cov_type="HC0")

    esperado_poisson = np.asarray(
        poisson.predict(tabla),
        dtype=float
    )

    y = tabla[respuesta].to_numpy(
        dtype=float
    )

    # ----------------------------------------
    # B. DISPERSION DE PEARSON
    # ----------------------------------------

    grados = float(poisson.df_resid)

    dispersion = (
        float(
            np.sum(
                (y - esperado_poisson) ** 2
                / np.maximum(
                    esperado_poisson,
                    1e-9
                )
            ) / grados
        )
        if grados > 0
        else np.nan
    )

    diagnosticos.append({
        "analisis": nombre,
        "modelo": "Poisson_HC0",
        "n": len(tabla),
        "aic": float(poisson.aic),
        "dispersion_pearson": dispersion,
        "convergio": True
    })

    # ----------------------------------------
    # C. COEFICIENTES POISSON
    # ----------------------------------------

    for variable in poisson.params.index:

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
            "p_exploratorio": float(
                poisson.pvalues[variable]
            ),
            "ic95_inf": float(
                intervalo.iloc[0]
            ),
            "ic95_sup": float(
                intervalo.iloc[1]
            )
        })

    # ----------------------------------------
    # D. BINOMIAL NEGATIVA NB2
    # ----------------------------------------

    nb = None

    try:

        with warnings.catch_warnings():

            warnings.simplefilter(
                "ignore",
                RuntimeWarning
            )

            # Matriz de variables generada
            # por el modelo Poisson.
            X_nb = pd.DataFrame(
                poisson.model.exog,
                columns=poisson.model.exog_names
            )

            nb = NegativeBinomial(
                y,
                X_nb,
                loglike_method="nb2"
            ).fit(
                start_params=np.r_[
                    np.asarray(poisson.params),
                    0.02
                ],
                method="bfgs",
                disp=False,
                maxiter=1000
            )

        convergio = bool(
            nb.mle_retvals.get(
                "converged",
                False
            )
        )

        if not np.isfinite(nb.aic):
            convergio = False

        diagnosticos.append({
            "analisis": nombre,
            "modelo": "Binomial_negativa_NB2",
            "n": len(tabla),
            "aic": (
                float(nb.aic)
                if np.isfinite(nb.aic)
                else np.nan
            ),
            "dispersion_pearson": np.nan,
            "convergio": convergio
        })

        if convergio:

            intervalos = nb.conf_int()

            for variable in nb.params.index:

                intervalo = intervalos.loc[
                    variable
                ]

                coeficientes.append({
                    "analisis": nombre,
                    "modelo": "Binomial_negativa_NB2",
                    "variable": variable,
                    "beta": float(
                        nb.params[variable]
                    ),
                    "p_exploratorio": float(
                        nb.pvalues[variable]
                    ),
                    "ic95_inf": float(
                        intervalo.iloc[0]
                    ),
                    "ic95_sup": float(
                        intervalo.iloc[1]
                    )
                })

        else:

            nb = None

            print(
                f"AVISO: NB2 no convergio "
                f"en {nombre}"
            )

    except (
        ValueError,
        ArithmeticError,
        np.linalg.LinAlgError
    ) as error:

        print(
            f"AVISO: NB2 fallo en "
            f"{nombre}: {error}"
        )

        diagnosticos.append({
            "analisis": nombre,
            "modelo": "Binomial_negativa_NB2",
            "n": len(tabla),
            "aic": np.nan,
            "dispersion_pearson": np.nan,
            "convergio": False
        })

        nb = None

    # ----------------------------------------
    # E. PREDICCIONES Y RESIDUOS
    # ----------------------------------------

    tabla = tabla.copy()

    tabla["esperado_poisson"] = (
        esperado_poisson
    )

    tabla["residuo_pearson_poisson"] = (
        (y - esperado_poisson)
        / np.sqrt(
            np.maximum(
                esperado_poisson,
                1e-9
            )
        )
    )

    tabla["esperado_nb2"] = (
        np.asarray(
            nb.predict(X_nb),
            dtype=float
        )
        if nb is not None
        else np.nan
    )

    return tabla, poisson, nb


# ============================================
# 5. SINIESTRALIMAP: PREPARAR PANEL
# ============================================

siniestros = leer(
    "03_siniestros_unicos.csv",
    dtype={"id_siniestro": "string"}
)

if (
    siniestros["id_siniestro"].isna().any()
    or siniestros["id_siniestro"]
    .duplicated().any()
):
    raise ValueError(
        "Identificadores duplicados o vacios"
    )

siniestros["anio"] = pd.to_numeric(
    siniestros["anio"],
    errors="coerce"
)

siniestros = siniestros[
    siniestros["anio"].between(
        2015, 2025
    )
].copy()

siniestros["anio"] = validar_conteos(
    siniestros["anio"],
    "anio Siniestralimap"
)

siniestros["municipio_norm"] = (
    siniestros["municipio"]
    .map(nombre_normalizado)
)

core_norm = {
    nombre_normalizado(nombre): nombre
    for nombre in CORE
}

siniestros["municipio_panel"] = (
    siniestros["municipio_norm"]
    .map(core_norm)
)


# ============================================
# 6. CONTROL DE COBERTURA
# ============================================

cobertura = (
    siniestros
    .groupby(
        ["anio", "municipio"],
        dropna=False
    )
    .size()
    .reset_index(
        name="eventos_fuente"
    )
)

cobertura["incluido_panel"] = (
    cobertura["municipio"].map(
        lambda x: (
            nombre_normalizado(x)
            in core_norm
        )
    )
)

cobertura.to_csv(
    PROCESADA
    / "10_cobertura_siniestralimap.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 7. CONSTRUIR PANEL MUNICIPIO-ANIO
# ============================================

siniestros_core = siniestros[
    siniestros["municipio_panel"].notna()
].copy()

conteos = (
    siniestros_core
    .groupby(
        ["municipio_panel", "anio"],
        as_index=False
    )
    .agg(
        siniestros_registrados=(
            "id_siniestro",
            "nunique"
        )
    )
)

# Todas las combinaciones posibles:
# seis municipios por once anios.

panel_referencia = (
    pd.MultiIndex.from_product(
        [CORE, ANIOS],
        names=[
            "municipio_panel",
            "anio"
        ]
    )
    .to_frame(index=False)
)

panel = panel_referencia.merge(
    conteos,
    on=["municipio_panel", "anio"],
    how="left",
    validate="one_to_one"
)

# No convertir datos no observados en 0.
panel["cobertura_observada"] = (
    panel["siniestros_registrados"]
    .notna()
)

panel["t_anios"] = (
    panel["anio"] - min(ANIOS)
)

panel_modelo = panel.dropna(
    subset=["siniestros_registrados"]
).copy()

panel_modelo[
    "siniestros_registrados"
] = validar_conteos(
    panel_modelo[
        "siniestros_registrados"
    ],
    "siniestros del panel"
)

if (
    panel_modelo["municipio_panel"].nunique() < 3
    or panel_modelo["anio"].nunique() < 6
):
    raise ValueError(
        "Panel temporal insuficiente"
    )


# ============================================
# 8. MODELO TEMPORAL DE SINIESTROS
# ============================================

panel_ajustado, poisson_sin, nb_sin = (
    ajustar_modelos(
        "siniestralimap_panel_6_municipios",
        panel_modelo,
        (
            "siniestros_registrados ~ "
            "C(municipio_panel) + t_anios"
        ),
        "siniestros_registrados"
    )
)

panel = panel.merge(
    panel_ajustado[
        [
            "municipio_panel",
            "anio",
            "esperado_poisson",
            "esperado_nb2",
            "residuo_pearson_poisson"
        ]
    ],
    on=["municipio_panel", "anio"],
    how="left",
    validate="one_to_one"
)

panel.to_csv(
    PROCESADA
    / "10_panel_siniestros_2015_2025.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 9. ANALISIS DE SENSIBILIDAD
# ============================================

# Repetimos el ajuste sin Guadalajara,
# para ver si domina la tendencia.

sin_guadalajara = panel_modelo[
    panel_modelo["municipio_panel"]
    != "Guadalajara"
].copy()

sensibilidad = smf.glm(
    (
        "siniestros_registrados ~ "
        "C(municipio_panel) + t_anios"
    ),
    data=sin_guadalajara,
    family=sm.families.Poisson()
).fit(cov_type="HC0")

print(
    "\n=== SINIESTRALIMAP 2015-2025 ==="
)

print(
    "Eventos en seis municipios:",
    len(siniestros_core)
)

print(
    "Municipio-anios observados:",
    len(panel_modelo),
    "de",
    len(panel)
)

print(
    "Eventos fuera del panel:",
    len(siniestros) - len(siniestros_core)
)

print(
    "Beta anual Poisson:",
    round(
        float(poisson_sin.params["t_anios"]),
        5
    )
)

print(
    "Beta anual sin Guadalajara:",
    round(
        float(sensibilidad.params["t_anios"]),
        5
    )
)


# ============================================
# 10. ATUS + DENUE, CORTE 2025
# ============================================

municipal = leer(
    "08_matriz_municipal_2025.csv",
    dtype={"cvegeo": "string"}
)

if (
    len(municipal) != 125
    or municipal["cvegeo"]
    .duplicated().any()
):
    raise ValueError(
        "La matriz 08 no contiene "
        "125 municipios unicos"
    )

columnas = [
    "registros_atus_2025",
    "establecimientos_denue_mayo_2025"
]

for columna in columnas:

    municipal[columna] = pd.to_numeric(
        municipal[columna],
        errors="coerce"
    )

# Solo municipios con ambas variables.
atus_muestra = municipal.dropna(
    subset=columnas
).copy()

atus_muestra[
    "registros_atus_2025"
] = validar_conteos(
    atus_muestra["registros_atus_2025"],
    "ATUS"
)

atus_muestra[
    "establecimientos_denue_mayo_2025"
] = validar_conteos(
    atus_muestra[
        "establecimientos_denue_mayo_2025"
    ],
    "DENUE"
)

atus_muestra["log1p_denue"] = (
    np.log1p(
        atus_muestra[
            "establecimientos_denue_mayo_2025"
        ].astype(float)
    )
)

if len(atus_muestra) < 20:
    raise ValueError(
        "Muestra ATUS-DENUE insuficiente"
    )

# Correlacion exploratoria.
rho, p_rho = spearmanr(
    atus_muestra[
        "registros_atus_2025"
    ],
    atus_muestra[
        "establecimientos_denue_mayo_2025"
    ]
)

atus_ajustado, poisson_atus, nb_atus = (
    ajustar_modelos(
        "atus_denue_municipal_2025",
        atus_muestra,
        (
            "registros_atus_2025 "
            "~ log1p_denue"
        ),
        "registros_atus_2025"
    )
)

atus_ajustado.to_csv(
    PROCESADA / "10_atus_denue_2025.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n=== ATUS + DENUE 2025 ===")

print(
    "Municipios con ambas fuentes:",
    len(atus_muestra)
)

print(
    "Sin ATUS disponible:",
    len(municipal) - len(atus_muestra)
)

print(
    f"Spearman: rho={rho:.4f}, "
    f"p exploratorio={p_rho:.4g}"
)


# ============================================
# 11. SEGURIDAD: SERIE DE HOMICIDIOS
# ============================================

seguridad = leer(
    "05_seguridad_controlada.csv"
)

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
        "Serie estatal ausente o duplicada"
    )

serie["fecha"] = pd.to_datetime(
    serie["periodo"] + "-01",
    format="%Y-%m-%d"
)

serie = (
    serie.sort_values("fecha")
    .reset_index(drop=True)
)

serie["cantidad"] = validar_conteos(
    serie["cantidad"],
    "Seguridad"
)

# Comprobar continuidad mensual.
meses = pd.period_range(
    serie["fecha"].min(),
    serie["fecha"].max(),
    freq="M"
)

observados = (
    serie["fecha"]
    .dt.to_period("M")
    .reset_index(drop=True)
)

if not observados.equals(
    pd.Series(meses)
):
    raise ValueError(
        "La serie tiene meses ausentes"
    )


# ============================================
# 12. VARIABLES TEMPORALES
# ============================================

serie["t_meses"] = np.arange(
    len(serie),
    dtype=float
)

angulo = (
    2 * np.pi
    * serie["fecha"].dt.month
    / 12
)

serie["sin_anual"] = np.sin(angulo)
serie["cos_anual"] = np.cos(angulo)


# ============================================
# 13. MODELO TEMPORAL DE SEGURIDAD
# ============================================

serie_ajustada, poisson_seg, nb_seg = (
    ajustar_modelos(
        "homicidio_doloso_estatal_mensual",
        serie,
        (
            "cantidad ~ t_meses "
            "+ sin_anual + cos_anual"
        ),
        "cantidad"
    )
)

# Prueba de autocorrelacion residual.
lb = acorr_ljungbox(
    serie_ajustada[
        "residuo_pearson_poisson"
    ],
    lags=[12],
    return_df=True
)

p_lb = float(
    lb["lb_pvalue"].iloc[0]
)

serie_ajustada.to_csv(
    PROCESADA / "10_seguridad_temporal.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n=== SEGURIDAD MENSUAL ===")

print(
    "Meses:",
    len(serie_ajustada)
)

print(
    "Ljung-Box, 12 rezagos:",
    f"{p_lb:.4g}"
)


# ============================================
# 14. SENSIBILIDAD A DISCREPANCIAS
# ============================================

if "control_regional" in serie.columns:

    revisados = (
        serie["control_regional"]
        .eq("REVISAR")
    )

    print(
        "Meses marcados para revision:",
        int(revisados.sum())
    )

    if (
        revisados.any()
        and (~revisados).sum() >= 24
    ):

        sin_revisados = smf.glm(
            (
                "cantidad ~ t_meses "
                "+ sin_anual + cos_anual"
            ),
            data=serie.loc[~revisados],
            family=sm.families.Poisson()
        ).fit(cov_type="HC0")

        print(
            "Beta temporal, todos:",
            round(
                float(
                    poisson_seg.params["t_meses"]
                ),
                5
            )
        )

        print(
            "Beta temporal, sin revision:",
            round(
                float(
                    sin_revisados.params["t_meses"]
                ),
                5
            )
        )


# ============================================
# 15. EXPORTAR DIAGNOSTICOS
# ============================================

pd.DataFrame(
    diagnosticos
).to_csv(
    PROCESADA
    / "10_diagnosticos_modelos.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    coeficientes
).to_csv(
    PROCESADA
    / "10_coeficientes_modelos.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 16. RESULTADOS FINALES
# ============================================

print("\n=== RESUMEN DE MODELOS ===")

print(
    pd.DataFrame(
        diagnosticos
    ).to_string(index=False)
)

print(
    "\nSe generaron 6 archivos "
    "10_*.csv en Data Procesada."
)

print(
    "AVISO: los valores p son exploratorios."
)

print(
    "No se han corregido aun las dependencias "
    "temporales ni espaciales."
)

print(
    "DENUE mayo 2025 solo se utiliza "
    "en el corte municipal 2025."
)
