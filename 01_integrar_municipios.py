
from pathlib import Path
import pandas as pd

# ==============================================
# 1. UBICACIÓN DE LOS DATOS
# ==============================================

RAIZ = Path(__file__).resolve().parent.parent

CRUDA = RAIZ / "Data Cruda"
PROCESADA = RAIZ / "Data Procesada"

PROCESADA.mkdir(exist_ok=True)


def encontrar(nombre):
    archivos = list(CRUDA.rglob(nombre))

    if not archivos:
        raise FileNotFoundError(
            f"No encontré {nombre} dentro de {CRUDA}"
        )

    if len(archivos) > 1:
        raise RuntimeError(
            f"Hay varias copias de {nombre}"
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

    raise RuntimeError(f"No pude leer {ruta.name}")


# ==============================================
# 2. NORMALIZACIÓN GEOGRÁFICA
# ==============================================

def codigo(serie, ancho):
    return (
        serie.fillna("")
        .str.strip()
        .str.replace(r"\.0+$", "", regex=True)
        .str.zfill(ancho)
    )


def preparar_municipio(df, campo_entidad, campo_municipio):
    df = df.copy()

    df["entidad"] = codigo(df[campo_entidad], 2)
    df["municipio"] = codigo(df[campo_municipio], 3)

    # 14 es la clave de Jalisco
    df = df[df["entidad"] == "14"].copy()

    validos = (
        df["municipio"].str.fullmatch(r"\d{3}")
        & ~df["municipio"].isin(["000", "999"])
    )

    descartados = int((~validos).sum())

    df = df[validos].copy()

    df["cvegeo"] = df["entidad"] + df["municipio"]

    return df, descartados


# ==============================================
# 3. PROCESAMIENTO DE ATUS 2025
# ==============================================

ruta_atus = encontrar("atus_anual_2025.csv")

atus = leer_csv(
    ruta_atus,
    ["CVE_ENT", "CVE_MUN", "ANIO"]
)

atus = atus[
    codigo(atus["ANIO"], 4) == "2025"
].copy()

atus, descartados_atus = preparar_municipio(
    atus,
    "CVE_ENT",
    "CVE_MUN"
)

conteo_atus = (
    atus.groupby("cvegeo")
    .size()
    .rename("registros_atus_2025")
)


# ==============================================
# 4. PROCESAMIENTO DE DENUE
# ==============================================

ruta_denue = encontrar("denue_inegi_14_.csv")

denue = leer_csv(
    ruta_denue,
    ["id", "cve_ent", "cve_mun"]
)

denue, descartados_denue = preparar_municipio(
    denue,
    "cve_ent",
    "cve_mun"
)

# Evitamos contar dos veces el mismo ID registrado
duplicados = (
    denue["id"].notna()
    & denue["id"].duplicated(keep="first")
)

num_duplicados = int(duplicados.sum())

denue = denue.loc[~duplicados].copy()

conteo_denue = (
    denue.groupby("cvegeo")
    .size()
    .rename("establecimientos_denue_mayo_2025")
)



# ==============================================
# 5. INTEGRACIÓN DE LOS DOS DATASETS
# ==============================================

# Unimos las series por su índice compartido:
# la clave geográfica de cinco dígitos (CVEGEO).

tabla = pd.concat(
    [conteo_atus, conteo_denue],
    axis=1
)

# Recuperamos CVEGEO como una columna real.
tabla = tabla.rename_axis("cvegeo").reset_index()

# Normalizamos los identificadores.
tabla["cvegeo"] = tabla["cvegeo"].astype("string").str.zfill(5)

# Separamos la clave estatal y municipal.
tabla.insert(1, "cve_ent", tabla["cvegeo"].str[:2])
tabla.insert(2, "cve_mun", tabla["cvegeo"].str[2:])

# Identificamos qué municipios tienen registros.
tabla["atus_con_registros"] = (
    tabla["registros_atus_2025"].notna()
)

tabla["denue_con_registros"] = (
    tabla["establecimientos_denue_mayo_2025"].notna()
)

# Conservamos los valores ausentes.
tabla["registros_atus_2025"] = pd.to_numeric(
    tabla["registros_atus_2025"],
    errors="coerce"
).astype("Int64")

tabla["establecimientos_denue_mayo_2025"] = pd.to_numeric(
    tabla["establecimientos_denue_mayo_2025"],
    errors="coerce"
).astype("Int64")

# Ordenamos los municipios.
tabla = tabla.sort_values("cvegeo").reset_index(drop=True)


# ==============================================
# 6. VALIDACIÓN DE LA INTEGRACIÓN
# ==============================================

print("\n========== VALIDACIÓN ==========")

# Verificamos que existen las columnas esenciales.
columnas_obligatorias = [
    "cvegeo",
    "cve_ent",
    "cve_mun",
    "registros_atus_2025",
    "establecimientos_denue_mayo_2025"
]

for columna in columnas_obligatorias:
    assert columna in tabla.columns, (
        f"Falta la columna: {columna}"
    )

# Verificamos los identificadores geográficos.
assert tabla["cvegeo"].str.fullmatch(r"14\d{3}").all(), (
    "Existen claves municipales inválidas"
)

assert tabla["cvegeo"].is_unique, (
    "Hay municipios duplicados"
)

# Los totales deben coincidir con los registros procesados.
assert tabla["registros_atus_2025"].sum() == len(atus)
assert tabla["establecimientos_denue_mayo_2025"].sum() == len(denue)

print("Identificadores municipales: CORRECTOS")
print("Municipios duplicados: 0")
print("Totales de ambas fuentes: CORRECTOS")

print("\nMunicipios totales:", len(tabla))

print(
    "Municipios con registros ATUS:",
    int(tabla["atus_con_registros"].sum())
)

print(
    "Municipios con registros DENUE:",
    int(tabla["denue_con_registros"].sum())
)

print(
    "Municipios sin registros ATUS:",
    int((~tabla["atus_con_registros"]).sum())
)

print(
    "Total registros ATUS:",
    int(tabla["registros_atus_2025"].sum())
)

print(
    "Total establecimientos DENUE:",
    int(tabla["establecimientos_denue_mayo_2025"].sum())
)

print("\nMunicipios sin registros ATUS:")

municipios_sin_atus = tabla.loc[
    ~tabla["atus_con_registros"],
    [
        "cvegeo",
        "establecimientos_denue_mayo_2025"
    ]
]

print(municipios_sin_atus.to_string(index=False))


# ==============================================
# 7. EXPORTACIÓN
# ==============================================

salida = (
    PROCESADA /
    "01_atus_denue_por_municipio_2025.csv"
)

tabla.to_csv(
    salida,
    index=False,
    encoding="utf-8-sig"
)

print("\n========== RESULTADO FINAL ==========")

print("\nColumnas:")
print(tabla.columns.tolist())

print("\nPrimeras ocho filas:")
print(tabla.head(8).to_string(index=False))

print(f"\nArchivo generado: {salida}")
