
r"""HOTSPOT | Etapa 23.1 - auditoria de integracion y preparacion de despliegue.

Colocar en la raiz de hotspot-mvp. Ejemplo Windows PowerShell:

    ..\.venv\Scripts\python.exe .\23_1_auditoria_despliegue.py
    ..\.venv\Scripts\python.exe .\23_1_auditoria_despliegue.py --http http://localhost:8000

Solo lectura sobre los archivos del proyecto. Genera informes en la carpeta
hermana 'Data Procesada'. No modifica los datos, modelos, visores ni scripts.

Las pruebas de archivo y HTTP NO reemplazan una prueba real del navegador,
FPS, accesibilidad, responsividad ni una validacion de riesgo vial.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


# ==========================================
# 1. ARCHIVOS REQUERIDOS
# ==========================================

REQUIRED_FILES = [
    "22_3_index.html",
    "app/22_3.css",
    "app/22_3.js",
    "22_visor_municipal.html",
    "22_2_visor_urbano.html",
    "22_puente.js",
    "18_panel_cientifico.js",
    "19_papiroflexia_three.js",
    "22_2_red_espectral_three.js",
    "22_2_contexto_urbano.js",
    "22_2_estabilidad.js",
    "datos/municipios.json",
    "datos/municipios_ligero.geojson",
    "datos/siniestros.geojson",
    "datos/seguridad.json",
    "datos/modelos.json",
    "datos/grafo.json",
    "datos/19_escena_espectral.json",
    "datos/21_zonas_siniestros.geojson",
    "datos/21_resumen_zonas.json",
    "datos/21_grafo_siniestros_2025.json",
    "datos/21_embedding_siniestros_2025.json",
    "datos/21_estabilidad_zonas_2025.geojson",
    "datos/22_2_contexto_urbano.json",
]


# ==========================================
# 2. ARCHIVOS QUE SE VERIFICAN POR HTTP
# ==========================================

HTTP_FILES = [
    "22_3_index.html",
    "app/22_3.css",
    "app/22_3.js",
    "22_visor_municipal.html",
    "22_2_visor_urbano.html",
    "22_2_red_espectral_three.js",
    "22_2_contexto_urbano.js",
    "datos/municipios_ligero.geojson",
    "datos/21_embedding_siniestros_2025.json",
    "datos/21_estabilidad_zonas_2025.geojson",
    "datos/22_2_contexto_urbano.json",
]


# ==========================================
# 3. DETECTAR REFERENCIAS HTML
# ==========================================

class LocalReferences(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.paths: list[str] = []
        self.externals: list[str] = []

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        if tag not in {
            "script",
            "link",
            "iframe",
            "img"
        }:
            return

        properties = dict(attrs)

        value = (
            properties.get("src")
            or properties.get("href")
        )

        if (
            not value
            or value.startswith((
                "#",
                "data:",
                "blob:",
                "mailto:"
            ))
        ):
            return

        if value.startswith((
            "https://",
            "http://",
            "//"
        )):

            self.externals.append(value)

        else:

            self.paths.append(
                value.split("?", 1)[0]
                     .split("#", 1)[0]
            )


# ==========================================
# 4. CLASE PRINCIPAL DE AUDITORIA
# ==========================================

class Auditor:

    def __init__(self, base: Path):

        self.base = base.resolve()

        self.checks = []

        self.metrics = {}

    # ======================================
    # 5. REGISTRAR COMPROBACIONES
    # ======================================

    def record(
        self,
        status: str,
        area: str,
        detail: str
    ):

        self.checks.append({
            "estado": status,
            "area": area,
            "detalle": str(detail)
        })

        print(
            f"[{status}] {area}: {detail}"
        )

    def require(
        self,
        valid: bool,
        area: str,
        good: str,
        bad: str
    ):

        self.record(
            "OK" if valid else "ERROR",
            area,
            good if valid else bad
        )

        return valid

    def info(
        self,
        area: str,
        detail: str
    ):

        self.record(
            "AVISO",
            area,
            detail
        )

    # ======================================
    # 6. CARGAR JSON
    # ======================================

    def load(self, name: str):

        path = self.base / name

        if not path.is_file():
            return None

        try:

            with path.open(
                encoding="utf-8-sig"
            ) as fh:

                return json.load(fh)

        except (
            OSError,
            ValueError
        ) as exc:

            self.record(
                "ERROR",
                name,
                f"JSON ilegible: {exc}"
            )

            return None

    # ======================================
    # 7. CAPTURAR ERRORES DE DATOS
    # ======================================

    def protect(
        self,
        area: str,
        fn
    ):

        try:

            fn()

        except (
            KeyError,
            TypeError,
            ValueError,
            IndexError,
            AttributeError,
            AssertionError
        ) as exc:

            self.record(
                "ERROR",
                area,
                f"Estructura invalida: {exc}"
            )

    # ======================================
    # 8. AUDITAR ARCHIVOS DEL FRONTEND
    # ======================================

    def files(self):

        faltantes = [
            name
            for name in REQUIRED_FILES
            if not (
                self.base / name
            ).is_file()
        ]

        self.require(
            not faltantes,
            "Archivos de produccion",
            (
                f"{len(REQUIRED_FILES)} "
                "recursos locales presentes"
            ),
            (
                "No encontrados: "
                + ", ".join(faltantes)
            )
        )

        for name in (
            "22_3_index.html",
            "22_visor_municipal.html",
            "22_2_visor_urbano.html"
        ):

            path = self.base / name

            if not path.exists():
                continue

            content = path.read_text(
                encoding="utf-8-sig"
            )

            parser = LocalReferences()

            parser.feed(content)

            missing = []

            for asset in parser.paths:

                target = (
                    path.parent / asset
                ).resolve()

                try:

                    is_internal = (
                        target.is_relative_to(
                            self.base
                        )
                    )

                except AttributeError:

                    is_internal = (
                        str(target).startswith(
                            str(self.base)
                        )
                    )

                if (
                    is_internal
                    and not target.is_file()
                ):

                    missing.append(asset)

            self.require(
                not missing,
                f"Referencias HTML {name}",
                (
                    "Scripts, estilos e imagenes "
                    "declarados presentes"
                ),
                (
                    "Rutas rotas: "
                    + ", ".join(missing)
                )
            )

            if parser.externals:

                hosts = sorted({
                    urlparse(
                        u
                        if u.startswith("http")
                        else "https:" + u
                    ).netloc
                    for u in parser.externals
                })

                self.info(
                    name,
                    (
                        "Carga librerias externas: "
                        + ", ".join(hosts)
                    )
                )

        # ==================================
        # 9. MOTOR THREE.JS URBANO
        # ==================================

        motor = (
            self.base
            / "22_2_red_espectral_three.js"
        )

        if motor.exists():

            js = motor.read_text(
                encoding="utf-8-sig"
            )

            self.require(
                "22_2_contexto_urbano.js" in js,
                "Motor 3D urbano",
                "Contexto cartografico importado",
                (
                    "No aparece la importacion de "
                    "22_2_contexto_urbano.js"
                )
            )

        # ==================================
        # 10. VISOR URBANO
        # ==================================

        visor_urbano = (
            self.base
            / "22_2_visor_urbano.html"
        )

        if visor_urbano.exists():

            html = visor_urbano.read_text(
                encoding="utf-8-sig"
            )

            for asset in (
                "22_2_estabilidad.js",
                "22_puente.js",
                "22_2_red_espectral_three.js"
            ):

                self.require(
                    asset in html,
                    "Visor urbano",
                    f"Incluye {asset}",
                    f"No incluye {asset}"
                )

        # ==================================
        # 11. VISOR MUNICIPAL
        # ==================================

        visor_municipal = (
            self.base
            / "22_visor_municipal.html"
        )

        if visor_municipal.exists():

            html = visor_municipal.read_text(
                encoding="utf-8-sig"
            )

            for asset in (
                "22_puente.js",
                "19_papiroflexia_three.js",
                "18_panel_cientifico.js"
            ):

                self.require(
                    asset in html,
                    "Visor municipal",
                    f"Incluye {asset}",
                    f"No incluye {asset}"
                )

    # ======================================
    # 12. AUDITORIA MUNICIPAL
    # ======================================

    def municipal(self):

        data = self.load(
            "datos/municipios.json"
        )

        geo = self.load(
            "datos/municipios_ligero.geojson"
        )

        graph = self.load(
            "datos/grafo.json"
        )

        spec = self.load(
            "datos/19_escena_espectral.json"
        )

        security = self.load(
            "datos/seguridad.json"
        )

        # ==================================
        # 13. MUNICIPIOS Y ATUS
        # ==================================

        if data is not None:

            def check():

                ms = data["municipios"]

                ids = [
                    str(m["cvegeo"])
                    for m in ms
                ]

                na = sum(
                    m.get(
                        "registros_atus_2025"
                    ) is None
                    for m in ms
                )

                self.metrics.update(
                    municipios=len(ms),
                    atus_sin_dato=na
                )

                self.require(
                    (
                        len(ms) == 125
                        and len(set(ids)) == 125
                    ),
                    "Municipios",
                    "125 municipios unicos",
                    (
                        f"Hay {len(ms)} / "
                        f"{len(set(ids))} unicos"
                    )
                )

                self.require(
                    na == 45,
                    "ATUS faltante",
                    "45 valores null preservados",
                    (
                        "Se esperaban 45 null; "
                        f"hay {na}"
                    )
                )

            self.protect(
                "Datos municipales",
                check
            )

        # ==================================
        # 14. CARTOGRAFIA LIGERA
        # ==================================

        if geo is not None:

            self.protect(
                "Cartografia",

                lambda: self.require(
                    (
                        geo.get("type")
                        == "FeatureCollection"
                        and len(
                            geo["features"]
                        ) == 125
                    ),

                    "Cartografia ligera",
                    "125 poligonos disponibles",
                    "Se esperan 125 poligonos"
                )
            )

        # ==================================
        # 15. GRAFOS MUNICIPALES
        # ==================================

        for name, obj, n, e in (
            (
                "Grafo municipal",
                graph,
                125,
                304
            ),
            (
                "Escena espectral municipal",
                spec,
                125,
                304
            )
        ):

            if obj is None:
                continue

            def check(
                obj=obj,
                name=name,
                n=n,
                e=e
            ):

                nodes = obj["nodos"]

                edges = obj["aristas"]

                self.require(
                    (
                        len(nodes) == n
                        and len(edges) == e
                    ),
                    name,
                    f"{n} nodos y {e} aristas",
                    (
                        f"Hay {len(nodes)} nodos "
                        f"y {len(edges)} aristas"
                    )
                )

            self.protect(
                name,
                check
            )

        # ==================================
        # 16. SEGURIDAD REGIONAL
        # ==================================

        if security is not None:

            self.protect(
                "Seguridad regional",

                lambda: self.require(
                    (
                        len(
                            security["registros"]
                        ) == 12195
                    ),

                    "Seguridad regional",

                    "12,195 registros agregados",

                    (
                        f"Hay "
                        f"{len(security['registros'])} "
                        "registros "
                        "(esperados: 12,195)"
                    )
                )
            )

        self.info(
            "Interpretacion cientifica",
            (
                "ATUS null no es cero; "
                "Seguridad es regional, "
                "no son puntos delictivos"
            )
        )

    # ======================================
    # 17. AUDITORIA URBANA
    # ======================================

    def urbano(self):

        points = self.load(
            "datos/siniestros.geojson"
        )

        zones = self.load(
            "datos/21_zonas_siniestros.geojson"
        )

        summary = self.load(
            "datos/21_resumen_zonas.json"
        )

        graph = self.load(
            "datos/21_grafo_siniestros_2025.json"
        )

        emb = self.load(
            "datos/21_embedding_siniestros_2025.json"
        )

        stable = self.load(
            "datos/21_estabilidad_zonas_2025.geojson"
        )

        backdrop = self.load(
            "datos/22_2_contexto_urbano.json"
        )

        # ==================================
        # 18. SINIESTROS GEOREFERENCIADOS
        # ==================================

        if points is not None:

            def check():

                feats = points["features"]

                count25 = sum(
                    int(
                        f.get(
                            "properties",
                            {}
                        ).get("anio", -1)
                    ) == 2025
                    for f in feats
                )

                self.metrics.update(
                    siniestros_total=len(feats),
                    siniestros_2025=count25
                )

                self.require(
                    (
                        len(feats) == 16957
                        and count25 == 1337
                    ),
                    "Siniestros georreferenciados",
                    (
                        "16,957 eventos "
                        "(1,337 de 2025)"
                    ),
                    (
                        f"Total {len(feats)}, "
                        f"2025 {count25}"
                    )
                )

            self.protect(
                "Siniestros",
                check
            )

        # ==================================
        # 19. ZONAS DE SINIESTRALIDAD
        # ==================================

        if zones is not None:

            def check():

                feats = zones["features"]

                active = sum(
                    int(
                        f["properties"].get(
                            "n_2025",
                            0
                        )
                    ) > 0
                    for f in feats
                )

                focus = [
                    f for f in feats
                    if f["properties"].get(
                        "alta_concentracion_2025"
                    ) is True
                ]

                focal_events = sum(
                    int(
                        f["properties"].get(
                            "n_2025",
                            0
                        )
                    )
                    for f in focus
                )

                self.metrics.update(
                    celdas_historicas=len(feats),
                    celdas_2025=active,
                    focos_2025=len(focus)
                )

                result = (
                    len(feats),
                    active,
                    len(focus),
                    focal_events
                )

                self.require(
                    result == (
                        764,
                        447,
                        44,
                        414
                    ),

                    "Zonas urbanas",

                    (
                        "764 historicas; "
                        "447 activas; "
                        "44 destacadas con "
                        "414 eventos"
                    ),

                    f"Obtenido {result}"
                )

            self.protect(
                "Cuadricula de siniestros",
                check
            )

        # ==================================
        # 20. RESUMEN ETAPA 21.1
        # ==================================

        if summary is not None:

            self.protect(
                "Resumen 21.1",

                lambda: self.require(
                    (
                        summary[
                            "total_eventos_georreferenciados"
                        ] == 16957
                        and summary[
                            "eventos_por_anio"
                        ]["2025"] == 1337
                    ),

                    "Resumen de zonas",

                    (
                        "Total y 2025 coinciden "
                        "con etapa 21.1"
                    ),

                    "Totales inconsistentes"
                )
            )

        # ==================================
        # 21. GRAFO URBANO
        # ==================================

        if graph is not None:

            def check():

                nodes = graph["nodos"]

                edges = graph["aristas"]

                components = graph[
                    "resumen"
                ]["componentes"]

                ids = {
                    n["id"]
                    for n in nodes
                }

                valid = all(
                    (
                        e["source"] in ids
                        and e["target"] in ids
                        and e["source"] != e["target"]
                    )
                    for e in edges
                )

                self.require(
                    (
                        (
                            len(nodes),
                            len(edges),
                            components
                        ) == (
                            447,
                            1034,
                            46
                        )
                        and len(ids) == 447
                        and valid
                    ),

                    "Grafo urbano",

                    (
                        "447 nodos / "
                        "1,034 aristas / "
                        "46 componentes; "
                        "IDs correctos"
                    ),

                    (
                        f"Hay {len(nodes)} nodos / "
                        f"{len(edges)} aristas / "
                        f"{components} componentes; "
                        f"referencias validas={valid}"
                    )
                )

            self.protect(
                "Grafo urbano",
                check
            )

        # ==================================
        # 22. EMBEDDING ESPECTRAL URBANO
        # ==================================

        if emb is not None:

            def check():

                nodes = emb["nodos"]

                edges = emb["aristas"]

                spec = [
                    n for n in nodes
                    if n.get(
                        "espectral_xyz"
                    ) is not None
                ]

                non = [
                    n for n in nodes
                    if n.get(
                        "espectral_xyz"
                    ) is None
                ]

                events = sum(
                    int(
                        n.get(
                            "conteo_2025",
                            0
                        )
                    )
                    for n in nodes
                )

                in_major = sum(
                    int(
                        n.get(
                            "conteo_2025",
                            0
                        )
                    )
                    for n in spec
                )

                good_vectors = all(
                    (
                        len(
                            n["espectral_xyz"]
                        ) == 3
                        and all(
                            math.isfinite(
                                float(v)
                            )
                            for v in n[
                                "espectral_xyz"
                            ]
                        )
                    )
                    for n in spec
                )

                self.metrics.update(
                    nodos_urbanos=len(nodes),
                    aristas_urbanas=len(edges),
                    embeddings=len(spec),
                    fuera_embedding=len(non)
                )

                result = (
                    len(nodes),
                    len(edges),
                    len(spec),
                    len(non),
                    events,
                    in_major
                )

                self.require(
                    (
                        result == (
                            447,
                            1034,
                            347,
                            100,
                            1337,
                            1165
                        )
                        and good_vectors
                    ),

                    "Embedding urbano",

                    (
                        "447 nodos; "
                        "347 embeddings; "
                        "100 sin embedding; "
                        "1,337 eventos preservados"
                    ),

                    (
                        f"Resultado {result}; "
                        f"vectores validos="
                        f"{good_vectors}"
                    )
                )

            self.protect(
                "Embedding",
                check
            )

        # ==================================
        # 23. CONSISTENCIA GRAFO-EMBEDDING
        # ==================================

        if (
            graph is not None
            and emb is not None
        ):

            def consistency():

                ids_graph = {
                    n["id"]
                    for n in graph["nodos"]
                }

                ids_emb = {
                    n["id"]
                    for n in emb["nodos"]
                }

                pairs_graph = {
                    tuple(sorted((
                        e["source"],
                        e["target"]
                    )))
                    for e in graph["aristas"]
                }

                pairs_emb = {
                    tuple(sorted((
                        e["source"],
                        e["target"]
                    )))
                    for e in emb["aristas"]
                }

                self.require(
                    (
                        ids_graph == ids_emb
                        and pairs_graph == pairs_emb
                    ),

                    "Contrato grafo / embedding",

                    (
                        "Mismos IDs y mismas "
                        "aristas en ambos archivos"
                    ),

                    (
                        "IDs o aristas difieren "
                        "entre las etapas "
                        "21.2 y 21.3"
                    )
                )

            self.protect(
                "Consistencia urbana",
                consistency
            )

        # ==================================
        # 24. ESTABILIDAD ESPACIAL
        # ==================================

        if stable is not None:

            def check():

                feats = stable["features"]

                ok = all(
                    (
                        f["properties"].get(
                            "promedio_estabilidad_eventos"
                        ) is None
                        or (
                            0 <= float(
                                f["properties"][
                                    "promedio_estabilidad_eventos"
                                ]
                            ) <= 1
                        )
                    )
                    for f in feats
                )

                self.require(
                    (
                        len(feats) == 764
                        and ok
                    ),

                    "Estabilidad espacial",

                    (
                        "764 celdas con indicadores "
                        "en [0,1] o null"
                    ),

                    (
                        f"Celdas={len(feats)}, "
                        f"valores correctos={ok}"
                    )
                )

            self.protect(
                "Estabilidad espacial",
                check
            )

        # ==================================
        # 25. MAPA DE GUADALAJARA
        # ==================================

        if backdrop is not None:

            def check():

                tiles = backdrop["teselas"]

                contours = backdrop[
                    "contornos_guadalajara"
                ]

                self.require(
                    (
                        0 < len(tiles) <= 32
                        and bool(contours)
                    ),

                    "Mapa 3D Guadalajara",

                    (
                        f"{len(tiles)} teselas "
                        "preparadas y "
                        f"{len(contours)} contorno(s)"
                    ),

                    (
                        "Teselas/contornos "
                        "incompletos"
                    )
                )

            self.protect(
                "Cartografia urbana",
                check
            )

        # ==================================
        # 26. LIMITACIONES CIENTIFICAS
        # ==================================

        self.info(
            "Alcance de inferencia",
            (
                "La estabilidad es descriptiva; "
                "los conteos NO son tasas "
                "de riesgo ni causalidad"
            )
        )

        # ==================================
        # 27. INFORME AUXILIAR ETAPA 21.5
        # ==================================

        optional = (
            self.base.parent
            / "Data Procesada"
            / "21_resumen_estabilidad.json"
        )

        if optional.is_file():

            try:

                result = json.loads(
                    optional.read_text(
                        encoding="utf-8-sig"
                    )
                )

                sens = result[
                    "sensibilidad_espacial_2025"
                ]

                measures = (
                    len(
                        sens["escenarios"]
                    ),

                    sens[
                        "eventos_en_6_o_mas_escenarios"
                    ],

                    sens[
                        "eventos_en_9_o_mas_escenarios"
                    ],

                    sens[
                        "eventos_en_12_escenarios"
                    ]
                )

                self.require(
                    measures == (
                        12,
                        411,
                        212,
                        43
                    ),

                    "Estabilidad 21.5",

                    (
                        "12 escenarios; "
                        "eventos persistentes "
                        "411 / 212 / 43"
                    ),

                    (
                        "Resultados distintos: "
                        f"{measures}"
                    )
                )

            except (
                KeyError,
                ValueError,
                TypeError,
                OSError
            ) as exc:

                self.record(
                    "ERROR",
                    "Informe de estabilidad 21.5",
                    str(exc)
                )

        else:

            self.info(
                "Informe 21.5",
                (
                    "No se encontro el JSON "
                    "de analisis auxiliar; "
                    "el GeoJSON del frontend "
                    "se audito"
                )
            )

    # ======================================
    # 28. AUDITORIA DE RECURSOS HTTP
    # ======================================

    def http(self, base_url: str):

        base = (
            base_url.rstrip("/")
            + "/"
        )

        for path in HTTP_FILES:

            try:

                url = urljoin(
                    base,
                    path
                )

                parsed = urlparse(url)

                if parsed.scheme not in {
                    "http",
                    "https"
                }:

                    raise ValueError(
                        "URL HTTP invalida"
                    )

                req = Request(
                    url,
                    method="HEAD",
                    headers={
                        "User-Agent":
                            "HotspotQA/23.1"
                    }
                )

                with urlopen(
                    req,
                    timeout=5
                ) as response:

                    code = response.status

                    ctype = response.headers.get(
                        "Content-Type",
                        ""
                    )

                self.require(
                    code == 200,
                    f"HTTP {path}",
                    f"200 ({ctype})",
                    f"HTTP {code}"
                )

            except (
                HTTPError,
                URLError,
                TimeoutError,
                ValueError,
                OSError
            ) as exc:

                self.record(
                    "ERROR",
                    f"HTTP {path}",
                    str(exc)
                )

    # ======================================
    # 29. GENERAR REPORTES
    # ======================================

    def save(self):

        output = (
            self.base.parent
            / "Data Procesada"
        )

        output.mkdir(
            parents=True,
            exist_ok=True
        )

        statuses = Counter(
            i["estado"]
            for i in self.checks
        )

        state = (
            "BLOQUEADO"
            if statuses["ERROR"]
            else "APTO_PARA_PRUEBAS_MANUALES"
        )

        report = {

            "etapa": "23.1",

            "generado_utc":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "estado": state,

            "advertencia": (
                "APTO_PARA_PRUEBAS_MANUALES "
                "no equivale a listo "
                "para produccion"
            ),

            "metricas": self.metrics,

            "resumen": dict(statuses),

            "comprobaciones": self.checks,

            "pruebas_manuales_pendientes": [

                (
                    "Abrir las cinco vistas "
                    "desde 22_3_index.html "
                    "sin errores de consola"
                ),

                (
                    "Cambiar entre vistas 20 veces "
                    "y verificar que no hay "
                    "congelamientos"
                ),

                (
                    "Seleccionar municipio y celda; "
                    "verificar que se restauran "
                    "correctamente"
                ),

                (
                    "Reproducir ambas papiroflexias "
                    "y medir FPS y uso de memoria "
                    "en el navegador"
                ),

                (
                    "Probar movil, teclado "
                    "y lector de pantalla"
                ),

                (
                    "Probar cartografia con y sin "
                    "acceso a Internet; "
                    "revisar atribucion/licencia"
                ),

                (
                    "Revisar fuentes, limitaciones, "
                    "permisos, privacidad "
                    "y textos cientificos"
                ),

                (
                    "Verificar HTTPS, cabeceras "
                    "de seguridad, cache "
                    "y disponibilidad en el hosting"
                )
            ]
        }

        json_path = (
            output
            / "23_1_auditoria_despliegue.json"
        )

        md_path = (
            output
            / "23_1_auditoria_despliegue.md"
        )

        json_path.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        # ==================================
        # 30. REPORTE MARKDOWN
        # ==================================

        lines = [

            "# Hotspot | Auditoría de integración 23.1",

            "",

            f"**Estado:** {state}",

            (
                f"**Comprobaciones:** "
                f"{len(self.checks)} | "
                f"OK: {statuses['OK']} | "
                f"Errores: {statuses['ERROR']} | "
                f"Avisos: {statuses['AVISO']}"
            ),

            "",

            "## Resultado por comprobación",

            ""
        ]

        lines += [

            (
                f"- **{i['estado']}** "
                f"— {i['area']}: "
                f"{i['detalle']}"
            )

            for i in self.checks
        ]

        lines += [

            "",

            "## Pruebas manuales aún pendientes",

            ""
        ]

        lines += [

            f"- [ ] {v}"

            for v in report[
                "pruebas_manuales_pendientes"
            ]
        ]

        lines += [

            "",

            (
                "> Esta auditoría no valida "
                "FPS reales, causalidad "
                "ni riesgo vial."
            ),

            ""
        ]

        md_path.write_text(
            "\n".join(lines),
            encoding="utf-8"
        )

        # ==================================
        # 31. RESUMEN EN TERMINAL
        # ==================================

        print(
            "\n=== ETAPA 23.1 | RESULTADO ==="
        )

        print(
            f"Estado: {state}"
        )

        print(
            f"OK: {statuses['OK']} | "
            f"Errores: {statuses['ERROR']} | "
            f"Avisos: {statuses['AVISO']}"
        )

        print(
            f"Reporte: {json_path}"
        )

        print(
            f"Checklist: {md_path}"
        )

        return statuses["ERROR"] == 0


# ==========================================
# 32. EJECUCION PRINCIPAL
# ==========================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Auditoria integrada Hotspot 23.1"
        )
    )

    parser.add_argument(
        "--http",
        metavar="URL",
        help=(
            "Verificar archivos desde "
            "un servidor HTTP local"
        )
    )

    args = parser.parse_args()

    auditor = Auditor(
        Path(__file__).resolve().parent
    )

    auditor.files()
    auditor.municipal()
    auditor.urbano()

    if args.http:

        auditor.http(
            args.http
        )

    else:

        auditor.info(
            "Prueba HTTP",
            (
                "No ejecutada; usar "
                "--http http://localhost:8000 "
                "con servidor encendido"
            )
        )

    return (
        0
        if auditor.save()
        else 1
    )


if __name__ == "__main__":

    sys.exit(
        main()
    )
