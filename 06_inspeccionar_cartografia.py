
from pathlib import Path
import sqlite3

# ==========================================
# 1. UBICAR LA CARTOGRAFÍA
# ==========================================

RAIZ = Path(__file__).resolve().parent.parent
CRUDA = RAIZ / "Data Cruda"

archivos = list(
    CRUDA.rglob("limite_municipal_jalisco_iieg.gpkg")
)

if len(archivos) != 1:
    raise FileNotFoundError(
        f"Esperaba un GeoPackage. Encontré {len(archivos)}."
    )

ruta = archivos[0]

print("\n=== CARTOGRAFÍA JALISCO ===")
print("Archivo:", ruta.name)

# ==========================================
# 2. ABRIR EL GEOPACKAGE
# ==========================================

# GeoPackage utiliza SQLite internamente.
conexion = sqlite3.connect(str(ruta))

# ==========================================
# 3. IDENTIFICAR CAPAS GEOGRÁFICAS
# ==========================================

capas = conexion.execute("""
    SELECT table_name, data_type, identifier, srs_id
    FROM gpkg_contents
""").fetchall()

for nombre, tipo, identificador, srs in capas:

    print("\nCAPA:", nombre)
    print("Tipo:", tipo)
    print("Sistema de referencia:", srs)

    # Consultar los nombres de las columnas.
    columnas = conexion.execute(
        f'PRAGMA table_info("{nombre}")'
    ).fetchall()

    print("\nCOLUMNAS:")

    for columna in columnas:
        print("-", columna[1], ":", columna[2])

    # Contar registros sin cargar geometrías.
    total = conexion.execute(
        f'SELECT COUNT(*) FROM "{nombre}"'
    ).fetchone()[0]

    print("\nRegistros:", total)

conexion.close()

print("\nInspección terminada.")
