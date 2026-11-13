
"""
HOTSPOT - 07_unir_cartografia_municipios.py

Objetivo:
Unir la tabla ATUS + DENUE con los
atributos de la cartografia municipal.

No modifica los datos originales.
No transforma todavia las geometrias.
"""

from pathlib import Path
import sqlite3
import pandas as pd


# ==========================================
# 1. CONFIGURAR RUTAS
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent

CRUDA = RAIZ / "Data Cruda"
PROCESADA = RAIZ / "Data Procesada"

RUTA_BASE = (
    PROCESADA
    / "01_atus_denue_por_municipio_2025.csv"
)

candidatos = list(
    CRUDA.rglob(
        "limite_municipal_jalisco_iieg.gpkg"
    )
)

if len(candidatos) != 1:
    raise FileNotFoundError(
        "No se encontro exactamente un GeoPackage"
    )

RUTA_GPKG = candidatos[0]


# ==========================================
# 2. LEER TABLA ESTADISTICA
# ==========================================

base = pd.read_csv(
    RUTA_BASE,
    dtype={"cvegeo": "string"},
    encoding="utf-8-sig"
)

base.columns = base.columns.str.strip()

if "cvegeo" not in base.columns:
    raise KeyError(
        f"No existe cvegeo. Columnas: {base.columns.tolist()}"
    )

print("\n=== TABLA ATUS + DENUE ===")
print("Municipios:", len(base))
print("Columnas:", base.columns.tolist())


# ==========================================
# 3. LEER ATRIBUTOS DEL GEOPACKAGE
# ==========================================

with sqlite3.connect(RUTA_GPKG) as conexion:

    consulta = """
    SELECT
        clave_geo AS cvegeo,
        nombre AS municipio_cartografia,
        region AS region_iieg,
        area_km2,
        area_ha
    FROM limite_municipal
    """

    cartografia = pd.read_sql_query(
        consulta,
        conexion
    )

print("\n=== CARTOGRAFIA MUNICIPAL ===")
print("Municipios:", len(cartografia))


# ==========================================
# 4. NORMALIZAR CLAVES
# ==========================================

base["cvegeo"] = (
    base["cvegeo"]
    .astype("string")
    .str.strip()
)

cartografia["cvegeo"] = (
    cartografia["cvegeo"]
    .astype("string")
    .str.strip()
)

# Las claves deben comenzar con 14
# y contener exactamente cinco digitos.

for nombre, tabla in [
    ("ATUS + DENUE", base),
    ("Cartografia", cartografia)
]:

    validas = tabla["cvegeo"].str.fullmatch(
        r"14\d{3}",
        na=False
    )

    if not validas.all():
        raise ValueError(
            f"Claves invalidas en {nombre}: "
            f"{tabla.loc[~validas, 'cvegeo'].tolist()}"
        )

    if tabla["cvegeo"].duplicated().any():
        raise ValueError(
            f"Claves duplicadas en {nombre}"
        )


# ==========================================
# 5. UNIR LAS DOS TABLAS
# ==========================================

matriz = base.merge(
    cartografia,
    on="cvegeo",
    how="outer",
    validate="one_to_one",
    indicator=True
)

print("\n=== VALIDACION DE LA UNION ===")

print(
    matriz["_merge"]
    .value_counts()
    .to_string()
)


# ==========================================
# 6. REVISAR MUNICIPIOS SIN COINCIDENCIA
# ==========================================

faltantes = matriz[
    matriz["_merge"] != "both"
]

if not faltantes.empty:

    ruta_errores = (
        PROCESADA
        / "07_municipios_sin_coincidencia.csv"
    )

    faltantes.to_csv(
        ruta_errores,
        index=False,
        encoding="utf-8-sig"
    )

    raise ValueError(
        "Hay municipios sin coincidencia. "
        "Revisa el archivo de control."
    )


# ==========================================
# 7. GUARDAR MATRIZ MUNICIPAL
# ==========================================

matriz = (
    matriz
    .drop(columns=["_merge"])
    .sort_values("cvegeo")
    .reset_index(drop=True)
)

ruta_salida = (
    PROCESADA
    / "07_matriz_municipal_geografica.csv"
)

matriz.to_csv(
    ruta_salida,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 8. MOSTRAR RESULTADOS
# ==========================================

print("\n=== MATRIZ MUNICIPAL GENERADA ===")

print("Municipios integrados:", len(matriz))

print(
    "Municipios sin superficie:",
    matriz["area_km2"].isna().sum()
)

print("\nPrimeros municipios:")

print(
    matriz[
        [
            "cvegeo",
            "municipio_cartografia",
            "region_iieg",
            "area_km2"
        ]
    ].head(10).to_string(index=False)
)

print("\nArchivo generado:", ruta_salida.name)
