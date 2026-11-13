
r"""HOTSPOT | Etapa 22.1

Integracion inicial de los visores
existentes sin reescribirlos.

Uso desde hotspot-mvp:

    ..\.venv\Scripts\python.exe .\22_preparar_app.py

ENTRADAS:

    19_visor_optimizado.html
    21_visor_red_espectral.html

    18_panel_cientifico.js
    22_puente.js
    22_app.html

SALIDAS:

    22_visor_municipal.html
    22_visor_urbano.html

No sobrescribe los visores originales
ni modifica los datos cientificos.
"""

from pathlib import Path
import re


# ==========================================
# 1. CONFIGURAR DIRECTORIO
# ==========================================

BASE = Path(__file__).resolve().parent


# ==========================================
# 2. COMPROBAR QUE EXISTE UN ARCHIVO
# ==========================================

def require(filename: str) -> Path:

    path = BASE / filename

    if not path.is_file():

        raise FileNotFoundError(
            f"Falta {filename} en {BASE}"
        )

    return path


# ==========================================
# 3. INSERTAR SCRIPT ANTES DE </body>
# ==========================================

def insert_before_body(
    html: str,
    script: str
) -> str:

    if not re.search(
        r"</body\s*>",
        html,
        re.I
    ):

        raise ValueError(
            "El visor de origen "
            "no contiene </body>."
        )

    return re.sub(

        r"</body\s*>",

        lambda _:
            script + "\n</body>",

        html,

        count=1,

        flags=re.I
    )


# ==========================================
# 4. GENERAR UNA COPIA INTEGRADA
# ==========================================

def clone(
    name: str,
    output: str,
    view: str,
    add_science=False
) -> None:

    # Leer el visor original.

    html = require(name).read_text(
        encoding="utf-8-sig"
    )

    # Evitar inyectar el puente dos veces.

    if "22_puente.js" in html:

        raise ValueError(
            f"El visor de origen {name} "
            "ya incluye 22_puente.js"
        )

    # ======================================
    # 5. INYECTAR PANEL CIENTIFICO
    # ======================================

    if (
        add_science
        and
        "18_panel_cientifico.js" not in html
    ):

        html = insert_before_body(

            html,

            '<script src="./18_panel_cientifico.js"></script>'
        )

    # ======================================
    # 6. INYECTAR PUENTE DE ESTADO
    # ======================================

    html = insert_before_body(

        html,

        (
            '<script src="./22_puente.js" '
            f'data-hotspot-view="{view}"></script>'
        )
    )

    # ======================================
    # 7. GUARDAR COPIA
    # ======================================

    path = BASE / output

    path.write_text(
        html,
        encoding="utf-8"
    )

    print(

        f"Generado: {output} "

        f"({path.stat().st_size:,} bytes)"
    )


# ==========================================
# 8. EJECUCION PRINCIPAL
# ==========================================

def main():

    # Verificar scripts necesarios.

    for filename in (

        "19_papiroflexia_three.js",

        "21_red_espectral_three.js",

        "18_panel_cientifico.js",

        "22_puente.js",

        "22_app.html"

    ):

        require(filename)

    # ======================================
    # 9. INTEGRAR VISOR MUNICIPAL
    # ======================================

    clone(

        "19_visor_optimizado.html",

        "22_visor_municipal.html",

        "municipal",

        add_science=True
    )

    # ======================================
    # 10. INTEGRAR VISOR URBANO
    # ======================================

    clone(

        "21_visor_red_espectral.html",

        "22_visor_urbano.html",

        "urbano"
    )

    # ======================================
    # 11. RESULTADO
    # ======================================

    print(
        "\nETAPA 22.1 LISTA."
    )

    print(
        "Abre: "
        "http://localhost:8000/22_app.html"
    )

    print(
        "Los HTML originales, "
        "las escenas 3D y los JSON "
        "no se modificaron."
    )

    print(
        "Nota: esta primera integracion "
        "navega entre modulos independientes; "
        "la unificacion interna es posterior."
    )


if __name__ == "__main__":
    main()
