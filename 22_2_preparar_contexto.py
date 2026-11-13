
"""HOTSPOT · Etapa 22.2: cartografia de referencia y estabilidad urbana.

Ejecutar desde hotspot-mvp:
    ..\\.venv\\Scripts\\python.exe .\\22_2_preparar_contexto.py

Lee (sin modificarlos):
  datos/21_grafo_siniestros_2025.json
  datos/21_embedding_siniestros_2025.json
  datos/21_estabilidad_zonas_2025.geojson
  datos/municipios_ligero.geojson
  21_red_espectral_three.js, 22_visor_urbano.html, 22_app.html
  22_2_contexto_urbano.js, 22_2_estabilidad.js

Genera:
  datos/22_2_contexto_urbano.json
  22_2_red_espectral_three.js
  22_2_visor_urbano.html
  22_2_app.html

Las teselas de OpenStreetMap se solicitan SOLO al abrir el visor 3D,
no durante este script. El fondo no modifica ninguna coordenada cientifica.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from pyproj import Transformer

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
CLAVE_GUADALAJARA = "14039"
MAX_TESELAS = 32
ZOOM_INICIAL = 12
MARGEN_METROS = 1200


def leer(ruta: Path):
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe {ruta}")
    return json.loads(ruta.read_text(encoding="utf-8-sig"))


def ruta(nombre: str) -> Path:
    p = BASE / nombre
    if not p.is_file():
        raise FileNotFoundError(f"Falta {p}")
    return p


def lon_a_tile(lon, zoom):
    return int(math.floor((lon + 180.0) / 360.0 * (2 ** zoom)))


def lat_a_tile(lat, zoom):
    rad = math.radians(max(-85.0, min(85.0, lat)))
    return int(math.floor((1.0 - math.asinh(math.tan(rad)) / math.pi) / 2.0 * 2 ** zoom))


def tile_a_lon(x, zoom):
    return x / (2 ** zoom) * 360.0 - 180.0


def tile_a_lat(y, zoom):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / (2 ** zoom)))))


def exterior_anillos(geometry):
    tipo = geometry.get("type")
    coords = geometry.get("coordinates")
    if tipo == "Polygon":
        return [coords[0]]
    if tipo == "MultiPolygon":
        return [parte[0] for parte in coords]
    raise ValueError("Se esperaba Polygon o MultiPolygon")


def main():
    ruta("22_2_contexto_urbano.js")
    ruta("22_2_estabilidad.js")

    graph = leer(DATOS / "21_grafo_siniestros_2025.json")
    emb = leer(DATOS / "21_embedding_siniestros_2025.json")
    stab = leer(DATOS / "21_estabilidad_zonas_2025.geojson")
    muni = leer(DATOS / "municipios_ligero.geojson")

    if (len(graph["nodos"]), len(emb["nodos"]), len(emb["aristas"])) != (447, 447, 1034):
        raise ValueError("Grafo urbano distinto del corte validado (447/1034)")

    if len(stab.get("features", [])) != 764:
        raise ValueError("Faltan celdas de estabilidad de la Etapa 21.5")

    metric = {n["id"]: n for n in graph["nodos"]}

    coords = [n["centro_xy_m"] for n in graph["nodos"]]
    centro_x = sum(p[0] for p in coords) / len(coords)
    centro_y = sum(p[1] for p in coords) / len(coords)

    escala = 4.0 / max(
        max(p[0] for p in coords) - min(p[0] for p in coords),
        max(p[1] for p in coords) - min(p[1] for p in coords),
        1
    )

    def escena_xy_m(x, y):
        return [
            round((x - centro_x) * escala, 8),
            round((y - centro_y) * escala, 8)
        ]

    # Comprobar correspondencia con el embedding original.

    for nodo in emb["nodos"]:
        m = metric.get(nodo["id"])

        if m is None:
            raise ValueError(f"ID sin correspondencia: {nodo['id']}")

        xy = escena_xy_m(*m["centro_xy_m"])

        if (
            abs(xy[0] - nodo["geo_xyz"][0]) > 0.00001
            or abs(xy[1] - nodo["geo_xyz"][2]) > 0.00001
        ):
            raise ValueError(
                f"La proyeccion no coincide con el embedding: {nodo['id']}"
            )

    # Encontrar la extension de la componente mayor.

    mayor = [
        metric[n["id"]]
        for n in emb["nodos"]
        if n["en_componente_mayor"]
    ]

    if len(mayor) != 347:
        raise ValueError("La componente mayor debe contener 347 celdas")

    xmin = min(n["centro_xy_m"][0] for n in mayor) - MARGEN_METROS
    xmax = max(n["centro_xy_m"][0] for n in mayor) + MARGEN_METROS
    ymin = min(n["centro_xy_m"][1] for n in mayor) - MARGEN_METROS
    ymax = max(n["centro_xy_m"][1] for n in mayor) + MARGEN_METROS

    wgs84_to_m = Transformer.from_crs(
        "EPSG:4326", "EPSG:6368", always_xy=True
    )

    m_to_wgs84 = Transformer.from_crs(
        "EPSG:6368", "EPSG:4326", always_xy=True
    )

    west, south = m_to_wgs84.transform(xmin, ymin)
    east, north = m_to_wgs84.transform(xmax, ymax)

    # Buscar una resolucion que no exceda las 32 teselas.

    for zoom in range(ZOOM_INICIAL, 8, -1):
        tx0, tx1 = lon_a_tile(west, zoom), lon_a_tile(east, zoom)
        ty0, ty1 = lat_a_tile(north, zoom), lat_a_tile(south, zoom)

        cantidad = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)

        if cantidad <= MAX_TESELAS:
            break
    else:
        raise ValueError("Demasiadas teselas de fondo; revisar extension")

    # Preparar geometria de las teselas.

    teselas = []

    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):

            lon_o = tile_a_lon(tx, zoom)
            lon_e = tile_a_lon(tx + 1, zoom)
            lat_n = tile_a_lat(ty, zoom)
            lat_s = tile_a_lat(ty + 1, zoom)

            esquinas = [
                (lon_o, lat_s),
                (lon_e, lat_s),
                (lon_e, lat_n),
                (lon_o, lat_n)
            ]

            plano = [
                escena_xy_m(*wgs84_to_m.transform(lon, lat))
                for lon, lat in esquinas
            ]

            teselas.append({
                "z": zoom,
                "x": tx,
                "y": ty,
                "vertices": plano
            })

    # Preparar limite del municipio Guadalajara.

    guadalajara = [
        f for f in muni.get("features", [])
        if str(f.get("properties", {}).get("cvegeo")) == CLAVE_GUADALAJARA
    ]

    if len(guadalajara) != 1:
        raise ValueError(
            "No se encontro exactamente una geometria de Guadalajara "
            "(cvegeo 14039)"
        )

    contorno = []

    for anillo in exterior_anillos(guadalajara[0]["geometry"]):
        contorno.append([
            escena_xy_m(*wgs84_to_m.transform(float(lon), float(lat)))
            for lon, lat in anillo
        ])

    # Exportar datos cartograficos.

    contexto = {
        "metadatos": {
            "descripcion": "Referencia visual 3D: mapa y limite municipal de Guadalajara",
            "crs_origen": "EPSG:6368",
            "crs_cartografia": "EPSG:4326",
            "alineacion": "Mismo centro y escala visual que 21_embedding_siniestros_2025.json",
            "teselas_maximas": MAX_TESELAS,
            "zoom": zoom,
            "municipio_contorno": "Guadalajara",
            "cvegeo": CLAVE_GUADALAJARA,
            "nota": "El mapa de fondo no forma parte del modelo espectral ni mide riesgo vial."
        },
        "teselas": teselas,
        "contornos_guadalajara": contorno
    }

    destino = DATOS / "22_2_contexto_urbano.json"

    destino.write_text(
        json.dumps(
            contexto,
            ensure_ascii=False,
            separators=(",", ":")
        ),
        encoding="utf-8"
    )

    # ======================================
    # GENERAR COPIAS INTEGRADAS
    # ======================================

    def sustituir_uno(texto, patron, reemplazo, etiqueta):
        nuevo, cantidad = re.subn(
            patron,
            reemplazo,
            texto,
            count=1,
            flags=re.S | re.I
        )

        if cantidad != 1:
            raise ValueError(
                f"No se encontro el marcador de {etiqueta}; "
                "revisa la version del visor"
            )

        return nuevo

    # Actualizar motor de papiroflexia.

    base_js = ruta("21_red_espectral_three.js").read_text(
        encoding="utf-8-sig"
    )

    base_js = sustituir_uno(
        base_js,
        r'''(import\s*\{\s*OrbitControls\s*\}\s*from\s*['"]three/addons/controls/OrbitControls\.js['"]\s*;)''',
        lambda m: (
            m.group(1)
            + "\nimport { cargarContextoUrbano } from './22_2_contexto_urbano.js';"
        ),
        "importacion OrbitControls"
    )

    base_js = sustituir_uno(
        base_js,
        r'''(\bscene\s*=\s*new\s+THREE\.Scene\s*\(\s*\)\s*;)''',
        lambda m: (
            m.group(1)
            + "\n  void cargarContextoUrbano({ THREE, scene, redibujar: requestDraw })"
            ".catch(err => console.warn('Fondo urbano:', err));"
        ),
        "creacion de escena Three.js"
    )

    (BASE / "22_2_red_espectral_three.js").write_text(
        base_js,
        encoding="utf-8"
    )

    # Actualizar visor urbano.

    html = ruta("22_visor_urbano.html").read_text(
        encoding="utf-8-sig"
    )

    html = sustituir_uno(
        html,
        r'''fetchJSON\s*\(\s*(['"])21_zonas_siniestros\.geojson\1\s*\)''',
        'fetchJSON("21_estabilidad_zonas_2025.geojson")',
        "fuente de zonas"
    )

    html = sustituir_uno(
        html,
        r'''<script\b(?=[^>]*\btype\s*=\s*['"]module['"])(?=[^>]*\bsrc\s*=\s*['"]\./21_red_espectral_three\.js['"])[^>]*>\s*</script>''',
        '<script type="module" src="./22_2_red_espectral_three.js"></script>',
        "motor Three.js 21.4"
    )

    html = sustituir_uno(
        html,
        r'''\bready\s*=\s*true\s*;\s*refresh\s*\(\s*\)\s*;''',
        lambda m: (
            m.group(0)
            + " window.dispatchEvent(new CustomEvent("
            "'hotspot:urbano-ready', {detail: {map, zonas}}));"
        ),
        "mapa urbano listo"
    )

    # Controles del mapa 3D.

    controles_mapa = '''
    <div class="bar"
         style="margin-top:6px;gap:14px;font-size:12px;align-items:center">

      <label>
        <input id="22MostrarMapa" type="checkbox" checked>
        Mapa real de calles
      </label>

      <label>
        <input id="22MostrarLimite" type="checkbox" checked>
        Límite de Guadalajara
      </label>

      <span id="22EstadoMapa" style="color:#9db6da">
        Capa cartográfica opcional
      </span>

      <a href="https://www.openstreetmap.org/copyright"
         target="_blank"
         rel="noopener noreferrer"
         style="color:#9cbbe4;font-size:11px">
        © OpenStreetMap contributors
      </a>

    </div>
    '''

    html = sustituir_uno(
        html,
        r'''<div\b(?=[^>]*\bid\s*=\s*['"]threeHost['"])[^>]*>\s*</div>''',
        lambda m: controles_mapa + m.group(0),
        "contenedor de Three.js"
    )

    # Controles de estabilidad.

    controles_estabilidad = '''
    <div class="card">

      <label>
        <input type="checkbox"
               id="22MostrarEstabilidad"
               checked>
        Resaltar estabilidad descriptiva
      </label>

      <label for="22Umbral">
        Frecuencia media mínima en 12 escenarios
      </label>

      <select id="22Umbral"
              style="background:#24344e;color:white;border:1px solid #56678d;padding:8px;border-radius:8px">

        <option value="0.50">50%</option>
        <option value="0.75" selected>75%</option>
        <option value="1.00">100%</option>

      </select>

      <p class="hint" id="22ResumenEstabilidad">
        Cargando sensibilidad de cuadrículas...
      </p>

    </div>
    '''

    html = sustituir_uno(
        html,
        r'''<button\b(?=[^>]*\bid\s*=\s*['"]open3d['"])[^>]*>''',
        lambda m: controles_estabilidad + m.group(0),
        "boton de papiroflexia urbana"
    )

    html = sustituir_uno(
        html,
        r'''<script\b(?=[^>]*\bsrc\s*=\s*['"]\./22_puente\.js['"])[^>]*>\s*</script>''',
        lambda m: (
            '<script src="./22_2_estabilidad.js"></script>\n'
            + m.group(0)
        ),
        "puente 22.1"
    )

    (BASE / "22_2_visor_urbano.html").write_text(
        html,
        encoding="utf-8"
    )

    # Actualizar aplicacion principal.

    app = ruta("22_app.html").read_text(
        encoding="utf-8-sig"
    )

    if "22_visor_urbano.html" not in app:
        raise ValueError(
            "No se encontro la ruta de la vista urbana en la app 22"
        )

    app = app.replace(
        "22_visor_urbano.html",
        "22_2_visor_urbano.html"
    )

    (BASE / "22_2_app.html").write_text(
        app,
        encoding="utf-8"
    )

    # Resumen.

    print("\n=== ETAPA 22.2 PREPARADA ===")
    print(f"Contexto: {destino.name} ({destino.stat().st_size:,} bytes)")
    print(f"Teselas para vista 3D: {len(teselas)} (z={zoom}; solo al abrir la vista)")
    print(f"Contornos de Guadalajara: {len(contorno)}")
    print(
        "Generados: 22_2_red_espectral_three.js, "
        "22_2_visor_urbano.html, 22_2_app.html"
    )
    print("Abre: http://localhost:8000/22_2_app.html")
    print("No se modificaron visores ni datos originales.")


if __name__ == "__main__":
    main()
