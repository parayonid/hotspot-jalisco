
"""
HOTSPOT - 08_integracion_estadistica_hotspot.py

Objetivo:
Integrar los cuatro datasets respetando
sus escalas espaciales y temporales.

Fuentes:
1. ATUS
2. DENUE
3. Siniestralimap
4. Plataforma de Seguridad

Periodo de comparacion: 2025

Salidas:
08_matriz_municipal_2025.csv
08_seguridad_region_mes_2025.csv
08_seguridad_resumen_2025.csv
08_siniestros_sin_asignar_2025.csv
08_control_integracion.csv
"""

# ==========================================
# 1. BIBLIOTECAS
# ==========================================

from pathlib import Path
import re
import unicodedata
import pandas as pd


# ==========================================
# 2. RUTAS
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent
PROCESADA = RAIZ / "Data Procesada"

RUTA_MUNICIPIOS = (
    PROCESADA / "07_matriz_municipal_geografica.csv"
)

RUTA_SINIESTROS = (
    PROCESADA / "03_siniestros_unicos.csv"
)

# Preferimos el archivo que ya tiene
# nuestras alertas de control de calidad.
RUTA_SEGURIDAD = (
    PROCESADA / "05_seguridad_controlada.csv"
)

if not RUTA_SEGURIDAD.exists():
    RUTA_SEGURIDAD = (
        PROCESADA / "04_seguridad_region_mes.csv"
    )

for ruta in (
    RUTA_MUNICIPIOS,
    RUTA_SINIESTROS,
    RUTA_SEGURIDAD
):
    if not ruta.is_file():
        raise FileNotFoundError(
            f"Archivo necesario no encontrado: {ruta}"
        )


# ==========================================
# 3. LEER ATUS + DENUE + CARTOGRAFIA
# ==========================================

municipios = pd.read_csv(
    RUTA_MUNICIPIOS,
    dtype={"cvegeo": "string"},
    encoding="utf-8-sig"
)

municipios["cvegeo"] = (
    municipios["cvegeo"]
    .str.strip()
    .str.zfill(5)
)

if len(municipios) != 125:
    raise ValueError(
        "La matriz municipal debe contener 125 municipios."
    )

if municipios["cvegeo"].duplicated().any():
    raise ValueError(
        "Hay claves municipales duplicadas."
    )

# Mantener los valores faltantes de ATUS.
# No suponemos que un municipio sin datos
# reportados equivale a cero accidentes.

municipios["registros_atus_2025"] = (
    pd.to_numeric(
        municipios["registros_atus_2025"],
        errors="coerce"
    )
)

municipios["establecimientos_denue_mayo_2025"] = (
    pd.to_numeric(
        municipios["establecimientos_denue_mayo_2025"],
        errors="coerce"
    )
)

print("\n=== ATUS + DENUE ===")
print("Municipios:", len(municipios))

print(
    "Municipios con ATUS:",
    municipios["registros_atus_2025"].notna().sum()
)

print(
    "Municipios con DENUE:",
    municipios[
        "establecimientos_denue_mayo_2025"
    ].notna().sum()
)


# ==========================================
# 4. NORMALIZAR NOMBRES MUNICIPALES
# ==========================================

def normalizar_nombre(valor):
    """
    Unifica mayusculas, acentos y signos
    para comparar nombres de municipios.
    """

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()

    texto = unicodedata.normalize(
        "NFKD", texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = re.sub(
        r"[^A-Z0-9 ]",
        " ",
        texto
    )

    return " ".join(texto.split())


# Crear diccionario:
# nombre municipal -> clave geografica

nombres_a_claves = {}

for _, fila in municipios.iterrows():

    nombre = normalizar_nombre(
        fila["municipio_cartografia"]
    )

    clave = fila["cvegeo"]

    if nombre in nombres_a_claves:
        raise ValueError(
            f"Nombre municipal ambiguo: {nombre}"
        )

    nombres_a_claves[nombre] = clave


def identificar_municipio(valor):
    """
    Identifica una clave municipal a partir
    de un nombre o codigo existente.

    No inventa coincidencias aproximadas.
    """

    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    # Si ya es una clave de cinco digitos.
    if re.fullmatch(r"14\d{3}", texto):
        if texto in set(municipios["cvegeo"]):
            return texto

    # Si es un codigo municipal de 1-3 digitos.
    if re.fullmatch(r"\d{1,3}", texto):
        clave = "14" + texto.zfill(3)

        if clave in set(municipios["cvegeo"]):
            return clave

    # Intentar coincidencia exacta por nombre.
    nombre = normalizar_nombre(texto)

    return nombres_a_claves.get(nombre)


# ==========================================
# 5. LEER SINIESTRALIMAP
# ==========================================

siniestros = pd.read_csv(
    RUTA_SINIESTROS,
    dtype={"id_siniestro": "string"},
    encoding="utf-8-sig"
)

if siniestros["id_siniestro"].duplicated().any():
    raise ValueError(
        "Hay identificadores de siniestro duplicados."
    )

# Convertir el anio a numero.
siniestros["anio"] = pd.to_numeric(
    siniestros["anio"],
    errors="coerce"
)

# Trabajaremos inicialmente con 2025.
siniestros_2025 = (
    siniestros[
        siniestros["anio"] == 2025
    ].copy()
)

siniestros_2025["cvegeo"] = (
    siniestros_2025["municipio"]
    .apply(identificar_municipio)
)

# La fuente original identifica si
# el evento cuenta con coordenadas.
siniestros_2025["coord_valida"] = (
    pd.to_numeric(
        siniestros_2025["coordenadas_validas"],
        errors="coerce"
    ) == 1
)

# Eventos que pudimos asociar a un municipio.
sin_asignar = siniestros_2025[
    siniestros_2025["cvegeo"].isna()
].copy()

sin_asignar.to_csv(
    PROCESADA
    / "08_siniestros_sin_asignar_2025.csv",
    index=False,
    encoding="utf-8-sig"
)

sin_asignados = siniestros_2025[
    siniestros_2025["cvegeo"].notna()
].copy()

if sin_asignados.empty:
    raise ValueError(
        "No se pudo asociar ningun siniestro "
        "de 2025 con la cartografia municipal. "
        "Revisa los valores de la columna municipio."
    )

print("\n=== SINIESTRALIMAP ===")

print(
    "Siniestros registrados en 2025:",
    len(siniestros_2025)
)

print(
    "Siniestros asignados a municipios:",
    len(sin_asignados)
)

print(
    "Siniestros sin asignar:",
    len(sin_asignar)
)


# ==========================================
# 6. AGRUPAR SINIESTROS POR MUNICIPIO
# ==========================================

sin_municipal = (
    sin_asignados
    .groupby("cvegeo", as_index=False)
    .agg(
        siniestros_registrados_2025=(
            "id_siniestro",
            "nunique"
        ),
        siniestros_con_coord_2025=(
            "coord_valida",
            "sum"
        )
    )
)

# ==========================================
# 7. CREAR MATRIZ MUNICIPAL INTEGRADA
# ==========================================

matriz_municipal = municipios.merge(
    sin_municipal,
    on="cvegeo",
    how="left",
    validate="one_to_one"
)

# Aquí cero significa "no hay registros
# asignados desde Siniestralimap",
# no "no ocurrieron siniestros reales".

columnas_siniestros = [
    "siniestros_registrados_2025",
    "siniestros_con_coord_2025"
]

matriz_municipal[columnas_siniestros] = (
    matriz_municipal[columnas_siniestros]
    .fillna(0)
    .astype(int)
)

matriz_municipal[
    "siniestros_sin_coord_2025"
] = (
    matriz_municipal[
        "siniestros_registrados_2025"
    ]
    - matriz_municipal[
        "siniestros_con_coord_2025"
    ]
)

# Etiqueta para no confundir ausencia
# de ATUS con un cero observado.
matriz_municipal["atus_dato_disponible"] = (
    matriz_municipal[
        "registros_atus_2025"
    ].notna()
)

if len(matriz_municipal) != 125:
    raise ValueError(
        "Se perdieron municipios durante la union."
    )

if (
    matriz_municipal[
        "siniestros_registrados_2025"
    ].sum()
    != len(sin_asignados)
):
    raise ValueError(
        "No coinciden los conteos de siniestros."
    )

ruta_matriz = (
    PROCESADA / "08_matriz_municipal_2025.csv"
)

matriz_municipal.to_csv(
    ruta_matriz,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 8. LEER PLATAFORMA DE SEGURIDAD
# ==========================================

seguridad = pd.read_csv(
    RUTA_SEGURIDAD,
    encoding="utf-8-sig"
)

seguridad["periodo"] = (
    seguridad["periodo"]
    .astype("string")
    .str.strip()
)

seguridad["cantidad"] = pd.to_numeric(
    seguridad["cantidad"],
    errors="coerce"
)

if seguridad["cantidad"].isna().any():
    raise ValueError(
        "Hay cantidades no numericas en Seguridad."
    )

# Seleccionar enero-diciembre de 2025.
seguridad_2025 = seguridad[
    seguridad["periodo"].str.fullmatch(
        r"2025-(0[1-9]|1[0-2])",
        na=False
    )
].copy()

if seguridad_2025.empty:
    raise ValueError(
        "No se encontraron registros de Seguridad "
        "para 2025."
    )

# Si usamos la salida 04 directamente,
# agregamos una etiqueta de control pendiente.
if "control_regional" not in seguridad_2025.columns:
    seguridad_2025["control_regional"] = (
        "SIN_CONTROL_ADICIONAL"
    )

# No debe haber dos conteos para la misma
# region, mes, delito y medida.
claves_seguridad = [
    "region",
    "periodo",
    "delito",
    "medida"
]

if seguridad_2025.duplicated(
    claves_seguridad
).any():
    raise ValueError(
        "Hay observaciones duplicadas en Seguridad."
    )

ruta_seguridad = (
    PROCESADA
    / "08_seguridad_region_mes_2025.csv"
)

seguridad_2025.to_csv(
    ruta_seguridad,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 9. RESUMEN ANUAL POR INDICADOR
# ==========================================

# Sumamos los meses de un mismo indicador,
# nunca delitos diferentes ni tipos de
# medida que se superponen.

resumen_seguridad = (
    seguridad_2025
    .groupby(
        ["region", "delito", "medida"],
        as_index=False
    )
    .agg(
        conteo_anual_registrado=(
            "cantidad", "sum"
        ),
        meses_observados=(
            "periodo", "nunique"
        ),
        observaciones_en_revision=(
            "control_regional",
            lambda valores: (
                valores == "REVISAR"
            ).sum()
        )
    )
)

resumen_seguridad["anio"] = 2025

resumen_seguridad[
    "serie_anual_completa"
] = (
    resumen_seguridad["meses_observados"] == 12
)

resumen_seguridad[
    "requiere_revision"
] = (
    resumen_seguridad[
        "observaciones_en_revision"
    ] > 0
)

ruta_resumen = (
    PROCESADA
    / "08_seguridad_resumen_2025.csv"
)

resumen_seguridad.to_csv(
    ruta_resumen,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 10. CONTROL DE LAS CUATRO FUENTES
# ==========================================

control = pd.DataFrame([
    {
        "fuente": "ATUS",
        "periodo": "2025",
        "escala": "municipal",
        "registros_integrados": int(
            municipios[
                "registros_atus_2025"
            ].notna().sum()
        ),
        "observacion": (
            "Municipios con registros disponibles; "
            "los faltantes permanecen como NA"
        )
    },
    {
        "fuente": "DENUE",
        "periodo": "mayo 2025",
        "escala": "municipal",
        "registros_integrados": int(
            municipios[
                "establecimientos_denue_mayo_2025"
            ].notna().sum()
        ),
        "observacion": (
            "Conteos municipales de establecimientos"
        )
    },
    {
        "fuente": "Siniestralimap",
        "periodo": "2025",
        "escala": "evento y municipio",
        "registros_integrados": len(sin_asignados),
        "observacion": (
            "Eventos unicos asignados por "
            "identificador municipal o nombre"
        )
    },
    {
        "fuente": "Plataforma de Seguridad",
        "periodo": "2025",
        "escala": "regional y mensual",
        "registros_integrados": len(seguridad_2025),
        "observacion": (
            "Observaciones por delito y medida; "
            "no se distribuyen entre municipios"
        )
    }
])

ruta_control = (
    PROCESADA
    / "08_control_integracion.csv"
)

control.to_csv(
    ruta_control,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 11. MOSTRAR RESULTADOS
# ==========================================

print("\n=== INTEGRACION HOTSPOT 2025 ===")

print("\nMatriz municipal:")
print("Municipios:", len(matriz_municipal))

print(
    "ATUS disponibles:",
    matriz_municipal[
        "atus_dato_disponible"
    ].sum()
)

print(
    "Siniestros municipales asignados:",
    matriz_municipal[
        "siniestros_registrados_2025"
    ].sum()
)

print("\nMatriz de seguridad:")

print(
    "Observaciones mensuales:",
    len(seguridad_2025)
)

print(
    "Regiones:",
    sorted(seguridad_2025["region"].unique())
)

print(
    "Indicadores anuales:",
    len(resumen_seguridad)
)

print("\n=== CONTROL DE FUENTES ===")
print(control.to_string(index=False))

print("\n=== ARCHIVOS GENERADOS ===")
print(ruta_matriz.name)
print(ruta_seguridad.name)
print(ruta_resumen.name)
print("08_siniestros_sin_asignar_2025.csv")
print(ruta_control.name)

print(
    "\nIMPORTANTE: La matriz municipal "
    "y la matriz regional no deben "
    "unirse directamente por municipio."
)
