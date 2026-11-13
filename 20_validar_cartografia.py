
r"""HOTSPOT | Etapa 20.3: validación geométrica.

Ejecutar:
    ..\.venv\Scripts\python.exe .\20_validar_cartografia.py

Entradas:
    datos/municipios.geojson
    datos/municipios_ligero.geojson
    datos/grafo.json

Salidas:
    Data Procesada/20_calidad_cartografia.json
    Data Procesada/20_detalle_geometrico.csv

No modifica los datos originales.
"""

import csv
import json

from pathlib import Path
from statistics import median

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union


# ==========================================
# 1. CONFIGURAR RUTAS
# ==========================================

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"

SALIDA = BASE.parent / "Data Procesada"

SALIDA.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================
# 2. LEER JSON
# ==========================================

def cargar(nombre):

    ruta = DATOS / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe {ruta}"
        )

    with ruta.open(
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


# ==========================================
# 3. EXTRAER POLIGONOS
# ==========================================

def obtener_poligonos(geojson, origen):

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            f"{origen}: GeoJSON invalido."
        )

    resultado = {}

    for feature in geojson.get("features", []):

        clave = str(
            feature.get("properties", {})
                   .get("cvegeo", "")
        ).strip()

        if (
            len(clave) != 5
            or not clave.isdigit()
            or clave in resultado
        ):
            raise ValueError(
                f"Clave invalida: {clave}"
            )

        geom = shape(
            feature["geometry"]
        )

        if (
            geom.geom_type not in (
                "Polygon",
                "MultiPolygon"
            )
            or geom.is_empty
            or not geom.is_valid
            or geom.area <= 0
        ):
            raise ValueError(
                f"Poligono invalido: {clave}"
            )

        resultado[clave] = geom

    if len(resultado) != 125:
        raise ValueError(
            f"{origen}: se esperaban "
            "125 municipios."
        )

    return resultado


# ==========================================
# 4. PROCESAR GEOMETRIA
# ==========================================

def main():

    original_json = cargar(
        "municipios.geojson"
    )

    ligero_json = cargar(
        "municipios_ligero.geojson"
    )

    grafo = cargar("grafo.json")

    original = obtener_poligonos(
        original_json,
        "original"
    )

    ligero = obtener_poligonos(
        ligero_json,
        "ligero"
    )

    if set(original) != set(ligero):
        raise ValueError(
            "Las claves municipales "
            "no coinciden."
        )

    if (
        len(grafo["nodos"]) != 125
        or len(grafo["aristas"]) != 304
    ):
        raise ValueError(
            "Grafo inesperado."
        )

    # ======================================
    # 5. PROYECTAR A METROS
    # ======================================

    transformar = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6368",
        always_xy=True
    ).transform

    original = {
        clave: transform(transformar, geom)
        for clave, geom in original.items()
    }

    ligero = {
        clave: transform(transformar, geom)
        for clave, geom in ligero.items()
    }

    # ======================================
    # 6. COMPARAR CADA MUNICIPIO
    # ======================================

    filas = []

    for clave in sorted(original):

        a = original[clave]
        b = ligero[clave]

        cambio_area = 100 * (
            b.area - a.area
        ) / a.area

        diferencia = 100 * (
            a.symmetric_difference(b).area
            / a.area
        )

        desplazamiento = (
            a.boundary.hausdorff_distance(
                b.boundary
            )
        )

        filas.append({
            "cvegeo": clave,

            "area_original_km2":
                round(a.area / 1_000_000, 5),

            "area_ligera_km2":
                round(b.area / 1_000_000, 5),

            "cambio_area_pct":
                round(cambio_area, 5),

            "diferencia_simetrica_pct":
                round(diferencia, 5),

            "desplazamiento_max_borde_m":
                round(desplazamiento, 5)
        })

    # ======================================
    # 7. COMPARAR SUPERFICIE TERRITORIAL
    # ======================================

    union_original = unary_union(
        list(original.values())
    )

    union_ligera = unary_union(
        list(ligero.values())
    )

    perdida = (
        union_original
        .difference(union_ligera)
        .area / 1_000_000
    )

    adicion = (
        union_ligera
        .difference(union_original)
        .area / 1_000_000
    )

    solapamiento = max(
        0.0,

        (
            sum(
                geom.area
                for geom in ligero.values()
            )
            - union_ligera.area
        ) / 1_000_000
    )

    # ======================================
    # 8. COMPARAR FRONTERAS VECINAS
    # ======================================

    fronteras = 0
    modificadas = 0
    ejemplos = []
    revisadas = set()

    for arista in grafo["aristas"]:

        a = str(arista["source"])
        b = str(arista["target"])

        if (
            a not in original
            or b not in original
            or a == b
        ):
            raise ValueError(
                f"Arista invalida: {a}-{b}"
            )

        par = tuple(sorted((a, b)))

        if par in revisadas:
            raise ValueError(
                f"Arista duplicada: {par}"
            )

        revisadas.add(par)

        original_comun = (
            original[a].boundary
            .intersection(
                original[b].boundary
            )
            .length
        )

        if original_comun <= 100:
            continue

        fronteras += 1

        ligero_comun = (
            ligero[a].boundary
            .intersection(
                ligero[b].boundary
            )
            .length
        )

        if ligero_comun < (
            0.8 * original_comun
        ):

            modificadas += 1

            ejemplos.append({
                "municipios": f"{a}-{b}",

                "frontera_original_km":
                    round(original_comun / 1000, 3),

                "frontera_ligera_km":
                    round(ligero_comun / 1000, 3)
            })

    # ======================================
    # 9. VERIFICAR POSICIONES DE NODOS
    # ======================================

    fuera_original = []
    fuera_ligero = []

    for nodo in grafo["nodos"]:

        clave = str(nodo["id"])

        if clave not in original:
            raise ValueError(
                f"Nodo desconocido: {clave}"
            )

        coordenadas = nodo.get(
            "geografico_lonlat"
        )

        if (
            not isinstance(coordenadas, list)
            or len(coordenadas) != 2
        ):
            raise ValueError(
                f"Coordenadas invalidas: {clave}"
            )

        punto = transform(
            transformar,
            Point(coordenadas)
        )

        if not original[clave].covers(punto):
            fuera_original.append(clave)

        if not ligero[clave].covers(punto):
            fuera_ligero.append(clave)

    # ======================================
    # 10. CALCULAR RESUMEN
    # ======================================

    bytes_original = (
        DATOS / "municipios.geojson"
    ).stat().st_size

    bytes_ligero = (
        DATOS / "municipios_ligero.geojson"
    ).stat().st_size

    reduccion = 100 * (
        1 - bytes_ligero / bytes_original
    )

    cambios = [
        abs(fila["cambio_area_pct"])
        for fila in filas
    ]

    reporte = {
        "municipios": len(filas),
        "aristas_revisadas": len(revisadas),

        "proyeccion_metrica": "EPSG:6368",

        "reduccion_archivo_pct":
            round(reduccion, 2),

        "max_cambio_area_municipal_pct":
            round(max(cambios), 4),

        "mediana_cambio_area_municipal_pct":
            round(median(cambios), 4),

        "superficie_perdida_km2":
            round(perdida, 3),

        "superficie_anadida_km2":
            round(adicion, 3),

        "solapamiento_km2":
            round(solapamiento, 3),

        "fronteras_compartidas":
            fronteras,

        "fronteras_modificadas":
            modificadas,

        "ejemplos":
            ejemplos[:10],

        "nodos_fuera_original":
            fuera_original,

        "nodos_fuera_ligero":
            fuera_ligero,

        "advertencia": (
            "Los cambios de superficie "
            "incluyen diferencias del contorno "
            "estatal. No equivalen exclusivamente "
            "a huecos entre municipios."
        )
    }

    # ======================================
    # 11. EXPORTAR CSV
    # ======================================

    ruta_csv = (
        SALIDA / "20_detalle_geometrico.csv"
    )

    with ruta_csv.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=list(filas[0])
        )

        escritor.writeheader()
        escritor.writerows(filas)

    # ======================================
    # 12. EXPORTAR JSON
    # ======================================

    ruta_json = (
        SALIDA / "20_calidad_cartografia.json"
    )

    with ruta_json.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            reporte,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    # ======================================
    # 13. RESULTADOS
    # ======================================

    print(
        "\n=== ETAPA 20.3: "
        "VALIDACION GEOMETRICA ==="
    )

    print(
        "Municipios:", len(filas)
    )

    print(
        "Aristas revisadas:", len(revisadas)
    )

    print(
        "Reduccion archivo:",
        f"{reduccion:.2f}%"
    )

    print(
        "Maximo cambio area:",
        f"{max(cambios):.4f}%"
    )

    print(
        "Superficie perdida:",
        f"{perdida:.3f} km2"
    )

    print(
        "Superficie anadida:",
        f"{adicion:.3f} km2"
    )

    print(
        "Solapamiento:",
        f"{solapamiento:.3f} km2"
    )

    print(
        "Fronteras modificadas:",
        f"{modificadas}/{fronteras}"
    )

    print(
        "Nodos fuera del poligono ligero:",
        len(fuera_ligero)
    )

    print(
        "\nReportes generados correctamente."
    )

    print(
        "No se modificaron datos originales."
    )


if __name__ == "__main__":
    main()
