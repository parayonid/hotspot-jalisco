
"""HOTSPOT | Etapa 21.3: análisis espectral de siniestros.

Ejecutar desde hotspot-mvp:
    ..\\.venv\\Scripts\\python.exe .\\21_analisis_espectral_siniestros.py

ENTRADA:
    datos/21_grafo_siniestros_2025.json

SALIDAS:
    datos/21_embedding_siniestros_2025.json
    ../Data Procesada/21_resultados_espectrales_2025.json
    ../Data Procesada/21_autovalores_siniestros_2025.csv
    ../Data Procesada/21_embedding_siniestros_2025.csv

El embedding se calcula en la componente mayor.
El grafo completo se conserva para visualizacion.
"""

from collections import deque
from pathlib import Path
import csv
import json
import math

import numpy as np

from scipy.sparse import (
    coo_matrix,
    csgraph
)

from scipy.sparse.linalg import eigsh


# ==========================================
# 1. CONFIGURACION
# ==========================================

BASE = Path(__file__).resolve().parent

DATOS = BASE / "datos"

REPORTES = BASE.parent / "Data Procesada"

PERMUTACIONES = 1999

SEMILLA = 20251112


# ==========================================
# 2. EXPORTAR RESULTADOS
# ==========================================

def guardar_json(ruta, objeto):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            objeto,
            f,
            ensure_ascii=False,
            allow_nan=False,
            indent=2
        )

    print(
        f"Generado: {ruta.name} "
        f"({ruta.stat().st_size:,} bytes)"
    )


def guardar_csv(ruta, filas, columnas):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=columnas
        )

        writer.writeheader()
        writer.writerows(filas)

    print(
        f"Generado: {ruta.name} "
        f"({len(filas):,} filas)"
    )


# ==========================================
# 3. IDENTIFICAR COMPONENTES CONEXAS
# ==========================================

def componentes_conexas(vecinos):

    pendientes = set(vecinos)

    grupos = []

    while pendientes:

        inicial = min(pendientes)

        cola = deque([inicial])

        pendientes.remove(inicial)

        grupo = []

        while cola:

            actual = cola.popleft()

            grupo.append(actual)

            nuevos = sorted(
                vecinos[actual] & pendientes
            )

            for v in nuevos:

                pendientes.remove(v)
                cola.append(v)

        grupos.append(
            sorted(grupo)
        )

    grupos.sort(
        key=lambda g: (
            -len(g),
            g[0]
        )
    )

    return grupos


# ==========================================
# 4. ENERGIA DE UNA SENAL SOBRE EL GRAFO
# ==========================================

def energia_senal(
    x,
    origen,
    destino,
    pesos
):

    """
    Energia de Dirichlet:

    E(x) = x^T L x

    = suma sobre las aristas no dirigidas
      de w_ij * (x_i - x_j)^2
    """

    return float(
        np.sum(
            pesos * np.square(
                x[origen] - x[destino]
            )
        )
    )


# ==========================================
# 5. EJECUCION PRINCIPAL
# ==========================================

def main():

    entrada = (
        DATOS /
        "21_grafo_siniestros_2025.json"
    )

    if not entrada.is_file():

        raise FileNotFoundError(
            f"Falta {entrada}. "
            "Ejecuta primero la Etapa 21.2."
        )

    with entrada.open(
        encoding="utf-8-sig"
    ) as f:

        grafo = json.load(f)

    nodos = grafo["nodos"]

    aristas = grafo["aristas"]

    resumen_entrada = grafo.get(
        "resumen", {}
    )

    ids = [
        str(n["id"])
        for n in nodos
    ]

    indice_global = {
        v: i
        for i, v in enumerate(ids)
    }

    # ======================================
    # 6. VALIDAR EL GRAFO
    # ======================================

    if (
        (len(nodos), len(aristas))
        != (447, 1034)
        or len(indice_global) != len(nodos)
    ):

        raise ValueError(
            "Se esperaban 447 vertices unicos "
            "y 1,034 aristas de 2025."
        )

    vecinos = {
        v: set()
        for v in ids
    }

    conexiones = set()

    for a in aristas:

        u = str(a["source"])
        v = str(a["target"])

        if (
            u not in vecinos
            or v not in vecinos
            or u == v
        ):

            raise ValueError(
                f"Arista invalida: {u}-{v}"
            )

        par = tuple(
            sorted((u, v))
        )

        if par in conexiones:

            raise ValueError(
                f"Arista duplicada: {par}"
            )

        conexiones.add(par)

        vecinos[u].add(v)
        vecinos[v].add(u)

        # Verificar vecindad por lado
        # o diagonal.

        dx = abs(
            int(
                nodos[indice_global[u]][
                    "indice_x"
                ]
            )
            -
            int(
                nodos[indice_global[v]][
                    "indice_x"
                ]
            )
        )

        dy = abs(
            int(
                nodos[indice_global[u]][
                    "indice_y"
                ]
            )
            -
            int(
                nodos[indice_global[v]][
                    "indice_y"
                ]
            )
        )

        if not (
            dx <= 1
            and dy <= 1
            and dx + dy >= 1
        ):

            raise ValueError(
                f"Conexion no vecina: {u}-{v}"
            )

        esperado = (
            1 / math.hypot(dx, dy)
        )

        if not math.isclose(
            float(a["peso"]),
            esperado,
            abs_tol=2e-6
        ):

            raise ValueError(
                f"Peso incorrecto: {u}-{v}"
            )

    # ======================================
    # 7. RECUPERAR COMPONENTE MAYOR
    # ======================================

    grupos = componentes_conexas(
        vecinos
    )

    mayor = grupos[0]

    conjunto_mayor = set(mayor)

    grupo_por_nodo = {

        v: i + 1

        for i, grupo in enumerate(grupos)

        for v in grupo
    }

    if (
        len(grupos) != 46
        or len(mayor) != 347
    ):

        raise ValueError(
            "Se esperaban 46 componentes "
            "y una componente mayor de 347 nodos."
        )

    if len(grupos) != int(
        resumen_entrada.get(
            "componentes", -1
        )
    ):

        raise ValueError(
            "Las componentes no coinciden "
            "con la Etapa 21.2."
        )

    # ======================================
    # 8. PREPARAR NODOS DE LA COMPONENTE
    # ======================================

    nodos_mayor = [

        nodo
        for nodo in nodos

        if str(nodo["id"])
        in conjunto_mayor
    ]

    ids_mayor = [

        str(n["id"])
        for n in nodos_mayor
    ]

    idx = {

        v: i
        for i, v in enumerate(ids_mayor)
    }

    n = len(nodos_mayor)

    edges_mayor = [

        a
        for a in aristas

        if (
            a["source"] in conjunto_mayor
            and a["target"] in conjunto_mayor
        )
    ]

    # ======================================
    # 9. EXTRAER ARISTAS PONDERADAS
    # ======================================

    ia = np.array(

        [
            idx[a["source"]]
            for a in edges_mayor
        ],

        dtype=int
    )

    ib = np.array(

        [
            idx[a["target"]]
            for a in edges_mayor
        ],

        dtype=int
    )

    w = np.array(

        [
            float(a["peso"])
            for a in edges_mayor
        ],

        dtype=float
    )

    if (
        not np.all(np.isfinite(w))
        or np.any(w <= 0)
    ):

        raise ValueError(
            "Pesos invalidos."
        )

    # ======================================
    # 10. MATRIZ DE ADYACENCIA W
    # ======================================

    W = coo_matrix(

        (
            np.r_[w, w],

            (
                np.r_[ia, ib],
                np.r_[ib, ia]
            )
        ),

        shape=(n, n),

        dtype=float
    ).tocsr()

    # ======================================
    # 11. LAPLACIANO L = D - W
    # ======================================

    L = csgraph.laplacian(

        W,

        normed=False
    ).tocsr()

    # ======================================
    # 12. CALCULAR AUTOVECTORES
    # ======================================

    v0 = np.linspace(
        1.0,
        2.0,
        n,
        dtype=float
    )

    valores, vectores = eigsh(

        L,

        k=4,

        which="SM",

        tol=1e-9,

        maxiter=max(
            10000,
            30 * n
        ),

        v0=v0
    )

    orden = np.argsort(
        valores
    )

    valores = valores[orden]

    vectores = vectores[:, orden]

    # ======================================
    # 13. ORIENTACION DETERMINISTA
    # ======================================

    # El signo de un autovector
    # es matematicamente arbitrario.

    for j in range(4):

        k = int(
            np.argmax(
                np.abs(vectores[:, j])
            )
        )

        if vectores[k, j] < 0:

            vectores[:, j] *= -1

    # ======================================
    # 14. VALIDAR AUTOPARES
    # ======================================

    residuos = [

        float(
            np.linalg.norm(

                L @ vectores[:, j]

                -

                valores[j] * vectores[:, j]
            )
        )

        for j in range(4)
    ]

    if (
        abs(float(valores[0])) > 1e-6
        or float(valores[1]) <= 1e-8
        or max(residuos) > 1e-5
    ):

        raise RuntimeError(
            "La descomposicion espectral "
            "no supero los controles numericos."
        )

    # ======================================
    # 15. SENAL DE SINIESTRALIDAD
    # ======================================

    conteos = np.array(

        [
            int(nodo["conteo_2025"])
            for nodo in nodos_mayor
        ],

        dtype=int
    )

    if np.any(conteos <= 0):

        raise ValueError(
            "Hay celdas sin registros "
            "en la componente de 2025."
        )

    # Reducir influencia de conteos extremos.

    x = np.log1p(
        conteos.astype(float)
    )

    # ======================================
    # 16. ENERGIA ESPECTRAL
    # ======================================

    energia = energia_senal(
        x,
        ia,
        ib,
        w
    )

    energia_matricial = float(

        x @ (L @ x)
    )

    if not math.isclose(
        energia,
        energia_matricial,
        rel_tol=1e-9,
        abs_tol=1e-8
    ):

        raise RuntimeError(
            "La energia por aristas "
            "no coincide con x^T L x."
        )

    # ======================================
    # 17. PRUEBA DE PERMUTACIONES
    # ======================================

    rng = np.random.default_rng(
        SEMILLA
    )

    energias_aleatorias = np.empty(

        PERMUTACIONES,

        dtype=float
    )

    for p in range(PERMUTACIONES):

        permutada = rng.permutation(x)

        energias_aleatorias[p] = (
            energia_senal(
                permutada,
                ia,
                ib,
                w
            )
        )

    # Energia menor = mayor suavidad
    # relativa a estas permutaciones.

    p_suavidad = (

        1 + int(
            np.count_nonzero(
                energias_aleatorias <= energia
            )
        )

    ) / (PERMUTACIONES + 1)

    # Energia mayor = mayor contraste
    # relativo a estas permutaciones.

    p_contraste = (

        1 + int(
            np.count_nonzero(
                energias_aleatorias >= energia
            )
        )

    ) / (PERMUTACIONES + 1)

    # ======================================
    # 18. EMBEDDING ESPECTRAL
    # ======================================

    # Seleccionamos u2, u3, u4.

    embedding = vectores[:, 1:4]

    escala = 1.8 / max(
        1e-12,
        float(
            np.max(
                np.abs(embedding)
            )
        )
    )

    por_emb = {

        v: embedding[i]

        for i, v in enumerate(ids_mayor)
    }

    # ======================================
    # 19. POSICIONES GEOGRAFICAS VISUALES
    # ======================================

    # Utilizar el mismo marco geometrico
    # para los 447 nodos.

    xy = np.array(

        [
            nodo["centro_xy_m"]
            for nodo in nodos
        ],

        dtype=float
    )

    if not np.all(
        np.isfinite(xy)
    ):

        raise ValueError(
            "Coordenadas metricas invalidas."
        )

    centro_xy = np.mean(
        xy,
        axis=0
    )

    escala_geo = 4.0 / max(

        float(
            np.ptp(xy[:, 0])
        ),

        float(
            np.ptp(xy[:, 1])
        ),

        1
    )

    # ======================================
    # 20. EXPORTAR LOS 447 NODOS
    # ======================================

    nodos_exportados = []

    filas_csv = []

    for i, nodo in enumerate(nodos):

        clave = str(
            nodo["id"]
        )

        en_mayor = (
            clave in conjunto_mayor
        )

        geo_xyz = [

            float(
                (xy[i, 0] - centro_xy[0])
                * escala_geo
            ),

            0.04,

            float(
                (xy[i, 1] - centro_xy[1])
                * escala_geo
            )
        ]

        u = por_emb.get(
            clave
        )

        vector = (

            [float(v) for v in u]

            if u is not None

            else None
        )

        # La elevacion es exclusivamente
        # una transformacion visual.

        spec = (

            [
                float(
                    u[0] * escala
                ),

                float(
                    1.2 +
                    u[2] * escala * 0.6
                ),

                float(
                    u[1] * escala
                )
            ]

            if u is not None

            else None
        )

        item = {

            "id": clave,

            "centro_lonlat":
                nodo["centro_lonlat"],

            "geo_xyz": [
                round(v, 8)
                for v in geo_xyz
            ],

            "autovectores_u2_u3_u4": (

                [
                    round(v, 12)
                    for v in vector
                ]

                if vector else None
            ),

            "espectral_xyz": (

                [
                    round(v, 8)
                    for v in spec
                ]

                if spec else None
            ),

            "en_componente_mayor":
                en_mayor,

            "componente":
                grupo_por_nodo[clave],

            "conteo_2025":
                int(nodo["conteo_2025"]),

            "alta_concentracion_2025":
                bool(
                    nodo[
                        "alta_concentracion_2025"
                    ]
                ),

            "grado":
                int(nodo["grado"])
        }

        nodos_exportados.append(
            item
        )

        filas_csv.append({

            "id_celda": clave,

            "componente":
                grupo_por_nodo[clave],

            "en_componente_mayor":
                en_mayor,

            "conteo_2025":
                int(nodo["conteo_2025"]),

            "u2": (
                vector[0] if vector else ""
            ),

            "u3": (
                vector[1] if vector else ""
            ),

            "u4": (
                vector[2] if vector else ""
            )
        })

    # ======================================
    # 21. EXPORTAR TODAS LAS ARISTAS
    # ======================================

    aristas_exportadas = [

        {

            "source":
                str(a["source"]),

            "target":
                str(a["target"]),

            "peso":
                float(a["peso"]),

            "en_componente_mayor":
                a["source"] in conjunto_mayor
        }

        for a in aristas
    ]

    # ======================================
    # 22. COMPROBAR EVENTOS CONSERVADOS
    # ======================================

    total_eventos = sum(

        int(
            nodo["conteo_2025"]
        )

        for nodo in nodos
    )

    eventos_mayor = int(
        conteos.sum()
    )

    if total_eventos != 1337:

        raise ValueError(
            "Se esperaban 1,337 siniestros "
            "georreferenciados de 2025."
        )

    # ======================================
    # 23. RESUMEN DE AUTOVALORES
    # ======================================

    autovalores = [

        {

            "indice": i + 1,

            "autovalor":
                float(valores[i]),

            "residuo_norma_Lu_menos_lambda_u":
                residuos[i]
        }

        for i in range(4)
    ]

    # ======================================
    # 24. REPORTE ESTADISTICO
    # ======================================

    reporte = {

        "descripcion": (
            "Analisis exploratorio "
            "de vecindad de celdas activas "
            "de 2025."
        ),

        "grafo_total": {

            "nodos":
                len(nodos),

            "aristas":
                len(aristas),

            "componentes":
                len(grupos),

            "aislados": sum(
                len(g) == 1
                for g in grupos
            ),

            "eventos_2025":
                total_eventos
        },

        "componente_mayor": {

            "nodos": n,

            "aristas":
                len(edges_mayor),

            "eventos_2025":
                eventos_mayor,

            "fraccion_eventos_total":
                eventos_mayor / total_eventos,

            "autovalores":
                autovalores,

            "lambda2":
                float(valores[1]),

            "max_residuo_autopar":
                max(residuos)
        },

        "energia_senal_log1p_conteos": {

            "observada":
                energia,

            "comprobacion_xLx":
                energia_matricial,

            "permutaciones":
                PERMUTACIONES,

            "semilla":
                SEMILLA,

            "media_permutaciones": float(
                np.mean(
                    energias_aleatorias
                )
            ),

            "desviacion_permutaciones": float(
                np.std(
                    energias_aleatorias,
                    ddof=1
                )
            ),

            "percentil_05": float(
                np.quantile(
                    energias_aleatorias,
                    0.05
                )
            ),

            "percentil_95": float(
                np.quantile(
                    energias_aleatorias,
                    0.95
                )
            ),

            "p_suavidad_unilateral":
                p_suavidad,

            "p_contraste_unilateral":
                p_contraste
        },

        "advertencias": [

            "El embedding se calculo solo "
            "en la componente mayor.",

            "Las otras celdas conservan "
            "posiciones geograficas, pero "
            "no coordenadas espectrales.",

            "Las aristas expresan vecindad "
            "de celdas, no conexiones viales "
            "ni causalidad entre siniestros.",

            "Las permutaciones son una "
            "referencia condicional al grafo. "
            "No corrigen sesgos de cobertura "
            "ni exposicion vial.",

            "Los conteos no representan "
            "tasas de riesgo.",

            "Los signos de los autovectores "
            "son matematicamente arbitrarios."
        ]
    }

    # ======================================
    # 25. JSON PARA EL FRONTEND THREE.JS
    # ======================================

    exportacion = {

        "metadatos": {

            "anio": 2025,

            "nodos":
                len(nodos),

            "aristas":
                len(aristas),

            "componentes":
                len(grupos),

            "nodos_con_embedding": n,

            "nodos_sin_embedding":
                len(nodos) - n,

            "aristas_con_embedding":
                len(edges_mayor),

            "grafo": (
                "Vecindad reina sobre "
                "celdas de 1 km2"
            ),

            "metodo_espectral": (
                "L = D - W; coordenadas "
                "u2, u3, u4 de componente mayor"
            ),

            "interpretacion": (
                "Las posiciones y alturas "
                "espectrales no son riesgo vial."
            )
        },

        "nodos":
            nodos_exportados,

        "aristas":
            aristas_exportadas
    }

    # ======================================
    # 26. GUARDAR ARCHIVOS
    # ======================================

    guardar_json(

        DATOS /
        "21_embedding_siniestros_2025.json",

        exportacion
    )

    guardar_json(

        REPORTES /
        "21_resultados_espectrales_2025.json",

        reporte
    )

    guardar_csv(

        REPORTES /
        "21_autovalores_siniestros_2025.csv",

        autovalores,

        [
            "indice",
            "autovalor",
            "residuo_norma_Lu_menos_lambda_u"
        ]
    )

    guardar_csv(

        REPORTES /
        "21_embedding_siniestros_2025.csv",

        filas_csv,

        [
            "id_celda",
            "componente",
            "en_componente_mayor",
            "conteo_2025",
            "u2",
            "u3",
            "u4"
        ]
    )

    # ======================================
    # 27. RESULTADOS EN TERMINAL
    # ======================================

    print(
        "\n=== ETAPA 21.3 | "
        "ANALISIS ESPECTRAL SINIESTROS ==="
    )

    print(
        f"Grafo 2025: {len(nodos)} nodos, "
        f"{len(aristas)} aristas, "
        f"{len(grupos)} componentes"
    )

    print(
        f"Componente mayor: {n} nodos, "
        f"{len(edges_mayor)} aristas, "
        f"{eventos_mayor} eventos"
    )

    for j in range(4):

        print(
            f"lambda{j + 1} = "
            f"{valores[j]:.9f}; "
            f"residuo = {residuos[j]:.2e}"
        )

    print(
        "Energia log1p observada = "
        f"{energia:.6f}"
    )

    print(
        "Media energia permutada = "
        f"{np.mean(energias_aleatorias):.6f}"
    )

    print(
        f"p suavidad = {p_suavidad:.4f}; "
        f"p contraste = {p_contraste:.4f}"
    )

    print(
        f"Registros conservados: "
        f"{total_eventos}; "
        f"celdas sin embedding: "
        f"{len(nodos) - n}"
    )

    print(
        "Nota: se analizan concentraciones "
        "de registros, NO probabilidades "
        "de riesgo."
    )


if __name__ == "__main__":
    main()
