
r"""HOTSPOT | Etapa 20.1: auditoría de integridad.

Ejecutar desde hotspot-mvp:
    ..\.venv\Scripts\python.exe .\20_auditoria_mvp.py

Entradas:
    hotspot-mvp/datos/*.json
    hotspot-mvp/19_visor_optimizado.html
    hotspot-mvp/19_papiroflexia_three.js

Salida:
    Data Procesada/20_reporte_auditoria.json
    Data Procesada/20_detalle_auditoria.csv

No modifica los archivos científicos originales.
"""

import csv
import json
import math

from pathlib import Path
from collections import Counter, deque

from shapely.geometry import shape


# ============================================
# 1. CONFIGURAR RUTAS
# ============================================

BASE = Path(__file__).resolve().parent

DATOS = BASE / "datos"

PROCESADA = BASE.parent / "Data Procesada"

PROCESADA.mkdir(
    parents=True,
    exist_ok=True
)

ARCHIVOS = [
    "municipios.json",
    "municipios.geojson",
    "municipios_ligero.geojson",
    "grafo.json",
    "19_escena_espectral.json",
    "siniestros.geojson",
    "seguridad.json",
    "modelos.json"
]

REVISIONES = []
RESUMEN = {}


# ============================================
# 2. FUNCIONES DE AUDITORIA
# ============================================

class ErrorAuditoria(Exception):
    pass


def registrar(area, estado, detalle):

    REVISIONES.append({
        "area": area,
        "estado": estado,
        "detalle": str(detalle)
    })

    print(
        f"[{estado}] {area}: {detalle}"
    )


def exigir(
    condicion,
    area,
    detalle_ok,
    detalle_error
):

    if condicion:

        registrar(
            area,
            "OK",
            detalle_ok
        )

    else:

        registrar(
            area,
            "ERROR",
            detalle_error
        )

        raise ErrorAuditoria(
            detalle_error
        )


def aviso(area, detalle):

    registrar(
        area,
        "AVISO",
        detalle
    )


def cargar(nombre):

    ruta = DATOS / nombre

    with ruta.open(
        encoding="utf-8-sig"
    ) as archivo:

        return json.load(archivo)


def identificadores(items, campo):

    return [
        str(item[campo]).strip()
        for item in items
    ]


# ============================================
# 3. VALIDAR NUMEROS
# ============================================

def valor_numerico(
    value,
    admite_null=False
):

    if value is None and admite_null:
        return None

    if (
        isinstance(value, bool)
        or value is None
    ):
        raise ValueError(
            f"No es numerico: {value!r}"
        )

    numero = float(value)

    if not math.isfinite(numero):
        raise ValueError(
            f"Numero no finito: {value!r}"
        )

    return numero


def casi_igual(a, b, tol=1e-5):

    if a is None or b is None:
        return a is None and b is None

    return math.isclose(
        valor_numerico(a),
        valor_numerico(b),
        abs_tol=tol,
        rel_tol=tol
    )


# ============================================
# 4. CONTAR VERTICES
# ============================================

def puntos_geometria(geom):

    if geom.geom_type == "Polygon":
        partes = [geom]
    else:
        partes = list(geom.geoms)

    total = 0

    for parte in partes:

        total += len(
            parte.exterior.coords
        )

        for interior in parte.interiors:
            total += len(
                interior.coords
            )

    return total


# ============================================
# 5. COMENZAR AUDITORIA
# ============================================

def auditar():

    print(
        "\n=== HOTSPOT | "
        "ETAPA 20: AUDITORIA ===\n"
    )

    # ----------------------------------------
    # A. COMPROBAR ARCHIVOS
    # ----------------------------------------

    faltantes = [
        nombre
        for nombre in ARCHIVOS
        if not (DATOS / nombre).is_file()
    ]

    exigir(
        not faltantes,
        "Archivos exportados",
        "Ocho archivos de datos encontrados",
        f"Faltan archivos: {faltantes}"
    )

    html = (
        BASE / "19_visor_optimizado.html"
    )

    js = (
        BASE / "19_papiroflexia_three.js"
    )

    exigir(
        html.is_file() and js.is_file(),
        "Frontend Etapa 19",
        "HTML y motor Three.js encontrados",
        "Faltan archivos del visor 19"
    )

    # ----------------------------------------
    # B. LEER LOS OCHO ARCHIVOS
    # ----------------------------------------

    municipal_json = cargar(
        "municipios.json"
    )

    geo_original = cargar(
        "municipios.geojson"
    )

    geo_ligero = cargar(
        "municipios_ligero.geojson"
    )

    grafo = cargar(
        "grafo.json"
    )

    escena = cargar(
        "19_escena_espectral.json"
    )

    siniestros = cargar(
        "siniestros.geojson"
    )

    seguridad = cargar(
        "seguridad.json"
    )

    modelos = cargar(
        "modelos.json"
    )

    # ----------------------------------------
    # C. VALIDAR LOS 125 MUNICIPIOS
    # ----------------------------------------

    municipios = municipal_json[
        "municipios"
    ]

    ids = identificadores(
        municipios,
        "cvegeo"
    )

    exigir(
        len(ids) == 125
        and len(set(ids)) == 125
        and all(
            len(c) == 5 and c.isdigit()
            for c in ids
        ),
        "Municipios",
        "125 claves cvegeo unicas",
        "Claves municipales invalidas"
    )

    por_id = dict(
        zip(ids, municipios)
    )

    # ----------------------------------------
    # D. COMPROBAR VALORES ATUS FALTANTES
    # ----------------------------------------

    faltantes_atus = sum(
        m.get("registros_atus_2025") is None
        for m in municipios
    )

    RESUMEN["municipios"] = len(ids)

    RESUMEN["atus_sin_dato"] = (
        faltantes_atus
    )

    RESUMEN["atus_con_dato"] = (
        125 - faltantes_atus
    )

    if faltantes_atus == 45:

        registrar(
            "ATUS",
            "OK",
            "45 municipios sin dato (null), "
            "80 con dato"
        )

    else:

        aviso(
            "ATUS",
            f"Se encontraron {faltantes_atus} "
            "valores null; el corte anterior "
            "tenia 45"
        )

    # ----------------------------------------
    # E. VALIDAR CONTEOS MUNICIPALES
    # ----------------------------------------

    for m in municipios:

        for campo in [
            "establecimientos_denue_mayo_2025",
            "siniestros_registrados_2025"
        ]:

            n = valor_numerico(
                m.get(campo)
            )

            if n < 0 or not n.is_integer():
                raise ErrorAuditoria(
                    f"Conteo invalido: "
                    f"{m['cvegeo']}/{campo}"
                )

        atus = valor_numerico(
            m.get("registros_atus_2025"),
            admite_null=True
        )

        if atus is not None:

            if (
                atus < 0
                or not atus.is_integer()
            ):

                raise ErrorAuditoria(
                    f"ATUS invalido: "
                    f"{m['cvegeo']}"
                )

    registrar(
        "Conteos municipales",
        "OK",
        "Valores numericos no negativos"
    )

    # ----------------------------------------
    # F. COMPARAR CARTOGRAFIA
    # ----------------------------------------

    originales = geo_original.get(
        "features", []
    )

    ligeras = geo_ligero.get(
        "features", []
    )

    originales_id = {
        str(f["properties"]["cvegeo"]): f
        for f in originales
    }

    ligeras_id = {
        str(f["properties"]["cvegeo"]): f
        for f in ligeras
    }

    exigir(
        len(originales) == 125
        and len(ligeras) == 125
        and len(originales_id) == 125
        and len(ligeras_id) == 125
        and set(originales_id) == set(ids)
        and set(ligeras_id) == set(ids),
        "Cartografia",
        "Original y simplificada contienen "
        "los mismos 125 municipios",
        "Las claves cartograficas no coinciden"
    )

    # ----------------------------------------
    # G. MEDIR LA SIMPLIFICACION
    # ----------------------------------------

    vertices_originales = 0

    vertices_ligeros = 0

    mayores_cambios = []

    for clave in ids:

        g0 = shape(
            originales_id[clave]["geometry"]
        )

        g1 = shape(
            ligeras_id[clave]["geometry"]
        )

        if (
            g0.is_empty
            or g1.is_empty
            or not g0.is_valid
            or not g1.is_valid
            or g0.area <= 0
            or g1.area <= 0
        ):

            raise ErrorAuditoria(
                f"Poligono invalido: {clave}"
            )

        vertices_originales += (
            puntos_geometria(g0)
        )

        vertices_ligeros += (
            puntos_geometria(g1)
        )

        cambio = abs(
            g1.area / g0.area - 1
        )

        if cambio > 0.05:
            mayores_cambios.append(
                (clave, cambio)
            )

    tam_original = (
        DATOS / "municipios.geojson"
    ).stat().st_size

    tam_ligero = (
        DATOS / "municipios_ligero.geojson"
    ).stat().st_size

    reduccion = 100 * (
        1 - tam_ligero / tam_original
    )

    RESUMEN[
        "vertices_geojson_original"
    ] = vertices_originales

    RESUMEN[
        "vertices_geojson_ligero"
    ] = vertices_ligeros

    RESUMEN[
        "reduccion_geojson_porcentaje"
    ] = round(reduccion, 2)

    registrar(
        "Simplificacion",
        "OK",
        f"Vertices: {vertices_originales:,} "
        f"-> {vertices_ligeros:,}; "
        f"reduccion: {reduccion:.2f}%"
    )

    if mayores_cambios:

        aviso(
            "Precision cartografica",
            f"{len(mayores_cambios)} municipios "
            "tienen cambio de area planar >5%; "
            f"ejemplos: {mayores_cambios[:3]}"
        )

    else:

        registrar(
            "Precision cartografica",
            "OK",
            "Sin cambios de area planar >5%"
        )

    # ----------------------------------------
    # H. VALIDAR GRAFO
    # ----------------------------------------

    nodos = grafo["nodos"]

    aristas = grafo["aristas"]

    claves_grafo = identificadores(
        nodos,
        "id"
    )

    exigir(
        len(nodos) == 125
        and len(set(claves_grafo)) == 125
        and set(claves_grafo) == set(ids)
        and len(aristas) == 304,
        "Grafo",
        "125 nodos y 304 aristas",
        "El grafo no coincide con municipios"
    )

    vecinos = {
        clave: set()
        for clave in ids
    }

    enlaces = set()

    for arista in aristas:

        a = str(arista["source"])

        b = str(arista["target"])

        if (
            a not in vecinos
            or b not in vecinos
            or a == b
        ):

            raise ErrorAuditoria(
                f"Arista invalida: {a}-{b}"
            )

        par = tuple(
            sorted((a, b))
        )

        if par in enlaces:

            raise ErrorAuditoria(
                f"Arista repetida: {a}-{b}"
            )

        enlaces.add(par)

        vecinos[a].add(b)

        vecinos[b].add(a)

    # Comprobar grado de cada municipio.

    for nodo in nodos:

        clave = str(nodo["id"])

        if (
            int(nodo["grado"])
            != len(vecinos[clave])
        ):

            raise ErrorAuditoria(
                f"Grado incorrecto: {clave}"
            )

    # ----------------------------------------
    # I. COMPROBAR CONECTIVIDAD
    # ----------------------------------------

    visitados = set()

    pendientes = deque([
        ids[0]
    ])

    while pendientes:

        actual = pendientes.popleft()

        if actual in visitados:
            continue

        visitados.add(actual)

        pendientes.extend(
            vecinos[actual] - visitados
        )

    exigir(
        len(visitados) == 125,
        "Conectividad",
        "Una componente conexa",
        "El grafo esta desconectado"
    )

    RESUMEN["aristas"] = len(aristas)

    # ----------------------------------------
    # J. VALIDAR ESCENA ESPECTRAL
    # ----------------------------------------

    escena_nodos = escena["nodos"]

    escena_aristas = escena["aristas"]

    ids_escena = identificadores(
        escena_nodos,
        "id"
    )

    exigir(
        len(ids_escena) == 125
        and ids_escena == claves_grafo
        and len(escena_aristas) == 304,
        "Escena 3D",
        "Orden de nodos y cantidad "
        "de aristas correctos",
        "Escena desalineada con el grafo"
    )

    # ----------------------------------------
    # K. VALIDAR CONEXIONES DE LA ESCENA
    # ----------------------------------------

    enlaces_escena = set()

    for par in escena_aristas:

        if (
            not isinstance(par, list)
            or len(par) != 2
        ):

            raise ErrorAuditoria(
                "Formato de arista 3D invalido"
            )

        i, j = par

        if (
            isinstance(i, bool)
            or isinstance(j, bool)
            or not isinstance(i, int)
            or not isinstance(j, int)
            or not (0 <= i < 125)
            or not (0 <= j < 125)
            or i == j
        ):

            raise ErrorAuditoria(
                f"Indices invalidos: {par}"
            )

        enlaces_escena.add(
            tuple(sorted((
                ids_escena[i],
                ids_escena[j]
            )))
        )

    exigir(
        enlaces_escena == enlaces,
        "Aristas 3D",
        "Las 304 conexiones son identicas "
        "al grafo original",
        "La escena cambio las conexiones"
    )

    # ----------------------------------------
    # L. COMPARAR INDICADORES DE LA ESCENA
    # ----------------------------------------

    mapa_campos = {
        "denue": "denue_por_km2",
        "atus": "registros_atus_2025",
        "siniestralimap":
            "siniestros_registrados_2025"
    }

    for nodo in escena_nodos:

        clave = str(nodo["id"])

        for nombre in [
            "geo",
            "espectral"
        ]:

            vector = nodo.get(nombre)

            if (
                not isinstance(vector, list)
                or len(vector) != 3
            ):

                raise ErrorAuditoria(
                    f"Coordenadas 3D invalidas: "
                    f"{clave}/{nombre}"
                )

            for valor in vector:
                valor_numerico(valor)

        for campo_escena, campo_municipal \
                in mapa_campos.items():

            valor_escena = nodo[
                "valores"
            ].get(campo_escena)

            valor_municipal = por_id[
                clave
            ].get(campo_municipal)

            if not casi_igual(
                valor_escena,
                valor_municipal
            ):

                raise ErrorAuditoria(
                    f"Indicador diferente: "
                    f"{clave}/{campo_escena}"
                )

    # ----------------------------------------
    # M. VERIFICAR QUE NO PERDIMOS LOS NULL
    # ----------------------------------------

    null_escena = sum(
        nodo["valores"]["atus"] is None
        for nodo in escena_nodos
    )

    exigir(
        null_escena == faltantes_atus,
        "Nulos en 3D",
        "ATUS conserva exactamente "
        "sus valores null",
        "La escena modifico los faltantes ATUS"
    )

    # ----------------------------------------
    # N. COMPROBAR SILUETA DE JALISCO
    # ----------------------------------------

    contornos = escena.get(
        "contornos_jalisco", []
    )

    contornos_validos = (
        bool(contornos)
        and all(
            len(anillo) >= 4
            for anillo in contornos
        )
        and all(
            len(punto) == 2
            and all(
                math.isfinite(float(x))
                for x in punto
            )
            for anillo in contornos
            for punto in anillo
        )
    )

    exigir(
        contornos_validos,
        "Silueta Jalisco",
        f"{len(contornos)} anillos exteriores "
        "listos para Three.js",
        "Silueta ausente o invalida"
    )

    # ----------------------------------------
    # O. VALIDAR SINIESTRALIMAP
    # ----------------------------------------

    features_s = siniestros.get(
        "features", []
    )

    exigir(
        siniestros.get("type")
            == "FeatureCollection"
        and bool(features_s),
        "Siniestralimap",
        f"{len(features_s):,} eventos "
        "georreferenciados",
        "GeoJSON de siniestros invalido"
    )

    por_anio = Counter()

    for indice, feature in enumerate(
        features_s
    ):

        geometria = (
            feature.get("geometry")
            or {}
        )

        if geometria.get("type") != "Point":

            raise ErrorAuditoria(
                f"Siniestro sin Point: {indice}"
            )

        coords = geometria.get(
            "coordinates", []
        )

        if (
            not isinstance(coords, list)
            or len(coords) < 2
        ):

            raise ErrorAuditoria(
                f"Siniestro sin coordenadas: {indice}"
            )

        lon = valor_numerico(coords[0])

        lat = valor_numerico(coords[1])

        if not (
            -180 <= lon <= 180
            and -90 <= lat <= 90
        ):

            raise ErrorAuditoria(
                f"Coordenadas fuera de rango: {indice}"
            )

        anio = feature.get(
            "properties", {}
        ).get("anio")

        if (
            anio is not None
            and str(anio).strip().isdigit()
        ):

            por_anio[int(anio)] += 1

    RESUMEN[
        "siniestros_georreferenciados"
    ] = len(features_s)

    RESUMEN[
        "siniestros_georreferenciados_2025"
    ] = por_anio.get(2025, 0)

    if len(features_s) != 16957:

        aviso(
            "Cantidad Siniestralimap",
            "El corte anterior tenia 16,957 "
            "puntos; revisar version"
        )

    if (
        not por_anio
        or min(por_anio) < 2015
        or max(por_anio) > 2025
    ):

        aviso(
            "Años de siniestros",
            f"Revisar años presentes: "
            f"{sorted(por_anio)}"
        )

    # Comparar puntos 2025 contra el total
    # asignado por municipio.

    asignados_2025 = sum(
        int(m["siniestros_registrados_2025"])
        for m in municipios
    )

    RESUMEN[
        "siniestralimap_asignados_2025"
    ] = asignados_2025

    if (
        por_anio.get(2025, 0)
        != asignados_2025
    ):

        aviso(
            "Conciliacion 2025",
            f"Puntos: {por_anio.get(2025, 0)}; "
            f"suma municipal: {asignados_2025}. "
            "Revisar criterios de asignacion."
        )

    else:

        registrar(
            "Conciliacion 2025",
            "OK",
            f"{asignados_2025} eventos "
            "georreferenciados y asignados"
        )

    # ----------------------------------------
    # P. VALIDAR SEGURIDAD REGIONAL
    # ----------------------------------------

    registros = seguridad.get(
        "registros", []
    )

    exigir(
        isinstance(registros, list)
        and bool(registros),
        "Seguridad",
        f"{len(registros):,} registros disponibles",
        "No hay series de Seguridad"
    )

    regiones = set()

    periodos = set()

    revisados = 0

    claves_seguridad = set()

    for registro in registros:

        campos = [
            "region",
            "periodo",
            "delito",
            "medida",
            "cantidad",
            "control_regional"
        ]

        if not all(
            campo in registro
            for campo in campos
        ):

            raise ErrorAuditoria(
                "Faltan campos de Seguridad"
            )

        # Esta fuente NO contiene ubicaciones
        # municipales de delitos individuales.

        if any(
            campo in registro
            for campo in [
                "lat",
                "lon",
                "latitud",
                "longitud",
                "municipio"
            ]
        ):

            raise ErrorAuditoria(
                "Seguridad contiene ubicaciones "
                "no esperadas"
            )

        regiones.add(
            registro["region"]
        )

        periodos.add(
            str(registro["periodo"])
        )

        cantidad = valor_numerico(
            registro["cantidad"]
        )

        if cantidad < 0:

            raise ErrorAuditoria(
                "Cantidad negativa en Seguridad"
            )

        clave = (
            registro["region"],
            registro["periodo"],
            registro["delito"],
            registro["medida"]
        )

        if clave in claves_seguridad:

            raise ErrorAuditoria(
                f"Registro duplicado: {clave}"
            )

        claves_seguridad.add(clave)

        if str(
            registro["control_regional"]
        ).upper() == "REVISAR":

            revisados += 1

    exigir(
        regiones == {
            "ESTADO",
            "AMG",
            "INTERIOR"
        },
        "Escala de Seguridad",
        f"3 regiones, {len(periodos)} periodos; "
        f"{revisados} registros REVISAR",
        f"Regiones inesperadas: {regiones}"
    )

    RESUMEN[
        "observaciones_seguridad"
    ] = len(registros)

    RESUMEN[
        "periodos_seguridad"
    ] = len(periodos)

    RESUMEN[
        "observaciones_seguridad_revisar"
    ] = revisados

    if len(registros) != 12195:

        aviso(
            "Cantidad Seguridad",
            "El corte anterior tenia 12,195 "
            "registros; revisar version"
        )

    if len(periodos) != 107:

        aviso(
            "Periodos Seguridad",
            "El corte anterior tenia 107 meses"
        )

    # ----------------------------------------
    # Q. VALIDAR RESULTADOS ESTADISTICOS
    # ----------------------------------------

    diagnosticos = modelos.get(
        "diagnosticos", []
    )

    coeficientes = modelos.get(
        "coeficientes", []
    )

    moran = modelos.get(
        "moran_atus", []
    )

    espectral = modelos.get(
        "analisis_espectral", []
    )

    energia = modelos.get(
        "energia_denue", []
    )

    exigir(
        len(diagnosticos) >= 6
        and bool(coeficientes)
        and len(moran) == 1
        and len(espectral) == 1
        and len(energia) == 1,
        "Modelos estadisticos",
        "Diagnosticos, coeficientes, Moran "
        "y energia presentes",
        "Modelos incompletos"
    )

    mo = moran[0]

    en = energia[0]

    es = espectral[0]

    # Los valores p siempre deben estar
    # entre cero y uno.

    for campo in [
        "p_agrupamiento_positivo",
        "p_bilateral_exploratorio"
    ]:

        p = valor_numerico(
            mo[campo]
        )

        if not 0 <= p <= 1:

            raise ErrorAuditoria(
                f"Valor p invalido: {campo}"
            )

    for campo in [
        "p_suavidad_unilateral",
        "p_contraste_unilateral"
    ]:

        p = valor_numerico(
            en[campo]
        )

        if not 0 <= p <= 1:

            raise ErrorAuditoria(
                f"Valor p invalido: {campo}"
            )

    # Comparar energia de Etapas 13 y 14.

    exigir(
        casi_igual(
            en["energia_observada"],
            es["energia_denue"],
            tol=1e-4
        )
        and int(es["n_municipios"]) == 125
        and int(es["n_aristas"]) == 304,
        "Energia espectral",
        "Etapas 13 y 14 coinciden",
        "La energia espectral no coincide"
    )

    RESUMEN["I_moran"] = (
        mo["I_moran"]
    )

    RESUMEN["energia_denue"] = (
        en["energia_observada"]
    )

    # ----------------------------------------
    # R. VALIDAR REFERENCIAS DEL FRONTEND
    # ----------------------------------------

    texto_html = html.read_text(
        encoding="utf-8"
    )

    exigir(
        "./datos/municipios_ligero.geojson"
            in texto_html
        and "./19_papiroflexia_three.js"
            in texto_html
        and 'type="module"' in texto_html
        and 'src="./17_papiroflexia.js"'
            not in texto_html,
        "Integracion HTML",
        "Cartografia ligera y Three.js activos",
        "El visor referencia archivos antiguos"
    )

    if (
        "./18_panel_cientifico.js"
        not in texto_html
    ):

        aviso(
            "Panel cientifico",
            "El visor 19 no referencia "
            "18_panel_cientifico.js"
        )

    elif not (
        BASE / "18_panel_cientifico.js"
    ).is_file():

        raise ErrorAuditoria(
            "El HTML referencia el panel 18, "
            "pero el archivo no existe"
        )

    else:

        registrar(
            "Panel cientifico",
            "OK",
            "Modulo encontrado y referenciado"
        )

    # ----------------------------------------
    # S. CONTRASTAR CON LA MATRIZ CIENTIFICA
    # ----------------------------------------

    fuente = (
        PROCESADA
        / "08_matriz_municipal_2025.csv"
    )

    if fuente.is_file():

        with fuente.open(
            encoding="utf-8-sig",
            newline=""
        ) as archivo:

            originales_csv = list(
                csv.DictReader(archivo)
            )

        fuente_ids = {
            str(f["cvegeo"]).strip(): f
            for f in originales_csv
        }

        exigir(
            len(originales_csv) == 125
            and set(fuente_ids) == set(ids),
            "Contraste con CSV cientifico",
            "Las 125 claves coinciden "
            "con la Etapa 08",
            "Claves diferentes frente al CSV"
        )

        for clave in ids:

            municipal = por_id[clave]

            fila_csv = fuente_ids[clave]

            for campo in [
                "registros_atus_2025",
                "establecimientos_denue_mayo_2025",
                "siniestros_registrados_2025"
            ]:

                dato = fila_csv.get(
                    campo
                )

                if dato in (
                    None,
                    "",
                    "NaN",
                    "nan"
                ):

                    dato = None

                if not casi_igual(
                    municipal.get(campo),
                    dato
                ):

                    raise ErrorAuditoria(
                        f"Valor diferente del CSV: "
                        f"{clave}/{campo}"
                    )

        registrar(
            "Datos vs CSV",
            "OK",
            "Los indicadores coinciden "
            "con la Etapa 08"
        )

    else:

        aviso(
            "Contraste con CSV cientifico",
            "No se encontro la matriz 08; "
            "se compararon los JSON"
        )

    # ----------------------------------------
    # T. LIMITACIONES METODOLOGICAS
    # ----------------------------------------

    aviso(
        "Alcance cientifico",
        "La auditoria no demuestra calidad "
        "predictiva ni ausencia de sesgos"
    )

    aviso(
        "Rendimiento visual",
        "FPS, apariencia y fluidez deben "
        "comprobarse en el navegador"
    )


# ============================================
# 6. GENERAR REPORTE
# ============================================

def escribir_reporte():

    errores = sum(
        r["estado"] == "ERROR"
        for r in REVISIONES
    )

    avisos = sum(
        r["estado"] == "AVISO"
        for r in REVISIONES
    )

    if errores:

        resultado = (
            "INTEGRIDAD NO VERIFICADA"
        )

    elif avisos:

        resultado = (
            "INTEGRIDAD VERIFICADA CON AVISOS"
        )

    else:

        resultado = (
            "INTEGRIDAD VERIFICADA"
        )

    RESUMEN["resultado"] = resultado

    RESUMEN["errores"] = errores

    RESUMEN["avisos"] = avisos

    reporte = {
        "resumen": RESUMEN,
        "revisiones": REVISIONES
    }

    # Reporte JSON.

    ruta_json = (
        PROCESADA
        / "20_reporte_auditoria.json"
    )

    with ruta_json.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            reporte,
            archivo,
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        )

    # Detalle CSV.

    ruta_csv = (
        PROCESADA
        / "20_detalle_auditoria.csv"
    )

    with ruta_csv.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "area",
                "estado",
                "detalle"
            ]
        )

        writer.writeheader()

        writer.writerows(
            REVISIONES
        )

    print(
        "\n=== RESUMEN DE LA AUDITORIA ==="
    )

    print("Estado:", resultado)

    print(
        "Comprobaciones:",
        len(REVISIONES)
    )

    print(
        "Errores:",
        errores,
        "| Avisos:",
        avisos
    )

    print(
        "Archivos:",
        ruta_json.name,
        "y",
        ruta_csv.name
    )

    print(
        "No se modificaron archivos "
        "cientificos ni frontend."
    )

    return errores


# ============================================
# 7. EJECUCION PRINCIPAL
# ============================================

def main():

    try:

        auditar()

    except (
        ErrorAuditoria,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        FileNotFoundError,
        OSError,
        json.JSONDecodeError
    ) as error:

        if (
            not REVISIONES
            or REVISIONES[-1]["estado"] != "ERROR"
        ):

            registrar(
                "Ejecucion",
                "ERROR",
                f"{type(error).__name__}: "
                f"{error}"
            )

    errores = escribir_reporte()

    if errores:

        raise SystemExit(1)


if __name__ == "__main__":
    main()
