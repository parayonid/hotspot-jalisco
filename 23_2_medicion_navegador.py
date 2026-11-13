
r"""HOTSPOT | Etapa 23.2: pruebas reproducibles desde Chromium.

Requisitos (en el mismo venv del proyecto):
  python -m pip install playwright
  python -m playwright install chromium

Con el servidor HTTP local funcionando, ejecutar desde hotspot-mvp:
  ..\.venv\Scripts\python.exe .\23_2_medicion_navegador.py

Opciones:
  --headless       Prueba automatica sin interfaz (NO comparable para FPS real)
  --ciclos 3       Numero de rondas por las cinco vistas
  --sin-3d         Solo verificar la navegacion

Entradas: app local http://localhost:8000/22_3_index.html
Salidas: ../Data Procesada/23_2_rendimiento.json y .md

NO cambia los datos ni los archivos del frontend.
La metrica RAF mide cadencia del hilo grafico DURANTE la animacion;
no es una medicion exacta de FPS de la GPU ni de memoria de video.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import (
        sync_playwright,
        TimeoutError as PlaywrightTimeout
    )
except ImportError as exc:
    raise SystemExit(
        "Falta Playwright. Ejecuta:\n"
        "..\\.venv\\Scripts\\python.exe -m pip install playwright\n"
        "y luego:\n"
        "..\\.venv\\Scripts\\python.exe -m playwright install chromium"
    ) from exc

# ==========================================
# 1. CONFIGURACION
# ==========================================

BASE = Path(__file__).resolve().parent

REPORTES = BASE.parent / "Data Procesada"

MODOS = (
    "red",
    "urbano3d",
    "territorio",
    "municipal3d",
    "ciencia"
)

# ==========================================
# 2. ESPERAR UN ELEMENTO VISIBLE
# ==========================================

def esperar(
    panel,
    selector,
    timeout=22000
):

    panel.locator(selector).wait_for(
        state="visible",
        timeout=timeout
    )

# ==========================================
# 3. MEDIR CADENCIA REQUEST ANIMATION FRAME
# ==========================================

def medir_raf(
    page,
    frame,
    boton,
    rango,
    espera_ms
):

    """
    Mide la cadencia de requestAnimationFrame
    mientras la escena esta animada.

    No representa FPS reales de la GPU.
    """

    # Reiniciar el deslizador.

    frame.locator(rango).evaluate(
        """el => {
            el.value = '0';

            el.dispatchEvent(
                new Event(
                    'input',
                    {bubbles: true}
                )
            );
        }"""
    )

    # ======================================
    # 4. INSTRUMENTAR RAF
    # ======================================

    frame.locator("body").evaluate(
        """() => {

            const anteriores =
                window.__hotspotQA;

            if (anteriores) {
                anteriores.activo = false;
            }

            const probe = {
                activo: true,
                tiempos: []
            };

            window.__hotspotQA = probe;

            function tick(t) {

                if (!probe.activo) {
                    return;
                }

                const b = document.querySelector(
                    probe.boton
                );

                if (
                    b &&
                    /Pausar/i.test(b.textContent)
                ) {
                    probe.tiempos.push(t);
                }

                requestAnimationFrame(tick);
            }

            requestAnimationFrame(tick);
        }"""
    )

    frame.locator("body").evaluate(
        "(el, s) => window.__hotspotQA.boton = s",
        boton
    )

    # Iniciar animacion.

    frame.locator(boton).click(
        timeout=10000
    )

    page.wait_for_timeout(
        espera_ms
    )

    # ======================================
    # 5. RECUPERAR MUESTRAS
    # ======================================

    datos = frame.locator("body").evaluate(
        """() => {

            const p = window.__hotspotQA;

            p.activo = false;

            return p.tiempos;
        }"""
    )

    if len(datos) < 4:

        return {
            "muestras_raf": len(datos),
            "aviso": "Sin suficientes fotogramas"
        }

    # ======================================
    # 6. INTERVALOS ENTRE FOTOGRAMAS
    # ======================================

    intervalos = [

        b - a

        for a, b in zip(
            datos,
            datos[1:]
        )

        if b > a
    ]

    if not intervalos:

        return {
            "muestras_raf": len(datos),
            "aviso": "Intervalos RAF invalidos"
        }

    fps = (
        1000.0
        /
        statistics.mean(intervalos)
    )

    p95 = sorted(intervalos)[

        math.ceil(
            0.95 * len(intervalos)
        ) - 1
    ]

    pausas = sum(
        d > 50
        for d in intervalos
    )

    return {

        "muestras_raf":
            len(datos),

        "cadencia_raf_aprox_hz":
            round(fps, 2),

        "intervalo_raf_p95_ms":
            round(p95, 2),

        "porcentaje_intervalos_mayores_50ms":
            round(
                100 * pausas / len(intervalos),
                2
            ),

        "aviso":
            "Cadencia RAF, NO FPS reales de GPU"
    }

# ==========================================
# 7. PROBAR PAPIROFLEXIAS 3D
# ==========================================

def probar_3d(page, modo):

    frame = page.frame_locator(
        "#module"
    )

    if modo == "municipal3d":

        (
            launch,
            panel,
            canvas,
            status,
            boton,
            rango,
            espera
        ) = (

            ".pap-launch",
            ".pap-panel",
            "#papView canvas",
            "#papStatus",
            "#papPlay",
            "#papRange",
            3300
        )

    else:

        (
            launch,
            panel,
            canvas,
            status,
            boton,
            rango,
            espera
        ) = (

            "#open3d",
            "#spectralPanel",
            "#threeHost canvas",
            "#threeStatus",
            "#play3d",
            "#tRange",
            4200
        )

    # ======================================
    # 8. ABRIR ESCENA
    # ======================================

    esperar(
        frame,
        launch
    )

    if not frame.locator(panel).is_visible():

        frame.locator(launch).click()

    inicio = time.perf_counter()

    esperar(
        frame,
        canvas,
        timeout=30000
    )

    # El canvas puede existir antes
    # de que WebGL termine de preparar datos.

    if modo == "municipal3d":

        frame.locator(status).filter(
            has_text="WebGL"
        ).wait_for(
            timeout=30000
        )

    else:

        frame.locator(status).filter(
            has_text="WebGL listo"
        ).wait_for(
            timeout=30000
        )

    carga_ms = round(

        (
            time.perf_counter() - inicio
        ) * 1000,

        1
    )

    # ======================================
    # 9. MEDIR ANIMACION
    # ======================================

    cadencia = medir_raf(

        page,
        frame,
        boton,
        rango,
        espera
    )

    return {

        "carga_escena_ms":
            carga_ms,

        "texto_estado":
            frame.locator(status).inner_text(),

        **cadencia
    }

# ==========================================
# 10. PROBAR UNA VISTA
# ==========================================

def probar_modo(
    page,
    modo,
    ciclo,
    timeout,
    sin_3d
):

    fila = {

        "ciclo": ciclo,
        "vista": modo,
        "ok": False
    }

    inicio = time.perf_counter()

    try:

        # ==================================
        # 11. CAMBIAR DE MODULO
        # ==================================

        page.locator(
            f'nav [data-mode="{modo}"]'
        ).click(
            timeout=timeout
        )

        page.locator("#loading").wait_for(
            state="hidden",
            timeout=timeout
        )

        frame = page.frame_locator(
            "#module"
        )

        esperar(
            frame,
            "body",
            timeout=timeout
        )

        fila["carga_navegacion_ms"] = round(

            (
                time.perf_counter() - inicio
            ) * 1000,

            1
        )

        fila["estado_padre"] = (
            page.locator(
                "#appStatus"
            ).inner_text()
        )

        # ==================================
        # 12. VISOR TERRITORIAL
        # ==================================

        if modo == "territorio":

            frame.locator("#status").filter(
                has_text="125 municipios cargados"
            ).wait_for(
                timeout=timeout
            )

            esperar(
                frame,
                ".maplibregl-canvas",
                timeout=timeout
            )

        # ==================================
        # 13. VISOR URBANO
        # ==================================

        elif modo == "red":

            frame.locator("#status").filter(
                has_text="447 celdas"
            ).wait_for(
                timeout=timeout
            )

            esperar(
                frame,
                ".maplibregl-canvas",
                timeout=timeout
            )

        # ==================================
        # 14. PANEL CIENTIFICO
        # ==================================

        elif modo == "ciencia":

            esperar(
                frame,
                ".ci-launch",
                timeout=timeout
            )

            if not frame.locator(
                ".ci-panel"
            ).is_visible():

                frame.locator(
                    ".ci-launch"
                ).click(
                    timeout=timeout
                )

            esperar(
                frame,
                ".ci-panel",
                timeout=timeout
            )

        # ==================================
        # 15. PAPIROFLEXIAS
        # ==================================

        if (
            modo in (
                "urbano3d",
                "municipal3d"
            )
            and not sin_3d
        ):

            fila["animacion"] = probar_3d(
                page,
                modo
            )

        fila["ok"] = True

    except Exception as exc:

        fila["error"] = str(exc)[:600]

    return fila

# ==========================================
# 16. EXPORTAR INFORMES
# ==========================================

def exportar(datos):

    REPORTES.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta_json = (
        REPORTES /
        "23_2_rendimiento.json"
    )

    ruta_md = (
        REPORTES /
        "23_2_rendimiento.md"
    )

    # ======================================
    # 17. JSON
    # ======================================

    ruta_json.write_text(

        json.dumps(
            datos,
            indent=2,
            ensure_ascii=False
        ),

        encoding="utf-8"
    )

    # ======================================
    # 18. MARKDOWN
    # ======================================

    filas = [

        "# HOTSPOT — Etapa 23.2 | Rendimiento en Chromium",

        "",

        f"**Estado:** {datos['estado']}",

        f"**URL:** {datos['url']}",

        f"**Navegador sin interfaz:** {datos['headless']}",

        "",

        "| Ciclo | Vista | Navegación (ms) | Cadencia RAF aprox. (Hz) | Resultado |",

        "|---:|---|---:|---:|---|"
    ]

    for fila in datos["pruebas"]:

        animacion = fila.get(
            "animacion",
            {}
        )

        raf = animacion.get(
            "cadencia_raf_aprox_hz",
            "—"
        )

        resultado = (
            "OK"
            if fila["ok"]
            else "ERROR"
        )

        filas.append(

            f"| {fila['ciclo']} "
            f"| {fila['vista']} "
            f"| {fila.get('carga_navegacion_ms', '—')} "
            f"| {raf} "
            f"| {resultado} |"
        )

    filas += [

        "",

        "## Limitaciones de la medición",

        "",

        "- La cadencia requestAnimationFrame es un indicador del hilo gráfico durante la animación; NO mide FPS reales de GPU.",

        "- Las pruebas automatizadas no sustituyen la evaluación visual, accesibilidad ni la medición de memoria/GPU.",

        "- CDN, Internet y teselas cartográficas pueden afectar los tiempos.",

        "- No comparar resultados headless con navegador normal.",

        "",

        "## Errores del navegador",

        ""
    ]

    if datos["errores_navegador"]:

        filas += [

            f"- {e}"

            for e in datos[
                "errores_navegador"
            ][:40]
        ]

    else:

        filas.append(
            "No se capturaron errores JavaScript ni respuestas HTTP fallidas."
        )

    filas += [

        "",

        "## Pruebas manuales pendientes",

        "",

        "- [ ] Inspeccionar consumo de GPU y memoria en Chrome.",

        "- [ ] Probar ambas animaciones, zoom, selección y filtros.",

        "- [ ] Probar Chrome, Edge y móvil.",

        "- [ ] Revisar navegación con teclado.",

        "- [ ] Probar el mapa sin acceso a Internet."
    ]

    ruta_md.write_text(

        "\n".join(filas) + "\n",

        encoding="utf-8"
    )

    return ruta_json, ruta_md

# ==========================================
# 19. EJECUCION PRINCIPAL
# ==========================================

def main():

    parser = argparse.ArgumentParser(

        description=(
            "Pruebas de navegacion "
            "y animaciones Hotspot"
        )
    )

    parser.add_argument(

        "--url",

        default=(
            "http://localhost:8000/"
            "22_3_index.html"
        )
    )

    parser.add_argument(

        "--ciclos",

        type=int,

        default=2
    )

    parser.add_argument(

        "--headless",

        action="store_true"
    )

    parser.add_argument(

        "--sin-3d",

        action="store_true"
    )

    parser.add_argument(

        "--ejecutable",

        help=(
            "Ruta opcional al navegador "
            "Chromium/Chrome"
        )
    )

    parser.add_argument(

        "--timeout",

        type=int,

        default=25000,

        help="Espera maxima en ms"
    )

    args = parser.parse_args()

    # ======================================
    # 20. VALIDAR ARGUMENTOS
    # ======================================

    origen = urlparse(
        args.url
    )

    if (
        origen.scheme != "http"
        or origen.hostname not in (
            "localhost",
            "127.0.0.1"
        )
    ):

        parser.error(
            "Por seguridad, usa una URL "
            "local http://localhost"
        )

    if not (
        1 <= args.ciclos <= 10
    ):

        parser.error(
            "--ciclos debe estar entre 1 y 10"
        )

    # ======================================
    # 21. PREPARAR PRUEBAS
    # ======================================

    errores = []

    pruebas = []

    print(
        "\n=== HOTSPOT | ETAPA 23.2 ==="
    )

    print(
        "Abriendo:",
        args.url
    )

    # ======================================
    # 22. LANZAR CHROMIUM
    # ======================================

    try:

        with sync_playwright() as playwright:

            opciones_navegador = {

                "headless": args.headless
            }

            if args.ejecutable:

                opciones_navegador[
                    "executable_path"
                ] = args.ejecutable

            browser = playwright.chromium.launch(
                **opciones_navegador
            )

            context = browser.new_context(

                viewport={
                    "width": 1440,
                    "height": 900
                }
            )

            page = context.new_page()

            page.set_default_timeout(
                args.timeout
            )

            # ==================================
            # 23. ESCUCHAR ERRORES DEL NAVEGADOR
            # ==================================

            page.on(

                "pageerror",

                lambda error:
                    errores.append(
                        f"JS: {str(error)[:300]}"
                    )
            )

            page.on(

                "console",

                lambda msg:
                    errores.append(
                        f"Consola: {msg.text[:300]}"
                    )
                    if msg.type == "error"
                    else None
            )

            page.on(

                "requestfailed",

                lambda req:
                    errores.append(
                        f"Red: {req.url[:220]}"
                    )
            )

            page.on(

                "response",

                lambda res:
                    errores.append(
                        f"HTTP {res.status}: "
                        f"{res.url[:220]}"
                    )
                    if res.status >= 400
                    else None
            )

            # ==================================
            # 24. ABRIR HOTSPOT
            # ==================================

            page.goto(

                args.url,

                wait_until="domcontentloaded",

                timeout=args.timeout
            )

            page.locator(
                "nav [data-mode]"
            ).first.wait_for()

            # ==================================
            # 25. RECORRER LAS CINCO VISTAS
            # ==================================

            for ciclo in range(
                1,
                args.ciclos + 1
            ):

                for modo in MODOS:

                    fila = probar_modo(

                        page,
                        modo,
                        ciclo,
                        args.timeout,
                        args.sin_3d
                    )

                    pruebas.append(
                        fila
                    )

                    estado = (
                        "OK"
                        if fila["ok"]
                        else "ERROR"
                    )

                    duracion = fila.get(
                        "carga_navegacion_ms",
                        "—"
                    )

                    print(

                        f"[{estado}] {modo} "
                        f"(ciclo {ciclo}) "
                        f"· navegacion {duracion} ms"
                    )

                    if "animacion" in fila:

                        print(

                            "   RAF aprox.:",

                            fila["animacion"].get(
                                "cadencia_raf_aprox_hz",
                                "sin dato"
                            ),

                            "Hz"
                        )

                    if "error" in fila:

                        print(

                            "   Detalle:",

                            fila["error"].splitlines()[0]
                        )

            context.close()

            browser.close()

    except Exception as exc:

        errores.append(

            "No se completo la ejecucion: "
            f"{exc}"
        )

        print(
            "[ERROR]",
            str(exc).splitlines()[0]
        )

    # ======================================
    # 26. ESTADO GENERAL
    # ======================================

    estado = (

        "REVISAR"

        if (
            errores
            or any(
                not x["ok"]
                for x in pruebas
            )
        )

        else "SIN_ERRORES_AUTOMATICOS"
    )

    reporte = {

        "etapa": "23.2",

        "generado_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "url":
            args.url,

        "headless":
            args.headless,

        "ciclos":
            args.ciclos,

        "estado":
            estado,

        "pruebas":
            pruebas,

        "errores_navegador":
            sorted(
                set(errores)
            )
    }

    rutas = exportar(
        reporte
    )

    # ======================================
    # 27. RESULTADOS EN TERMINAL
    # ======================================

    print(
        f"\nEstado: {estado}"
    )

    print(
        f"Pruebas: {len(pruebas)}"
    )

    print(
        "Incidencias:",
        len(
            reporte[
                "errores_navegador"
            ]
        )
    )

    print(
        "Reportes:",

        *rutas,

        sep="\n  "
    )

    print(
        "AVISO: cadencia RAF aproximada, "
        "NO FPS reales de GPU."
    )

    return (
        0
        if estado == "SIN_ERRORES_AUTOMATICOS"
        else 1
    )

if __name__ == "__main__":

    raise SystemExit(
        main()
    )