
"""
HOTSPOT - ETAPA 19
Preparar la escena territorial-espectral.

ENTRADAS:
    datos/grafo.json
    datos/municipios.json
    datos/municipios.geojson

SALIDAS:
    datos/19_escena_espectral.json
    datos/municipios_ligero.geojson
    19_visor_optimizado.html

Los datos cientificos originales
no se modifican.
"""

from pathlib import Path
import json
import math

from shapely.geometry import (
    shape,
    mapping,
    Polygon
)

from shapely.ops import unary_union


# ============================================
# 1. CONFIGURACION
# ============================================

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"

TOL_MUNICIPIOS = 0.0012
TOL_CONTORNO = 0.0040

THREE_VERSION = "0.180.0"


# ============================================
# 2. LEER JSON
# ============================================

def cargar(nombre):

    ruta = DATOS / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe: {ruta}. "
            "Ejecuta primero la Etapa 15."
        )

    with ruta.open(
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


# ============================================
# 3. GUARDAR JSON
# ============================================

def guardar(nombre, contenido):

    ruta = DATOS / nombre

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False
        )

    print(
        f"Generado: {ruta.name} "
        f"({ruta.stat().st_size:,} bytes)"
    )


# ============================================
# 4. VALIDAR VALORES
# ============================================

def numero(valor, contexto):

    if isinstance(valor, bool) or valor is None:
        raise ValueError(
            f"Valor faltante: {contexto}"
        )

    n = float(valor)

    if not math.isfinite(n):
        raise ValueError(
            f"Valor no finito: {contexto}"
        )

    return n


def indicador(valor):

    # Los valores faltantes siguen siendo null.

    if valor is None or valor == "":
        return None

    n = numero(valor, "indicador")

    if n < 0:
        raise ValueError(
            "Indicador negativo no permitido."
        )

    return n


# ============================================
# 5. EXTRAER CONTORNOS
# ============================================

def anillos_visuales(geom):

    if isinstance(geom, Polygon):
        partes = [geom]
    else:
        partes = list(geom.geoms)

    return [
        list(parte.exterior.coords)
        for parte in partes
        if parte.area > 0
    ]


# ============================================
# 6. PROCESAMIENTO PRINCIPAL
# ============================================

def main():

    grafo = cargar("grafo.json")

    municipal = cargar("municipios.json")

    cartografia = cargar("municipios.geojson")

    nodos = grafo.get("nodos", [])
    aristas = grafo.get("aristas", [])

    municipios = municipal.get(
        "municipios", []
    )

    features = cartografia.get(
        "features", []
    )

    # Validar los tamaños que calculamos
    # en las etapas anteriores.

    if (
        len(nodos),
        len(aristas),
        len(municipios),
        len(features)
    ) != (125, 304, 125, 125):

        raise ValueError(
            "Se esperaban 125 nodos, "
            "304 aristas, 125 municipios "
            "y 125 poligonos."
        )

    # ========================================
    # 7. VALIDAR CLAVES MUNICIPALES
    # ========================================

    ids = [
        str(n["id"])
        for n in nodos
    ]

    if len(set(ids)) != 125:
        raise ValueError(
            "Existen claves repetidas."
        )

    por_id = {
        str(m["cvegeo"]): m
        for m in municipios
    }

    poligonos = {
        str(f["properties"]["cvegeo"]): f
        for f in features
    }

    if (
        len(por_id) != 125
        or len(poligonos) != 125
        or set(ids) != set(por_id)
        or set(ids) != set(poligonos)
    ):
        raise ValueError(
            "Las claves municipales "
            "no coinciden."
        )

    # ========================================
    # 8. SIMPLIFICAR LA CARTOGRAFIA
    # ========================================

    formas = []
    features_ligeras = []

    for clave in ids:

        feature = poligonos[clave]

        geom = shape(
            feature["geometry"]
        )

        if (
            not geom.is_valid
            or geom.is_empty
            or geom.geom_type not in (
                "Polygon",
                "MultiPolygon"
            )
        ):
            raise ValueError(
                f"Geometria invalida: {clave}"
            )

        formas.append(geom)

        simplificada = geom.simplify(
            TOL_MUNICIPIOS,
            preserve_topology=True
        )

        features_ligeras.append({
            "type": "Feature",
            "id": clave,
            "properties": feature["properties"],
            "geometry": mapping(simplificada)
        })

    # ========================================
    # 9. CONSTRUIR SILUETA DE JALISCO
    # ========================================

    # Unimos los municipios originales
    # antes de simplificar el estado.

    estado = unary_union(formas)

    if estado.is_empty or not estado.is_valid:
        raise ValueError(
            "No se pudo construir "
            "una silueta valida."
        )

    estado = estado.simplify(
        TOL_CONTORNO,
        preserve_topology=True
    )

    # ========================================
    # 10. NORMALIZAR GEOGRAFIA
    # ========================================

    minlon, minlat, maxlon, maxlat = (
        estado.bounds
    )

    lon_centro = (
        minlon + maxlon
    ) / 2

    lat_centro = (
        minlat + maxlat
    ) / 2

    coslat = math.cos(
        math.radians(lat_centro)
    )

    escala = 4.0 / max(
        (maxlon - minlon) * coslat,
        maxlat - minlat
    )

    def geoplano(lon, lat):

        x = (
            (lon - lon_centro)
            * coslat * escala
        )

        z = (
            (lat - lat_centro)
            * escala
        )

        return [
            round(x, 6),
            round(z, 6)
        ]

    # ========================================
    # 11. CONTORNO FIJO DEL ESTADO
    # ========================================

    contorno = [
        [
            geoplano(x, y)
            for x, y in anillo
        ]
        for anillo in anillos_visuales(estado)
    ]

    # ========================================
    # 12. RECUPERAR AUTOVECTORES
    # ========================================

    espectros = []

    for nodo in nodos:

        valores = nodo.get(
            "espectral_xyz"
        )

        if (
            not isinstance(valores, list)
            or len(valores) != 3
        ):
            raise ValueError(
                f"Embedding invalido: {nodo['id']}"
            )

        espectros.append([
            numero(
                valor,
                f"espectral {nodo['id']}"
            )
            for valor in valores
        ])

    # ========================================
    # 13. NORMALIZACION ESPECTRAL
    # ========================================

    promedios = [
        sum(
            vector[j]
            for vector in espectros
        ) / 125
        for j in range(3)
    ]

    maxabs = max(
        abs(
            vector[j] - promedios[j]
        )
        for vector in espectros
        for j in range(3)
    )

    if maxabs < 1e-12:
        raise ValueError(
            "El embedding no presenta variacion."
        )

    factor = 1.8 / maxabs

    # ========================================
    # 14. PREPARAR LOS 125 NODOS
    # ========================================

    nodos_salida = []

    for nodo, uv in zip(nodos, espectros):

        clave = str(nodo["id"])

        punto = nodo.get(
            "geografico_lonlat"
        )

        if (
            not isinstance(punto, list)
            or len(punto) != 2
        ):
            raise ValueError(
                f"Coordenadas invalidas: {clave}"
            )

        lon = numero(
            punto[0],
            clave
        )

        lat = numero(
            punto[1],
            clave
        )

        if not (
            -106.5 <= lon <= -100.5
            and 18 <= lat <= 23.5
        ):
            raise ValueError(
                f"Punto fuera del area "
                f"esperada de Jalisco: {clave}"
            )

        x, z = geoplano(lon, lat)

        # Coordenadas espectrales.
        # X = u2
        # Z = u3
        # Y = u4 + desplazamiento visual

        spec = [
            round(
                (uv[0] - promedios[0])
                * factor,
                6
            ),
            round(
                1.1
                + (uv[2] - promedios[2])
                * factor * 0.6,
                6
            ),
            round(
                (uv[1] - promedios[1])
                * factor,
                6
            )
        ]

        info = por_id[clave]

        nodos_salida.append({
            "id": clave,
            "nombre": str(nodo["nombre"]),

            "geo": [x, 0.06, z],

            "espectral": spec,

            "valores": {
                "denue": indicador(
                    info.get("denue_por_km2")
                ),
                "atus": indicador(
                    info.get(
                        "registros_atus_2025"
                    )
                ),
                "siniestralimap": indicador(
                    info.get(
                        "siniestros_registrados_2025"
                    )
                )
            }
        })

    # ========================================
    # 15. TRANSFORMAR ARISTAS A INDICES
    # ========================================

    posiciones = {
        clave: i
        for i, clave in enumerate(ids)
    }

    aristas_indices = []
    vistas = set()

    for arista in aristas:

        a = str(arista["source"])
        b = str(arista["target"])

        if (
            a not in posiciones
            or b not in posiciones
            or a == b
        ):
            raise ValueError(
                f"Arista invalida: {a} - {b}"
            )

        par = tuple(
            sorted((a, b))
        )

        if par in vistas:
            raise ValueError(
                f"Arista duplicada: {par}"
            )

        vistas.add(par)

        aristas_indices.append([
            posiciones[a],
            posiciones[b]
        ])

    # ========================================
    # 16. EXPORTAR ESCENA 3D
    # ========================================

    guardar(
        "19_escena_espectral.json",
        {
            "meta": {
                "nodos": 125,
                "aristas": 304,
                "metodo": (
                    "Interpolacion visual "
                    "geografia / autovectores "
                    "u2, u3, u4"
                ),
                "advertencia": (
                    "La altura y los colores "
                    "no son estimaciones de riesgo. "
                    "ATUS faltante sigue siendo null."
                )
            },
            "nodos": nodos_salida,
            "aristas": aristas_indices,
            "contornos_jalisco": contorno
        }
    )

    # ========================================
    # 17. EXPORTAR MUNICIPIOS LIGEROS
    # ========================================

    guardar(
        "municipios_ligero.geojson",
        {
            "type": "FeatureCollection",
            "features": features_ligeras
        }
    )

    # ========================================
    # 18. GENERAR HTML OPTIMIZADO
    # ========================================

    original = (
        BASE / "17_visor_integrado.html"
    )

    if not original.is_file():

        print(
            "AVISO: Falta "
            "17_visor_integrado.html."
        )

        return

    html = original.read_text(
        encoding="utf-8"
    )

    if (
        "./17_papiroflexia.js" not in html
        or "./datos/municipios.geojson" not in html
    ):
        raise ValueError(
            "El visor 17 no contiene "
            "las referencias esperadas."
        )

    # Cargar la cartografia optimizada.

    html = html.replace(
        "./datos/municipios.geojson",
        "./datos/municipios_ligero.geojson"
    )

    # Eliminar el renderizador Plotly.
    # Sustituirlo por Three.js.

    html = html.replace(
        '<script src="./17_papiroflexia.js"></script>',
        '<script type="module" '
        'src="./19_papiroflexia_three.js"></script>'
    )

    if (
        '<script type="module" '
        'src="./19_papiroflexia_three.js"></script>'
        not in html
    ):
        raise ValueError(
            "No se pudo sustituir Plotly."
        )

    # Importar Three.js y OrbitControls.

    importmap = f"""
    <script type="importmap">
    {{
      "imports": {{
        "three":
          "https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js",
        "three/addons/":
          "https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/examples/jsm/"
      }}
    }}
    </script>
    """

    html = html.replace(
        "</head>",
        importmap + "\n</head>",
        1
    )

    nueva = (
        BASE / "19_visor_optimizado.html"
    )

    nueva.write_text(
        html,
        encoding="utf-8"
    )

    print(
        f"Generado: {nueva.name}"
    )

    print(
        "\n=== ETAPA 19: ESCENA PREPARADA ==="
    )

    print(
        "Municipios:",
        len(nodos_salida)
    )

    print(
        "Aristas:",
        len(aristas_indices)
    )

    print(
        "No se modificaron los modelos "
        "ni los autovectores originales."
    )


if __name__ == "__main__":
    main()
