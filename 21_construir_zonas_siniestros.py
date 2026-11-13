
r"""HOTSPOT | Etapa 21.1

Construccion de zonas espaciales de siniestros.

Ejecutar desde hotspot-mvp:

    ..\.venv\Scripts\python.exe .\21_construir_zonas_siniestros.py

ENTRADA:
    datos/siniestros.geojson

SALIDAS:
    datos/21_zonas_siniestros.geojson
    datos/21_resumen_zonas.json

    ../Data Procesada/21_matriz_zonas_siniestros.csv
    ../Data Procesada/21_asignacion_eventos_zonas.csv

La cuadricula utiliza celdas de 1000 x 1000 metros
en EPSG:6368.

Las concentraciones son descriptivas.
No representan riesgo vial validado.
"""

from collections import Counter, defaultdict
from pathlib import Path

import csv
import json
import math

from pyproj import Transformer


# ==========================================
# 1. CONFIGURACION
# ==========================================

BASE = Path(__file__).resolve().parent

DATOS = BASE / "datos"

PROCESADA = BASE.parent / "Data Procesada"

LADO_CELDA_M = 1000

ANIO_FOCO = 2025

ANIOS = list(range(2015, 2026))

FRACCION_SUPERIOR = 0.10

MIN_REGISTROS_FOCO = 3


# ==========================================
# 2. EXPORTAR JSON
# ==========================================

def escribir_json(ruta, objeto):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            objeto,
            archivo,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )

    print(
        f"Generado: {ruta.name} "
        f"({ruta.stat().st_size:,} bytes)"
    )


# ==========================================
# 3. EXPORTAR CSV
# ==========================================

def escribir_csv(ruta, columnas, filas):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:

        writer = csv.DictWriter(
            archivo,
            fieldnames=columnas
        )

        writer.writeheader()

        writer.writerows(filas)

    print(
        f"Generado: {ruta.name} "
        f"({len(filas):,} filas)"
    )


# ==========================================
# 4. DEFINIR ZONAS DE CONCENTRACION
# ==========================================

def contar_focos(conteos):

    """
    Selecciona las celdas del extremo
    superior de la distribucion anual.

    Conserva todos los empates en el umbral
    y no supera 10% de las celdas activas.

    No es una prueba de significancia.
    """

    if not conteos:
        return None, 0

    limite = max(
        1,
        math.ceil(
            FRACCION_SUPERIOR * len(conteos)
        )
    )

    candidatos = sorted({
        n
        for n in conteos
        if n >= MIN_REGISTROS_FOCO
    })

    validos = [
        umbral
        for umbral in candidatos
        if sum(
            n >= umbral
            for n in conteos
        ) <= limite
    ]

    if not validos:
        return None, 0

    umbral = min(validos)

    cantidad = sum(
        n >= umbral
        for n in conteos
    )

    return umbral, cantidad


# ==========================================
# 5. PROCESAMIENTO PRINCIPAL
# ==========================================

def main():

    fuente = DATOS / "siniestros.geojson"

    if not fuente.is_file():

        raise FileNotFoundError(
            f"Falta {fuente}. "
            "Ejecuta primero la Etapa 15."
        )

    with fuente.open(
        encoding="utf-8-sig"
    ) as archivo:

        geojson = json.load(archivo)

    if geojson.get("type") != "FeatureCollection":

        raise ValueError(
            "La fuente no es un "
            "GeoJSON FeatureCollection."
        )

    eventos = geojson.get("features")

    if (
        not isinstance(eventos, list)
        or not eventos
    ):

        raise ValueError(
            "No se encontraron siniestros."
        )

    # ======================================
    # 6. TRANSFORMACIONES GEOGRAFICAS
    # ======================================

    convertir = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6368",
        always_xy=True
    )

    regresar = Transformer.from_crs(
        "EPSG:6368",
        "EPSG:4326",
        always_xy=True
    )

    # ======================================
    # 7. CREAR ESTRUCTURAS
    # ======================================

    celdas = defaultdict(
        lambda: {

            "por_anio": Counter(),

            "municipios_foco": Counter()
        }
    )

    conteos_anuales = Counter()

    asignaciones = []

    ids = set()

    # ======================================
    # 8. PROCESAR TODOS LOS EVENTOS
    # ======================================

    for indice, evento in enumerate(eventos):

        geom = evento.get("geometry") or {}

        props = evento.get("properties") or {}

        coord = geom.get("coordinates")

        if (
            geom.get("type") != "Point"
            or not isinstance(
                coord,
                (list, tuple)
            )
            or len(coord) < 2
        ):

            raise ValueError(
                f"Evento {indice}: "
                "se esperaba Point [lon,lat]."
            )

        try:

            lon = float(coord[0])

            lat = float(coord[1])

            anio = int(props["anio"])

        except (
            ValueError,
            TypeError,
            KeyError
        ) as error:

            raise ValueError(
                f"Evento {indice}: "
                "coordenadas o año invalidos."
            ) from error

        # ==================================
        # 9. VALIDAR COORDENADAS
        # ==================================

        if not (
            math.isfinite(lon)
            and math.isfinite(lat)
        ):

            raise ValueError(
                f"Evento {indice}: "
                "coordenadas no finitas."
            )

        if not (
            -106.5 <= lon <= -101.0
            and 18.0 <= lat <= 23.5
        ):

            raise ValueError(
                f"Evento {indice}: "
                "coordenada fuera de Jalisco: "
                f"{(lon, lat)}"
            )

        if anio not in ANIOS:

            raise ValueError(
                f"Evento {indice}: "
                f"año inesperado {anio}."
            )

        # ==================================
        # 10. IDENTIFICADOR DEL EVENTO
        # ==================================

        event_id = str(
            props.get("id_siniestro")
            or evento.get("id")
            or ""
        ).strip()

        if (
            not event_id
            or event_id in ids
        ):

            raise ValueError(
                f"Evento {indice}: "
                "ID vacio o duplicado "
                f"{event_id!r}"
            )

        ids.add(event_id)

        # ==================================
        # 11. ASIGNAR EVENTO A CELDA
        # ==================================

        x, y = convertir.transform(
            lon,
            lat
        )

        ix = math.floor(
            x / LADO_CELDA_M
        )

        iy = math.floor(
            y / LADO_CELDA_M
        )

        clave = (ix, iy)

        celda_id = f"C_{ix}_{iy}"

        celdas[clave][
            "por_anio"
        ][anio] += 1

        conteos_anuales[anio] += 1

        if anio == ANIO_FOCO:

            nombre = str(
                props.get("municipio")
                or "No especificado"
            ).strip()

            celdas[clave][
                "municipios_foco"
            ][nombre] += 1

        asignaciones.append({

            "id_siniestro": event_id,

            "anio": anio,

            "id_celda": celda_id
        })

    # ======================================
    # 12. IDENTIFICAR CELDAS ACTIVAS
    # ======================================

    activas = [

        info["por_anio"][ANIO_FOCO]

        for info in celdas.values()

        if info["por_anio"][ANIO_FOCO] > 0
    ]

    umbral, cantidad_focos = contar_focos(
        activas
    )

    features = []

    matriz = []

    total_focos = 0

    # ======================================
    # 13. CONSTRUIR POLIGONOS DE 1 KM
    # ======================================

    for (ix, iy), info in sorted(
        celdas.items()
    ):

        x0 = ix * LADO_CELDA_M

        y0 = iy * LADO_CELDA_M

        x1 = x0 + LADO_CELDA_M

        y1 = y0 + LADO_CELDA_M

        esquinas_metros = [

            (x0, y0),

            (x1, y0),

            (x1, y1),

            (x0, y1),

            (x0, y0)
        ]

        # Convertir poligono a lon/lat.

        esquinas = []

        for xx, yy in esquinas_metros:

            lon, lat = regresar.transform(
                xx,
                yy
            )

            esquinas.append([
                round(lon, 7),
                round(lat, 7)
            ])

        # Centro geografico de la celda.

        lonc, latc = regresar.transform(

            (x0 + x1) / 2,

            (y0 + y1) / 2
        )

        conteos = info["por_anio"]

        conteo_foco = conteos[ANIO_FOCO]

        es_foco = (
            umbral is not None
            and conteo_foco >= umbral
        )

        if es_foco:

            total_focos += conteo_foco

        # Municipio mas mencionado
        # dentro de la celda en 2025.

        municipio_frecuente = None

        if info["municipios_foco"]:

            municipio_frecuente = (
                info["municipios_foco"]
                .most_common(1)[0][0]
            )

        # ==================================
        # 14. ATRIBUTOS DE CADA CELDA
        # ==================================

        propiedades = {

            "id_celda": f"C_{ix}_{iy}",

            "indice_x": ix,

            "indice_y": iy,

            "centro_lon": round(
                lonc, 7
            ),

            "centro_lat": round(
                latc, 7
            ),

            "centro_x_m": round(
                (x0 + x1) / 2, 2
            ),

            "centro_y_m": round(
                (y0 + y1) / 2, 2
            ),

            "conteo_2025": conteo_foco,

            "conteo_2015_2025": sum(
                conteos.values()
            ),

            "alta_concentracion_2025":
                es_foco,

            "municipio_reportado_frecuente_2025":
                municipio_frecuente
        }

        # Guardar conteos de cada año.

        propiedades.update({

            f"n_{anio}": conteos[anio]

            for anio in ANIOS
        })

        # ==================================
        # 15. CREAR FEATURE GEOJSON
        # ==================================

        features.append({

            "type": "Feature",

            "id": propiedades[
                "id_celda"
            ],

            "geometry": {

                "type": "Polygon",

                "coordinates": [
                    esquinas
                ]
            },

            "properties": propiedades
        })

        matriz.append(
            propiedades
        )

    # ======================================
    # 16. AUDITORIA DE CONTEOS
    # ======================================

    total_reconstruido = sum(

        celda["conteo_2015_2025"]

        for celda in matriz
    )

    if total_reconstruido != len(eventos):

        raise AssertionError(
            "No se conservaron "
            "todos los siniestros."
        )

    for anio in ANIOS:

        total_anual = sum(

            celda[f"n_{anio}"]

            for celda in matriz
        )

        if total_anual != conteos_anuales[anio]:

            raise AssertionError(
                "Descuadre de conteos "
                f"en {anio}."
            )

    if len(asignaciones) != len(ids):

        raise AssertionError(
            "La asignacion de eventos "
            "no es uno-a-uno."
        )

    # ======================================
    # 17. CREAR RESUMEN
    # ======================================

    top_10 = sorted(

        matriz,

        key=lambda celda: (

            -celda["conteo_2025"],

            celda["id_celda"]
        )
    )[:10]

    resumen = {

        "metodo":
            "Cuadricula fija de 1000 x 1000 m, EPSG:6368",

        "crs_geojson_salida":
            "EPSG:4326",

        "lado_celda_m":
            LADO_CELDA_M,

        "anio_foco":
            ANIO_FOCO,

        "total_eventos_georreferenciados":
            len(eventos),

        "eventos_por_anio": {

            str(anio): conteos_anuales[anio]

            for anio in ANIOS
        },

        "celdas_con_eventos_2015_2025":
            len(celdas),

        "celdas_con_eventos_2025":
            len(activas),

        "criterio_alta_concentracion_2025": (
            "Umbral entero minimo de al menos "
            "3 eventos/celda, conservando "
            "empates y sin superar 10% de "
            "celdas activas en 2025. "
            "Criterio descriptivo."
        ),

        "umbral_eventos_2025":
            umbral,

        "celdas_alta_concentracion_2025":
            cantidad_focos,

        "eventos_2025_en_celdas_alta_concentracion":
            total_focos,

        "top_10_celdas_2025": [

            {

                "id_celda": celda["id_celda"],

                "eventos_2025":
                    celda["conteo_2025"],

                "centro_lon":
                    celda["centro_lon"],

                "centro_lat":
                    celda["centro_lat"]

            }

            for celda in top_10
        ],

        "limitaciones": [

            "Las coordenadas de Siniestralimap "
            "pueden ser aproximadas.",

            "La fuente tiene cobertura "
            "territorial limitada.",

            "La concentracion es descriptiva, "
            "no una prueba inferencial.",

            "Los conteos no son tasas "
            "de riesgo vial.",

            "Todavia no se han creado "
            "aristas entre zonas."
        ]
    }

    # ======================================
    # 18. EXPORTAR RESULTADOS
    # ======================================

    escribir_json(

        DATOS / "21_zonas_siniestros.geojson",

        {

            "type": "FeatureCollection",

            "features": features
        }
    )

    escribir_json(

        DATOS / "21_resumen_zonas.json",

        resumen
    )

    escribir_csv(

        PROCESADA
        / "21_matriz_zonas_siniestros.csv",

        list(matriz[0]),

        matriz
    )

    escribir_csv(

        PROCESADA
        / "21_asignacion_eventos_zonas.csv",

        [
            "id_siniestro",
            "anio",
            "id_celda"
        ],

        asignaciones
    )

    # ======================================
    # 19. RESULTADOS EN TERMINAL
    # ======================================

    print(
        "\n=== ETAPA 21.1 | "
        "ZONAS DE CONCENTRACION ==="
    )

    print(
        "Eventos 2015-2025:",
        f"{len(eventos):,}"
    )

    print(
        "Eventos 2025:",
        f"{conteos_anuales[ANIO_FOCO]:,}"
    )

    print(
        "Celdas activas historicas:",
        f"{len(celdas):,}"
    )

    print(
        "Celdas activas en 2025:",
        f"{len(activas):,}"
    )

    print(
        "Umbral descriptivo 2025:",
        umbral,
        "registros/celda"
    )

    print(
        "Zonas destacadas 2025:",
        cantidad_focos
    )

    print(
        "Eventos en esas zonas:",
        total_focos
    )

    print(
        "Integridad: todos los eventos "
        "tienen una sola celda."
    )

    print(
        "Nota: las zonas no representan "
        "probabilidades de riesgo."
    )


if __name__ == "__main__":
    main()
