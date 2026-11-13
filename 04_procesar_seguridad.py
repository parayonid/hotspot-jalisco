
"""
HOTSPOT - 04_procesar_seguridad.py

Objetivo:
Extraer las series historicas de incidencia delictiva
de Jalisco desde el archivo Plataforma de Seguridad.

Regiones:
    ESTADO
    AMG
    INTERIOR

Resultados:
    04_seguridad_region_mes.csv
    04_seguridad_discrepancias.csv

Este script esta adaptado a la estructura del
Excel plataforma_seguridad_al_30_09__2026.xlsx.
"""

# ============================================
# 1. IMPORTAR BIBLIOTECAS
# ============================================

from pathlib import Path
from datetime import datetime, timedelta

import csv
import re
import zipfile
import xml.etree.ElementTree as ET


# ============================================
# 2. DEFINIR RUTAS
# ============================================

# La raiz del proyecto esta un nivel arriba
# de la carpeta hotspot-mvp.

RAIZ = Path(__file__).resolve().parent.parent

# Ubicacion de nuestro archivo original.
ORIGEN = (
    RAIZ
    / "Data Cruda"
    / "seguridad"
    / "plataforma_seguridad_al_30_09__2026.xlsx"
)

# Carpeta donde guardaremos los resultados.
DESTINO = RAIZ / "Data Procesada"

DESTINO.mkdir(
    parents=True,
    exist_ok=True
)

# Comprobamos que el Excel exista.
if not ORIGEN.is_file():
    raise FileNotFoundError(
        f"No se encontro el archivo: {ORIGEN}"
    )


# ============================================
# 3. IDENTIFICAR LAS HOJAS DEL EXCEL
# ============================================

# Estas rutas corresponden al Excel original
# que estamos utilizando.

HOJAS = {
    "ESTADO": "xl/worksheets/sheet2.xml",
    "AMG": "xl/worksheets/sheet3.xml",
    "INTERIOR": "xl/worksheets/sheet4.xml",
}

# Namespace utilizado por los documentos
# XML de Microsoft Excel.

NS = (
    "{http://schemas.openxmlformats.org/"
    "spreadsheetml/2006/main}"
)


# ============================================
# 4. CONVERTIR COLUMNAS EXCEL A NUMEROS
# ============================================

def numero_columna(celda):

    # Ejemplo: "AB20" -> "AB"
    letras = re.match(
        r"[A-Z]+",
        celda
    ).group()

    n = 0

    for letra in letras:

        # Sistema de numeracion en base 26.
        n = (
            n * 26
            + ord(letra)
            - 64
        )

    return n


# ============================================
# 5. LEER EL ARCHIVO EXCEL
# ============================================

def leer_excel():

    """
    Lee las hojas seleccionadas del XLSX.

    Devuelve un diccionario:
        region -> {(fila, columna): valor}
    """

    resultado = {}

    # Los archivos XLSX contienen documentos XML.
    with zipfile.ZipFile(ORIGEN) as zip_excel:

        compartidas = []

        # Cargar los textos compartidos del Excel.
        xml = ET.fromstring(
            zip_excel.read(
                "xl/sharedStrings.xml"
            )
        )

        for elemento in xml.findall(f"{NS}si"):

            texto = "".join(
                t.text or ""
                for t in elemento.iter(f"{NS}t")
            )

            compartidas.append(texto)

        # Procesar cada region.
        for nombre, ruta in HOJAS.items():

            xml = ET.fromstring(
                zip_excel.read(ruta)
            )

            celdas = {}

            # Recorrer las celdas XML.
            for celda in xml.iter(f"{NS}c"):

                referencia = celda.get("r", "")

                match = re.match(
                    r"([A-Z]+)(\d+)",
                    referencia
                )

                if not match:
                    continue

                valor = celda.find(f"{NS}v")

                if valor is None:
                    continue

                dato = valor.text or ""

                # Recuperar texto compartido.
                if celda.get("t") == "s":

                    dato = compartidas[
                        int(dato)
                    ]

                fila = int(match.group(2))
                columna = numero_columna(
                    referencia
                )

                celdas[(fila, columna)] = dato

            resultado[nombre] = celdas

    return resultado


# ============================================
# 6. VALIDAR CANTIDADES
# ============================================

def cantidad(dato):

    # Un valor vacio no equivale a cero.
    if (
        dato is None
        or str(dato).strip() == ""
    ):
        return None

    try:

        numero = float(dato)

        # Solo aceptamos enteros no negativos.
        if (
            numero.is_integer()
            and numero >= 0
        ):
            return int(numero)

        return None

    except ValueError:
        return None


# ============================================
# 7. EXTRAER LAS SERIES TEMPORALES
# ============================================

hojas = leer_excel()

registros = []

meses_por_region = {}

for region, celdas in hojas.items():

    meses = set()

    # Cada mes ocupa tres columnas.
    # B, E, H, K, N, etc.

    for col in range(2, 323, 3):

        # La fecha se encuentra en la fila 3.
        serial = cantidad(
            celdas.get((3, col))
        )

        # Validamos que sea una fecha de Excel
        # dentro del intervalo previsto.
        if (
            serial is None
            or not 40000 <= serial <= 55000
        ):
            continue

        # Convertir fecha serial de Excel.
        fecha = (
            datetime(1899, 12, 30)
            + timedelta(days=serial)
        )

        mes = fecha.strftime("%Y-%m")

        meses.add(mes)

        # ------------------------------------
        # FUNCION INTERNA PARA AGREGAR DATOS
        # ------------------------------------

        def agregar(
            fila,
            medida,
            desplazamiento=0
        ):

            # Recuperar nombre del delito.
            delito = str(
                celdas.get((fila, 1), "")
            ).strip().rstrip("*").strip()

            # Recuperar cantidad.
            valor = cantidad(
                celdas.get(
                    (
                        fila,
                        col + desplazamiento
                    )
                )
            )

            # Evitar registros sin datos.
            if delito and valor is not None:

                registros.append([
                    region,
                    mes,
                    delito,
                    medida,
                    valor,
                    fila
                ])

        # ------------------------------------
        # A. INDICADORES GENERALES
        # ------------------------------------

        # Incluye incidencia total, secuestro,
        # lesiones, violencia familiar y otros
        # indicadores de las filas seleccionadas.

        for fila in (
            4, 17, 31, 32, 33, 34, 35
        ):

            agregar(
                fila,
                "REGISTROS"
            )

        # ------------------------------------
        # B. ROBOS
        # ------------------------------------

        # Cada robo tiene tres medidas:
        # con violencia, sin violencia y total.

        for fila in range(7, 16):

            for desplazamiento, medida in enumerate(
                (
                    "CON_VIOLENCIA",
                    "SIN_VIOLENCIA",
                    "TOTAL"
                )
            ):

                agregar(
                    fila,
                    medida,
                    desplazamiento
                )

        # ------------------------------------
        # C. HOMICIDIOS Y FEMINICIDIOS
        # ------------------------------------

        # Conservamos eventos y victimas
        # como variables independientes.

        for fila in (20, 26):

            agregar(
                fila,
                "EVENTOS",
                0
            )

            agregar(
                fila,
                "VICTIMAS",
                1
            )

    meses_por_region[region] = len(meses)


# ============================================
# 8. EXPORTAR SERIES TEMPORALES
# ============================================

columnas = [
    "region",
    "periodo",
    "delito",
    "medida",
    "cantidad",
    "fila_excel"
]

ruta_series = (
    DESTINO
    / "04_seguridad_region_mes.csv"
)

with ruta_series.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as archivo:

    writer = csv.writer(archivo)

    writer.writerow(columnas)

    writer.writerows(
        sorted(registros)
    )


# ============================================
# 9. VALIDACION DE CONSISTENCIA REGIONAL
# ============================================

# Transformamos los registros en un diccionario.
# La clave identifica:
# region + mes + delito + medida.

valores = {
    (r, m, d, t): n
    for r, m, d, t, n, _ in registros
}

# Verificamos que no existan claves repetidas.
assert len(valores) == len(registros), (
    "Se encontraron registros duplicados"
)

diferencias = []

comprobadas = 0

# Recorremos los datos estatales.
for (
    region,
    mes,
    delito,
    medida
), estado in valores.items():

    if region != "ESTADO":
        continue

    # Buscar la misma observacion en AMG.
    amg = valores.get(
        (
            "AMG",
            mes,
            delito,
            medida
        )
    )

    # Buscar la misma observacion en Interior.
    interior = valores.get(
        (
            "INTERIOR",
            mes,
            delito,
            medida
        )
    )

    # Comparamos cuando ambas regiones
    # tienen una observacion numerica.
    if (
        amg is not None
        and interior is not None
    ):

        comprobadas += 1

        # El total estatal deberia coincidir
        # con la suma de ambas regiones.
        if estado != amg + interior:

            diferencias.append([
                mes,
                delito,
                medida,
                estado,
                amg,
                interior
            ])


# ============================================
# 10. EXPORTAR DISCREPANCIAS
# ============================================

ruta_revision = (
    DESTINO
    / "04_seguridad_discrepancias.csv"
)

with ruta_revision.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as archivo:

    writer = csv.writer(archivo)

    writer.writerow([
        "periodo",
        "delito",
        "medida",
        "estado",
        "amg",
        "interior"
    ])

    writer.writerows(diferencias)


# ============================================
# 11. MOSTRAR RESULTADOS
# ============================================

print(
    "\n=== PLATAFORMA DE SEGURIDAD PROCESADA ==="
)

print(
    "Meses por region:",
    meses_por_region
)

print(
    "Filas de series mensuales:",
    len(registros)
)

print(
    "Comparaciones verificadas:",
    comprobadas
)

print(
    "Discrepancias para revisar:",
    len(diferencias)
)

print(
    "Archivo:",
    ruta_series.name
)

print(
    "Control de calidad:",
    ruta_revision.name
)

print(
    "\nAVISO: Estas estadisticas no contienen "
    "ubicaciones individuales de delitos."
)
