
"""HOTSPOT | Etapa 21.5: sensibilidad de concentraciones espaciales.

Desde hotspot-mvp:
  ..\\.venv\\Scripts\\python.exe .\\21_validar_estabilidad_siniestros.py

Entradas:
  datos/siniestros.geojson
  datos/21_resumen_zonas.json
  datos/21_zonas_siniestros.geojson

Salidas:
  datos/21_estabilidad_zonas_2025.geojson
  ../Data Procesada/21_resumen_estabilidad.json
  ../Data Procesada/21_escenarios_estabilidad.csv
  ../Data Procesada/21_estabilidad_eventos_2025.csv

Criterio: como en Etapa 21.1, umbral entero >= 3 y como
maximo 10% de celdas activas, conservando empates.

No representa riesgo vial ni validacion predictiva.
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
SALIDA = BASE.parent / "Data Procesada"

SALIDA.mkdir(parents=True, exist_ok=True)

ANIO_FOCO = 2025

FRACCION_SUPERIOR = 0.10
MINIMO_REGISTROS = 3

TAMANOS_M = (500, 1000, 2000)

DESPLAZAMIENTOS = (
    (0.0, 0.0),
    (0.5, 0.0),
    (0.0, 0.5),
    (0.5, 0.5)
)

ANIOS_COMPARACION = (2023, 2024)


# ==========================================
# 2. LEER Y EXPORTAR ARCHIVOS
# ==========================================

def cargar(nombre):

    ruta = DATOS / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"Falta {ruta}"
        )

    with ruta.open(
        encoding="utf-8-sig"
    ) as archivo:

        return json.load(archivo)


def escribir_json(ruta, objeto, compacto=False):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    opciones = (
        {"separators": (",", ":")}
        if compacto
        else {"indent": 2}
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
            **opciones
        )

    print(
        f"Generado: {ruta.name} "
        f"({ruta.stat().st_size:,} bytes)"
    )


def escribir_csv(ruta, filas, campos):

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        writer = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        writer.writeheader()
        writer.writerows(filas)

    print(
        f"Generado: {ruta.name} "
        f"({len(filas):,} filas)"
    )


# ==========================================
# 3. CRITERIO ORIGINAL DE ZONAS DESTACADAS
# ==========================================

def foco_por_conteo(conteos):

    if not conteos:
        return None, set()

    limite = max(
        1,
        math.ceil(
            FRACCION_SUPERIOR * len(conteos)
        )
    )

    candidatos = sorted(
        set(conteos.values())
    )

    validos = [

        umbral
        for umbral in candidatos

        if umbral >= MINIMO_REGISTROS

        and sum(
            n >= umbral
            for n in conteos.values()
        ) <= limite
    ]

    if not validos:
        return None, set()

    umbral = min(validos)

    focos = {
        clave
        for clave, n in conteos.items()
        if n >= umbral
    }

    return umbral, focos


# ==========================================
# 4. IDENTIFICAR CELDA DE UN EVENTO
# ==========================================

def indice_celda(x, y, lado, fx, fy):

    return (
        math.floor(x / lado - fx),
        math.floor(y / lado - fy)
    )


# ==========================================
# 5. CONSTRUIR UN ESCENARIO
# ==========================================

def construir_escenario(
    eventos,
    lado,
    fx,
    fy,
    anio
):

    registros = [
        e
        for e in eventos
        if e["anio"] == anio
    ]

    conteos = Counter(

        indice_celda(
            e["x"],
            e["y"],
            lado,
            fx,
            fy
        )

        for e in registros
    )

    umbral, focos = foco_por_conteo(
        conteos
    )

    ids_destacados = {

        e["id"]
        for e in registros

        if indice_celda(
            e["x"],
            e["y"],
            lado,
            fx,
            fy
        ) in focos
    }

    return {
        "conteos": conteos,
        "umbral": umbral,
        "focos": focos,
        "ids": ids_destacados,
        "n_eventos": len(registros)
    }


# ==========================================
# 6. CARGAR Y PROYECTAR LOS SINIESTROS
# ==========================================

def leer_eventos():

    fuente = cargar(
        "siniestros.geojson"
    )

    if fuente.get("type") != "FeatureCollection":
        raise ValueError(
            "GeoJSON de siniestros invalido"
        )

    transformar = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6368",
        always_xy=True
    )

    eventos = []
    ids = set()

    for i, feature in enumerate(
        fuente.get("features", [])
    ):

        props = feature.get(
            "properties"
        ) or {}

        geom = feature.get(
            "geometry"
        ) or {}

        coords = geom.get(
            "coordinates"
        ) or []

        if (
            geom.get("type") != "Point"
            or len(coords) < 2
        ):
            raise ValueError(
                f"Geometria invalida: {i}"
            )

        identificador = str(

            props.get("id_siniestro")

            or feature.get("id")

            or ""

        ).strip()

        if (
            not identificador
            or identificador in ids
        ):
            raise ValueError(
                f"ID vacio o duplicado: {i}"
            )

        ids.add(identificador)

        anio = int(
            props["anio"]
        )

        lon = float(
            coords[0]
        )

        lat = float(
            coords[1]
        )

        if not (
            2015 <= anio <= 2025
            and math.isfinite(lon)
            and math.isfinite(lat)
            and -106.5 <= lon <= -101.0
            and 18 <= lat <= 23.5
        ):
            raise ValueError(
                f"Evento fuera de dominio: "
                f"{identificador}"
            )

        x, y = transformar.transform(
            lon,
            lat
        )

        if not (
            math.isfinite(x)
            and math.isfinite(y)
        ):
            raise ValueError(
                "Proyeccion geografica invalida"
            )

        eventos.append({
            "id": identificador,
            "anio": anio,
            "x": x,
            "y": y
        })

    return eventos


# ==========================================
# 7. SIMILITUD DE JACCARD
# ==========================================

def jaccard(a, b):

    union = a | b

    if not union:
        return None

    return len(a & b) / len(union)


# ==========================================
# 8. EJECUCION PRINCIPAL
# ==========================================

def main():

    eventos = leer_eventos()

    resumen = cargar(
        "21_resumen_zonas.json"
    )

    zonas = cargar(
        "21_zonas_siniestros.geojson"
    )

    anos = Counter(
        e["anio"]
        for e in eventos
    )

    if (
        len(eventos) != resumen[
            "total_eventos_georreferenciados"
        ]
    ):
        raise ValueError(
            "Total historico inconsistente"
        )

    for year in range(2015, 2026):

        if anos[year] != resumen[
            "eventos_por_anio"
        ][str(year)]:

            raise ValueError(
                f"Descuadre en {year}"
            )

    # ======================================
    # 9. RECONSTRUIR CASO BASE DE 2025
    # ======================================

    base = construir_escenario(
        eventos,
        1000,
        0,
        0,
        ANIO_FOCO
    )

    if (
        len(base["conteos"]) != resumen[
            "celdas_con_eventos_2025"
        ]
        or base["umbral"] != resumen[
            "umbral_eventos_2025"
        ]
        or len(base["focos"]) != resumen[
            "celdas_alta_concentracion_2025"
        ]
        or len(base["ids"]) != resumen[
            "eventos_2025_en_celdas_alta_concentracion"
        ]
    ):
        raise ValueError(
            "El caso base no coincide "
            "con la Etapa 21.1"
        )

    print(
        "Caso base verificado:",
        len(base["focos"]),
        "zonas,",
        len(base["ids"]),
        "eventos"
    )

    # ======================================
    # 10. PROBAR 12 CONFIGURACIONES
    # ======================================

    escenarios = []

    flags = defaultdict(int)

    for lado in TAMANOS_M:

        for fx, fy in DESPLAZAMIENTOS:

            escenario = construir_escenario(
                eventos,
                lado,
                fx,
                fy,
                ANIO_FOCO
            )

            etiqueta = (
                f"{lado}m_"
                f"dx{int(fx * 100)}_"
                f"dy{int(fy * 100)}"
            )

            destacados = escenario["ids"]

            for identificador in destacados:
                flags[identificador] += 1

            compartidos = len(
                base["ids"] & destacados
            )

            escenarios.append({

                "escenario": etiqueta,

                "lado_celda_m": lado,

                "desplazamiento_x_fraccion": fx,

                "desplazamiento_y_fraccion": fy,

                "celdas_activas":
                    len(escenario["conteos"]),

                "umbral_eventos":
                    escenario["umbral"],

                "celdas_destacadas":
                    len(escenario["focos"]),

                "eventos_destacados":
                    len(destacados),

                "fraccion_eventos_destacados":
                    round(
                        len(destacados)
                        / base["n_eventos"],
                        6
                    ),

                "jaccard_eventos_vs_base":
                    round(
                        jaccard(
                            base["ids"],
                            destacados
                        ),
                        6
                    ),

                "retencion_eventos_base":
                    round(
                        compartidos
                        / len(base["ids"]),
                        6
                    )
            })

    # ======================================
    # 11. ESTABILIDAD POR EVENTO
    # ======================================

    total_escenarios = len(
        escenarios
    )

    eventos_2025 = [
        e
        for e in eventos
        if e["anio"] == 2025
    ]

    detalle = []

    por_celda_base = defaultdict(list)

    for e in eventos_2025:

        ix, iy = indice_celda(
            e["x"],
            e["y"],
            1000,
            0,
            0
        )

        celda_id = f"C_{ix}_{iy}"

        frecuencia = flags[
            e["id"]
        ]

        por_celda_base[
            celda_id
        ].append(frecuencia)

        detalle.append({

            "id_siniestro": e["id"],

            "celda_base_1km": celda_id,

            "destacado_base_2025":
                int(e["id"] in base["ids"]),

            "escenarios_destacado":
                frecuencia,

            "fraccion_escenarios":
                round(
                    frecuencia / total_escenarios,
                    6
                )
        })

    # ======================================
    # 12. COMPARACION ENTRE AÑOS
    # ======================================

    comparaciones = []

    focos_por_anio = {}

    for anio in (
        *ANIOS_COMPARACION,
        ANIO_FOCO
    ):

        escenario = construir_escenario(
            eventos,
            1000,
            0,
            0,
            anio
        )

        focos_por_anio[
            anio
        ] = escenario["focos"]

        if anio == ANIO_FOCO:
            continue

        comparaciones.append({

            "anio": anio,

            "registros_georreferenciados":
                escenario["n_eventos"],

            "celdas_activas":
                len(escenario["conteos"]),

            "umbral_eventos":
                escenario["umbral"],

            "celdas_destacadas":
                len(escenario["focos"]),

            "celdas_compartidas_con_2025":
                len(
                    escenario["focos"]
                    & base["focos"]
                ),

            "jaccard_celdas_2025":
                round(
                    jaccard(
                        escenario["focos"],
                        base["focos"]
                    ),
                    6
                )
        })

    # ======================================
    # 13. GENERAR GEOJSON DE ESTABILIDAD
    # ======================================

    if zonas.get("type") != "FeatureCollection":
        raise ValueError(
            "GeoJSON de zonas invalido"
        )

    ids_focos_base = {

        f"C_{ix}_{iy}"

        for ix, iy in base["focos"]
    }

    nuevas_features = []

    for feature in zonas["features"]:

        p = dict(
            feature["properties"]
        )

        clave = str(
            p["id_celda"]
        )

        if (
            p["alta_concentracion_2025"]
            != (clave in ids_focos_base)
        ):
            raise ValueError(
                f"Foco inconsistente: {clave}"
            )

        frecuencias = por_celda_base.get(
            clave,
            []
        )

        p["eventos_2025_en_celda"] = len(
            frecuencias
        )

        p["promedio_estabilidad_eventos"] = (

            round(
                sum(frecuencias)
                / (
                    len(frecuencias)
                    * total_escenarios
                ),
                6
            )

            if frecuencias else None
        )

        posicion = (
            p["indice_x"],
            p["indice_y"]
        )

        p["destacada_2023_1km"] = (
            posicion in focos_por_anio[2023]
        )

        p["destacada_2024_1km"] = (
            posicion in focos_por_anio[2024]
        )

        nuevas_features.append({
            **feature,
            "properties": p
        })

    # ======================================
    # 14. RESUMEN DE ESTABILIDAD
    # ======================================

    n6 = sum(
        flags[e["id"]] >= 6
        for e in eventos_2025
    )

    n9 = sum(
        flags[e["id"]] >= 9
        for e in eventos_2025
    )

    n12 = sum(
        flags[e["id"]] == total_escenarios
        for e in eventos_2025
    )

    informe = {

        "metodo":
            "Sensibilidad descriptiva de "
            "concentraciones espaciales 2025",

        "configuracion": {

            "crs_metrico": "EPSG:6368",

            "lado_celdas_m":
                list(TAMANOS_M),

            "desplazamientos":
                list(DESPLAZAMIENTOS),

            "numero_escenarios":
                total_escenarios
        },

        "caso_base_2025": {

            "registros":
                base["n_eventos"],

            "celdas_activas":
                len(base["conteos"]),

            "celdas_destacadas":
                len(base["focos"]),

            "eventos_en_destacadas":
                len(base["ids"]),

            "umbral":
                base["umbral"]
        },

        "sensibilidad_espacial_2025": {

            "escenarios": escenarios,

            "eventos_en_6_o_mas_escenarios":
                n6,

            "eventos_en_9_o_mas_escenarios":
                n9,

            "eventos_en_12_escenarios":
                n12
        },

        "comparacion_temporal":
            comparaciones,

        "advertencias": [

            "No es validacion predictiva.",

            "Los mismos eventos de 2025 "
            "se utilizan para seleccionar "
            "y comparar las zonas.",

            "Los cambios de cobertura de "
            "Siniestralimap pueden afectar "
            "la comparacion temporal.",

            "Los puntos son aproximados.",

            "El criterio de concentracion "
            "no implica significancia "
            "estadistica ni riesgo vial."
        ]
    }

    # ======================================
    # 15. EXPORTAR RESULTADOS
    # ======================================

    escribir_json(

        DATOS
        / "21_estabilidad_zonas_2025.geojson",

        {
            "type": "FeatureCollection",
            "features": nuevas_features
        },

        compacto=True
    )

    escribir_json(

        SALIDA
        / "21_resumen_estabilidad.json",

        informe
    )

    escribir_csv(

        SALIDA
        / "21_escenarios_estabilidad.csv",

        escenarios,

        list(escenarios[0])
    )

    escribir_csv(

        SALIDA
        / "21_estabilidad_eventos_2025.csv",

        detalle,

        list(detalle[0])
    )

    # ======================================
    # 16. MOSTRAR RESULTADOS
    # ======================================

    print(
        "\n=== ETAPA 21.5 | "
        "ESTABILIDAD DE CONCENTRACIONES ==="
    )

    print(
        "Total eventos 2025:",
        base["n_eventos"]
    )

    print(
        "Escenarios:",
        total_escenarios
    )

    print(
        "Caso base:",
        len(base["focos"]),
        "zonas destacadas"
    )

    print(
        "Eventos en al menos 6 escenarios:",
        n6
    )

    print(
        "Eventos en al menos 9 escenarios:",
        n9
    )

    print(
        "Eventos en los 12 escenarios:",
        n12
    )

    for fila in comparaciones:

        print(
            f"{fila['anio']} vs 2025:",
            fila["celdas_compartidas_con_2025"],
            "celdas compartidas",
            "| Jaccard:",
            fila["jaccard_celdas_2025"]
        )

    print(
        "Nota: sensibilidad descriptiva, "
        "no validacion de riesgo."
    )


if __name__ == "__main__":
    main()
