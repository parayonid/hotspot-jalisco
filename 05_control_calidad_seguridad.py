
from pathlib import Path
import pandas as pd

# ==========================================
# 1. RUTAS
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "Data Procesada"

ruta_series = CARPETA / "04_seguridad_region_mes.csv"
ruta_discrepancias = CARPETA / "04_seguridad_discrepancias.csv"

# ==========================================
# 2. CARGAR RESULTADOS DEL SCRIPT 04
# ==========================================

series = pd.read_csv(
    ruta_series,
    dtype={
        "periodo": "string",
        "delito": "string",
        "medida": "string",
        "region": "string"
    }
)

discrepancias = pd.read_csv(
    ruta_discrepancias,
    dtype={
        "periodo": "string",
        "delito": "string",
        "medida": "string"
    }
)

# ==========================================
# 3. IDENTIFICAR OBSERVACIONES CON ALERTAS
# ==========================================

# Una discrepancia se identifica mediante:
# mes + delito + tipo de medida.

claves = ["periodo", "delito", "medida"]

alertas = (
    discrepancias[claves]
    .drop_duplicates()
    .copy()
)

alertas["control_regional"] = "REVISAR"

# Marcamos las observaciones relacionadas.
# No modificamos sus cantidades.

tabla = series.merge(
    alertas,
    on=claves,
    how="left",
    validate="many_to_one"
)

tabla["control_regional"] = (
    tabla["control_regional"]
    .fillna("SIN_DISCREPANCIA_DETECTADA")
)

# ==========================================
# 4. IDENTIFICAR TOTALES Y SUBTOTALES
# ==========================================

# Evitaremos sumar indicadores que ya
# contienen otras categorias.

tabla["es_resumen"] = (
    tabla["delito"]
    .str.upper()
    .str.contains(
        r"^(?:INCIDENCIA TOTAL|TOTAL DE ROBOS)",
        regex=True,
        na=False
    )
)

# ==========================================
# 5. EXPORTAR DATOS DOCUMENTADOS
# ==========================================

salida = (
    CARPETA / "05_seguridad_controlada.csv"
)

tabla.to_csv(
    salida,
    index=False,
    encoding="utf-8-sig"
)

# ==========================================
# 6. VALIDAR RESULTADOS
# ==========================================

assert len(tabla) == len(series)

assert (
    tabla["cantidad"].sum()
    == series["cantidad"].sum()
)

print("\n=== CONTROL DE CALIDAD ===")

print("Observaciones originales:", len(series))

print(
    "Discrepancias regionales:",
    len(alertas)
)

print(
    "Observaciones asociadas a discrepancias:",
    (tabla["control_regional"] == "REVISAR").sum()
)

print(
    "Observaciones sin discrepancia detectada:",
    (
        tabla["control_regional"]
        == "SIN_DISCREPANCIA_DETECTADA"
    ).sum()
)

print("\nArchivo generado:", salida)
