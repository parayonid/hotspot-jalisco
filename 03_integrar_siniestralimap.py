
from pathlib import Path
from collections import Counter
import csv
import json

# ============================================
# 1. UBICACIÓN DE LOS DATOS
# ============================================

RAIZ = Path(__file__).resolve().parent.parent

ORIGEN = (
    RAIZ / "Data Cruda"
    / "Siniestralimap"
    / "siniestralimap_2015-2025.csv"
)

DESTINO = RAIZ / "Data Procesada"
DESTINO.mkdir(parents=True, exist_ok=True)


# ============================================
# 2. RECONSTRUIR SINIESTROS ÚNICOS
# ============================================

eventos = {}
filas_totales = 0

with ORIGEN.open(
    "r", encoding="utf-8-sig", newline=""
) as archivo:

    for fila in csv.DictReader(archivo):
        filas_totales += 1

        identificador = fila["Id"].strip()

        if not identificador:
            raise ValueError(
                f"Fila {filas_totales}: Id vacío"
            )

        if identificador not in eventos:
            eventos[identificador] = {
                "id_siniestro": identificador,
                "fecha": fila["fecha"],
                "anio": fila["anio"],
                "mes_anio": fila["mes_anio"],
                "municipio": fila["mun"],
                "tipo_siniestro": fila["tipo_siniestro"],
                "longitud": "",
                "latitud": "",
                "personas_fallecidas": 0,
                "personas_heridas": 0,
                "personas_ilesas": 0,
                "filas_origen": 0,
                "_marcas": 0,
            }

        evento = eventos[identificador]
        evento["filas_origen"] += 1

        if fila["contador_siniestro"].strip() == "1":
            evento["_marcas"] += 1

            evento["fecha"] = fila["fecha"]
            evento["municipio"] = fila["mun"]
            evento["tipo_siniestro"] = fila["tipo_siniestro"]

        # Cada fila describe una persona involucrada.
        for campo, destino in [
            ("dmuerto", "personas_fallecidas"),
            ("dherido", "personas_heridas"),
            ("dileso", "personas_ilesas"),
        ]:
            evento[destino] += int(
                fila[campo].strip() or 0
            )

        # Coordenadas de la intersección vial próxima.
        if (
            evento["longitud"] == ""
            and fila["x"]
            and fila["y"]
        ):
            try:
                longitud = float(fila["x"])
                latitud = float(fila["y"])

                if (
                    -106 <= longitud <= -101
                    and 18 <= latitud <= 23
                ):
                    evento["longitud"] = longitud
                    evento["latitud"] = latitud

            except ValueError:
                pass


# ============================================
# 3. VALIDAR LOS EVENTOS
# ============================================

marcas_invalidas = sum(
    e["_marcas"] != 1
    for e in eventos.values()
)

if marcas_invalidas:
    raise ValueError(
        f"{marcas_invalidas} siniestros "
        "no tienen una marca única"
    )

for evento in eventos.values():
    del evento["_marcas"]

    evento["coordenadas_validas"] = int(
        evento["longitud"] != ""
    )


# ============================================
# 4. EXPORTAR EVENTOS ÚNICOS
# ============================================

columnas = list(
    next(iter(eventos.values())).keys()
)

ruta_eventos = DESTINO / "03_siniestros_unicos.csv"

with ruta_eventos.open(
    "w", encoding="utf-8-sig", newline=""
) as archivo:

    writer = csv.DictWriter(
        archivo, fieldnames=columnas
    )

    writer.writeheader()
    writer.writerows(eventos.values())


# ============================================
# 5. CONTEOS MUNICIPIO-AÑO
# ============================================

conteos = Counter(
    (e["municipio"], e["anio"])
    for e in eventos.values()
)

ruta_resumen = (
    DESTINO / "03_siniestros_municipio_anio.csv"
)

with ruta_resumen.open(
    "w", encoding="utf-8-sig", newline=""
) as archivo:

    writer = csv.writer(archivo)

    writer.writerow([
        "municipio",
        "anio",
        "siniestros_registrados"
    ])

    for (municipio, anio), cantidad in sorted(
        conteos.items()
    ):
        writer.writerow([
            municipio, anio, cantidad
        ])


# ============================================
# 6. EXPORTAR CAPA GEOGRÁFICA
# ============================================

features = []

for e in eventos.values():

    if e["coordenadas_validas"]:
        features.append({
            "type": "Feature",

            "geometry": {
                "type": "Point",
                "coordinates": [
                    e["longitud"],
                    e["latitud"]
                ]
            },

            "properties": {
                "id_siniestro": e["id_siniestro"],
                "anio": e["anio"],
                "municipio": e["municipio"],
                "tipo_siniestro": e["tipo_siniestro"],
                "personas_fallecidas": e["personas_fallecidas"],
                "personas_heridas": e["personas_heridas"]
            }
        })

ruta_geojson = (
    DESTINO / "03_siniestros_puntos.geojson"
)

with ruta_geojson.open(
    "w", encoding="utf-8"
) as archivo:

    json.dump(
        {
            "type": "FeatureCollection",
            "features": features
        },
        archivo,
        ensure_ascii=False
    )


# ============================================
# 7. RESULTADOS
# ============================================

print("\n=== SINIESTRALIMAP INTEGRADO ===")

print("Filas originales:", filas_totales)
print("Siniestros únicos:", len(eventos))
print("Siniestros con coordenadas:", len(features))

print(
    "Siniestros sin coordenadas:",
    len(eventos) - len(features)
)

print("Archivo de eventos:", ruta_eventos.name)
print("Resumen municipal:", ruta_resumen.name)
print("Puntos geográficos:", ruta_geojson.name)
