
from pathlib import Path
import pandas as pd

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent

CRUDA = RAIZ / "Data Cruda"
PROCESADA = RAIZ / "Data Procesada"

PROCESADA.mkdir(exist_ok=True)


def encontrar(nombre):
    archivos = list(CRUDA.rglob(nombre))

    if len(archivos) != 1:
        raise RuntimeError(
            f"Esperaba un archivo llamado {nombre}. "
            f"Encontré {len(archivos)}."
        )

    return archivos[0]


def leer_csv(ruta, columnas):
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(
                ruta,
                usecols=columnas,
                dtype="string",
                encoding=encoding,
                low_memory=False
            )
        except UnicodeDecodeError:
            continue

    raise RuntimeError("Error de codificación")


# ==========================================
# 2. CARGAR ATUS
# ==========================================

atus = leer_csv(
    encontrar("atus_anual_2025.csv"),
    [
        "CVE_ENT",
        "CVE_MUN",
        "ANIO",
        "TIPACCID",
        "CAUSAACCI",
        "CLASACC"
    ]
)

# Conservar únicamente Jalisco y 2025.
atus = atus[
    (atus["CVE_ENT"].str.strip().str.zfill(2) == "14")
    & (atus["ANIO"].str.strip() == "2025")
].copy()

print("\n=== ATUS 2025 ===")
print("Registros:", len(atus))


# ==========================================
# 3. EXPLORAR ACCIDENTES
# ==========================================

def explorar_variable(df, columna, archivo):
    conteos = (
        df[columna]
        .fillna("SIN_DATO")
        .str.strip()
        .replace("", "SIN_DATO")
        .value_counts()
        .rename_axis("codigo")
        .reset_index(name="cantidad")
    )

    conteos["porcentaje"] = (
        conteos["cantidad"] / len(df) * 100
    ).round(2)

    print(f"\n=== {columna} ===")
    print(conteos.head(15).to_string(index=False))

    conteos.to_csv(
        PROCESADA / archivo,
        index=False,
        encoding="utf-8-sig"
    )


explorar_variable(
    atus,
    "TIPACCID",
    "02_tipos_accidente.csv"
)

explorar_variable(
    atus,
    "CAUSAACCI",
    "02_causas_accidente.csv"
)

explorar_variable(
    atus,
    "CLASACC",
    "02_clasificaciones_accidente.csv"
)


# ==========================================
# 4. CARGAR DENUE
# ==========================================

denue = leer_csv(
    encontrar("denue_inegi_14_.csv"),
    [
        "id",
        "cve_ent",
        "cve_mun",
        "codigo_act",
        "per_ocu"
    ]
)

denue = denue[
    denue["cve_ent"].str.strip().str.zfill(2) == "14"
].copy()

# Eliminar IDs duplicados cuando existan.
duplicados = (
    denue["id"].notna()
    & denue["id"].duplicated()
)

denue = denue.loc[~duplicados].copy()

print("\n=== DENUE ===")
print("Establecimientos:", len(denue))


# ==========================================
# 5. EXPLORAR ACTIVIDAD ECONÓMICA
# ==========================================

# Los primeros dos dígitos representan el
# nivel sector del código SCIAN.
denue["sector_scian"] = (
    denue["codigo_act"]
    .str.strip()
    .str[:2]
)

explorar_variable(
    denue,
    "sector_scian",
    "02_sectores_economicos.csv"
)

explorar_variable(
    denue,
    "per_ocu",
    "02_personal_ocupado.csv"
)

print("\nExploración terminada correctamente.")
