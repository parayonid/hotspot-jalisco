
r"""HOTSPOT | Etapa 21.2: grafo espacial de siniestros.

ENTRADAS:
    datos/21_zonas_siniestros.geojson
    datos/21_resumen_zonas.json

SALIDAS:
    datos/21_grafo_siniestros.json
    datos/21_grafo_siniestros_2025.json
    datos/21_aristas_siniestros_2025.geojson

    ../Data Procesada/21_resumen_grafo_siniestros.json
    ../Data Procesada/21_metricas_grafo_siniestros.csv

Las aristas representan vecindad de celdas,
no conexiones viales ni relaciones causales.
"""

import csv
import json
import math

from collections import deque
from pathlib import Path


# ==========================================
# 1. CONFIGURACION
# ==========================================

BASE = Path(__file__).resolve().parent

DATOS = BASE / "datos"

REPORTES = BASE.parent / "Data Procesada"

ANIO_FOCO = 2025

LADO_CELDA_M = 1000

ANIOS = range(2015, 2026)

# Vecindad de reina: lados y diagonales.
# Cuatro direcciones para no duplicar aristas.

DIRECCIONES = [
    (1, 0),
    (0, 1),
    (1, 1),
    (1, -1)
]


# ==========================================
# 2. LEER ARCHIVOS
# ==========================================

def leer(nombre):

    ruta = DATOS / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"Falta {ruta}. "
            "Ejecuta la Etapa 21.1."
        )

    with ruta.open(
        encoding="utf-8-sig"
    ) as archivo:

        return json.load(archivo)


# ==========================================
# 3. GUARDAR JSON
# ==========================================

def guardar_json(ruta, objeto):

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
# 4. VALIDAR CONTEOS
# ==========================================

def entero_no_negativo(valor, campo):

    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
    ):
        raise ValueError(
            f"{campo}: entero esperado; "
            f"llego {valor!r}"
        )

    if (
        not math.isfinite(valor)
        or valor < 0
        or int(valor) != valor
    ):
        raise ValueError(
            f"{campo}: conteo invalido"
        )

    return int(valor)


# ==========================================
# 5. CARGAR CELDAS
# ==========================================

def leer_celdas(geojson, resumen):

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            "GeoJSON de zonas invalido."
        )

    features = geojson.get(
        "features", []
    )

    por_coord = {}
    por_id = {}

    total_anual = {
        year: 0
        for year in ANIOS
    }

    for feature in features:

        p = feature.get(
            "properties", {}
        )

        ix = p.get("indice_x")
        iy = p.get("indice_y")

        if (
            type(ix) is not int
            or type(iy) is not int
        ):
            raise ValueError(
                "Indices de celda invalidos."
            )

        identificador = f"C_{ix}_{iy}"

        if p.get("id_celda") != identificador:
            raise ValueError(
                f"ID inconsistente: {identificador}"
            )

        if (
            (ix, iy) in por_coord
            or identificador in por_id
        ):
            raise ValueError(
                f"Celda duplicada: {identificador}"
            )

        # ==================================
        # 6. RECUPERAR CONTEOS ANUALES
        # ==================================

        conteos = {}

        for year in ANIOS:

            n = entero_no_negativo(
                p.get(f"n_{year}"),
                f"{identificador}/n_{year}"
            )

            conteos[str(year)] = n

            total_anual[year] += n

        total_historico = sum(
            conteos.values()
        )

        if (
            total_historico == 0
            or total_historico !=
            p.get("conteo_2015_2025")
        ):
            raise ValueError(
                f"Conteo historico incorrecto: "
                f"{identificador}"
            )

        if (
            conteos[str(ANIO_FOCO)]
            != p.get("conteo_2025")
        ):
            raise ValueError(
                f"Conteo anual incorrecto: "
                f"{identificador}"
            )

        # ==================================
        # 7. POSICION DEL VERTICE
        # ==================================

        lon = float(
            p["centro_lon"]
        )

        lat = float(
            p["centro_lat"]
        )

        if not (
            math.isfinite(lon)
            and math.isfinite(lat)
            and -180 <= lon <= 180
            and -90 <= lat <= 90
        ):
            raise ValueError(
                f"Centro geografico invalido: "
                f"{identificador}"
            )

        nodo = {

            "id": identificador,

            "indice_x": ix,
            "indice_y": iy,

            "centro_lonlat": [
                lon, lat
            ],

            "centro_xy_m": [
                float(p["centro_x_m"]),
                float(p["centro_y_m"])
            ],

            "conteos": conteos,

            "conteo_2025":
                conteos[str(ANIO_FOCO)],

            "conteo_historico":
                total_historico,

            "alta_concentracion_2025":
                p.get(
                    "alta_concentracion_2025"
                ) is True
        }

        por_coord[(ix, iy)] = nodo

        por_id[identificador] = nodo

    if not por_id:
        raise ValueError(
            "No se encontraron celdas."
        )

    # ======================================
    # 8. AUDITAR CONTRA ETAPA 21.1
    # ======================================

    esperado = resumen.get(
        "eventos_por_anio", {}
    )

    for year in ANIOS:

        if (
            total_anual[year]
            != esperado.get(str(year))
        ):
            raise ValueError(
                f"Descuadre de eventos: {year}"
            )

    if (
        sum(total_anual.values())
        != resumen.get(
            "total_eventos_georreferenciados"
        )
    ):
        raise ValueError(
            "Total de siniestros diferente."
        )

    if (
        len(por_id)
        != resumen.get(
            "celdas_con_eventos_2015_2025"
        )
    ):
        raise ValueError(
            "Cantidad de celdas diferente."
        )

    activas = sum(
        n["conteo_2025"] > 0
        for n in por_id.values()
    )

    if (
        activas
        != resumen.get(
            "celdas_con_eventos_2025"
        )
    ):
        raise ValueError(
            "Celdas activas 2025 diferentes."
        )

    focos = [
        n
        for n in por_id.values()
        if n["alta_concentracion_2025"]
    ]

    if (
        len(focos)
        != resumen.get(
            "celdas_alta_concentracion_2025"
        )
    ):
        raise ValueError(
            "Cantidad de zonas destacadas "
            "inconsistente."
        )

    if (
        sum(n["conteo_2025"] for n in focos)
        != resumen.get(
            "eventos_2025_en_celdas_alta_concentracion"
        )
    ):
        raise ValueError(
            "Eventos en zonas destacadas "
            "inconsistentes."
        )

    return por_coord, total_anual


# ==========================================
# 9. COMPONENTES CONEXAS DEL GRAFO
# ==========================================

def componentes(nodos, aristas):

    vecinos = {
        n["id"]: set()
        for n in nodos
    }

    for arista in aristas:

        a = arista["source"]
        b = arista["target"]

        vecinos[a].add(b)
        vecinos[b].add(a)

    pendientes = set(vecinos)

    grupos = []

    while pendientes:

        origen = min(pendientes)

        cola = deque([origen])

        pendientes.remove(origen)

        miembros = []

        while cola:

            actual = cola.popleft()

            miembros.append(actual)

            siguientes = sorted(
                vecinos[actual] & pendientes
            )

            for siguiente in siguientes:

                pendientes.remove(
                    siguiente
                )

                cola.append(
                    siguiente
                )

        grupos.append(
            sorted(miembros)
        )

    grupos.sort(
        key=lambda g: (-len(g), g[0])
    )

    pertenencia = {

        identificador: i + 1

        for i, grupo in enumerate(grupos)

        for identificador in grupo
    }

    return grupos, pertenencia, vecinos


# ==========================================
# 10. CONSTRUIR UN GRAFO ESPACIAL
# ==========================================

def construir_grafo(
    por_coord,
    solo_2025
):

    nodos = [

        n.copy()

        for n in por_coord.values()

        if (
            not solo_2025
            or n["conteo_2025"] > 0
        )
    ]

    nodos.sort(
        key=lambda n: (
            n["indice_x"],
            n["indice_y"]
        )
    )

    indice = {

        (
            n["indice_x"],
            n["indice_y"]
        ): n

        for n in nodos
    }

    aristas = []

    # ======================================
    # 11. GENERAR ARISTAS DE VECINDAD
    # ======================================

    for nodo in nodos:

        ix = nodo["indice_x"]
        iy = nodo["indice_y"]

        for dx, dy in DIRECCIONES:

            vecino = indice.get(
                (ix + dx, iy + dy)
            )

            if vecino is None:
                continue

            distancia = (
                LADO_CELDA_M
                * math.hypot(dx, dy)
            )

            aristas.append({

                "source": nodo["id"],

                "target": vecino["id"],

                "tipo": (
                    "lado"
                    if dx == 0 or dy == 0
                    else "diagonal"
                ),

                "distancia_m":
                    round(distancia, 3),

                "peso": round(
                    LADO_CELDA_M / distancia,
                    8
                )
            })

    # ======================================
    # 12. CALCULAR CONECTIVIDAD
    # ======================================

    grupos, pertenencia, vecinos = (
        componentes(
            nodos,
            aristas
        )
    )

    suma_pesos = {

        n["id"]: 0.0

        for n in nodos
    }

    for arista in aristas:

        suma_pesos[
            arista["source"]
        ] += arista["peso"]

        suma_pesos[
            arista["target"]
        ] += arista["peso"]

    for nodo in nodos:

        identificador = nodo["id"]

        nodo["grado"] = len(
            vecinos[identificador]
        )

        nodo["grado_ponderado"] = round(
            suma_pesos[identificador],
            8
        )

        nodo["componente"] = (
            pertenencia[identificador]
        )

    # ======================================
    # 13. ESTADISTICAS DE RED
    # ======================================

    indice_id = {
        n["id"]: n
        for n in nodos
    }

    resumen = {

        "nodos": len(nodos),

        "aristas": len(aristas),

        "componentes": len(grupos),

        "tamano_componente_mayor": (
            len(grupos[0])
            if grupos else 0
        ),

        "nodos_aislados": sum(
            n["grado"] == 0
            for n in nodos
        ),

        "aristas_entre_focos": sum(

            indice_id[
                a["source"]
            ]["alta_concentracion_2025"]

            and

            indice_id[
                a["target"]
            ]["alta_concentracion_2025"]

            for a in aristas
        ),

        "aristas_por_lado": sum(
            a["tipo"] == "lado"
            for a in aristas
        ),

        "aristas_por_diagonal": sum(
            a["tipo"] == "diagonal"
            for a in aristas
        )
    }

    # ======================================
    # 14. CREAR ESTRUCTURA JSON
    # ======================================

    grafo = {

        "metadatos": {

            "tipo": (
                "celdas_activas_2025"
                if solo_2025
                else "celdas_historicas_2015_2025"
            ),

            "lado_celda_m":
                LADO_CELDA_M,

            "vecindad":
                "reina_8_vecinos",

            "peso":
                "1000_m / distancia_entre_centros_m",

            "advertencia": (
                "Las aristas representan "
                "vecindad geometrica, no calles, "
                "trayectos ni relaciones causales. "
                "El grafo puede estar desconectado."
            )
        },

        "resumen": resumen,

        "nodos": nodos,

        "aristas": aristas
    }

    return grafo


# ==========================================
# 15. EXPORTAR LAS ARISTAS COMO GEOJSON
# ==========================================

def geojson_aristas(grafo):

    by_id = {
        n["id"]: n
        for n in grafo["nodos"]
    }

    features = []

    for i, arista in enumerate(
        grafo["aristas"]
    ):

        a = by_id[
            arista["source"]
        ]

        b = by_id[
            arista["target"]
        ]

        features.append({

            "type": "Feature",

            "id": i,

            "properties": dict(arista),

            "geometry": {

                "type": "LineString",

                "coordinates": [

                    a["centro_lonlat"],

                    b["centro_lonlat"]
                ]
            }
        })

    return {

        "type": "FeatureCollection",

        "features": features
    }


# ==========================================
# 16. EJECUCION PRINCIPAL
# ==========================================

def main():

    zonas = leer(
        "21_zonas_siniestros.geojson"
    )

    resumen_zonas = leer(
        "21_resumen_zonas.json"
    )

    celdas, conteos_anuales = leer_celdas(
        zonas,
        resumen_zonas
    )

    # ======================================
    # 17. CONSTRUIR LAS DOS REDES
    # ======================================

    historico = construir_grafo(
        celdas,
        solo_2025=False
    )

    anio2025 = construir_grafo(
        celdas,
        solo_2025=True
    )

    ids_hist = {
        n["id"]
        for n in historico["nodos"]
    }

    ids_2025 = {
        n["id"]
        for n in anio2025["nodos"]
    }

    if not ids_2025 <= ids_hist:

        raise AssertionError(
            "El grafo 2025 contiene "
            "celdas desconocidas."
        )

    edges_hist = {

        tuple(sorted((
            e["source"],
            e["target"]
        )))

        for e in historico["aristas"]
    }

    for arista in anio2025["aristas"]:

        par = tuple(sorted((
            arista["source"],
            arista["target"]
        )))

        if par not in edges_hist:

            raise AssertionError(
                "El grafo 2025 no es "
                "subgrafo del historico."
            )

    total_2025 = sum(
        n["conteo_2025"]
        for n in anio2025["nodos"]
    )

    if total_2025 != conteos_anuales[ANIO_FOCO]:

        raise AssertionError(
            "El grafo no conserva "
            "todos los registros de 2025."
        )

    # ======================================
    # 18. GUARDAR REDES
    # ======================================

    guardar_json(

        DATOS / "21_grafo_siniestros.json",

        historico
    )

    guardar_json(

        DATOS / "21_grafo_siniestros_2025.json",

        anio2025
    )

    guardar_json(

        DATOS / "21_aristas_siniestros_2025.geojson",

        geojson_aristas(anio2025)
    )

    # ======================================
    # 19. REPORTE DE GRAFOS
    # ======================================

    salida_resumen = {

        "metodo": (
            "Vecindad reina de ocho posiciones "
            "entre celdas de 1 km, EPSG:6368"
        ),

        "grafo_historico":
            historico["resumen"],

        "grafo_2025":
            anio2025["resumen"],

        "siniestros_2025_conservados":
            total_2025,

        "zonas_destacadas_2025": sum(
            n["alta_concentracion_2025"]
            for n in anio2025["nodos"]
        ),

        "nota": (
            "Se conservan componentes "
            "desconectadas y nodos aislados. "
            "Para el analisis espectral debemos "
            "trabajar por componentes o evaluar "
            "el componente mayor."
        )
    }

    guardar_json(

        REPORTES / "21_resumen_grafo_siniestros.json",

        salida_resumen
    )

    # ======================================
    # 20. EXPORTAR METRICAS DE NODOS
    # ======================================

    columnas = [

        "id",
        "indice_x",
        "indice_y",

        "conteo_2025",
        "conteo_historico",

        "alta_concentracion_2025",

        "grado",
        "grado_ponderado",

        "componente"
    ]

    ruta_csv = (
        REPORTES
        / "21_metricas_grafo_siniestros.csv"
    )

    with ruta_csv.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas
        )

        escritor.writeheader()

        for nodo in anio2025["nodos"]:

            escritor.writerow({

                campo: nodo[campo]

                for campo in columnas
            })

    print(
        f"Generado: {ruta_csv.name} "
        f"({len(anio2025['nodos'])} filas)"
    )

    # ======================================
    # 21. RESUMEN EN TERMINAL
    # ======================================

    print(
        "\n=== ETAPA 21.2 | "
        "GRAFOS DE SINIESTROS ==="
    )

    for titulo, grafo in [

        ("Historico 2015-2025", historico),

        ("Subgrafo 2025", anio2025)
    ]:

        r = grafo["resumen"]

        print(f"\n{titulo}:")

        print(
            f"  Nodos: {r['nodos']} | "
            f"Aristas: {r['aristas']}"
        )

        print(
            f"  Componentes: {r['componentes']} | "
            f"Mayor: {r['tamano_componente_mayor']}"
        )

        print(
            f"  Nodos aislados: "
            f"{r['nodos_aislados']}"
        )

        print(
            "  Aristas lado/diagonal: "
            f"{r['aristas_por_lado']}/"
            f"{r['aristas_por_diagonal']}"
        )

        print(
            "  Aristas entre zonas destacadas: "
            f"{r['aristas_entre_focos']}"
        )

    print(
        f"\nEventos 2025 conservados: "
        f"{total_2025}"
    )

    print(
        "Nota: conectividad espacial, "
        "no relaciones causales."
    )


if __name__ == "__main__":
    main()
