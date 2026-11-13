
"""
HOTSPOT | Etapa 14: primera papiroflexia interactiva.

Entradas:
    Data Procesada/13_embedding_espectral.csv
    Data Procesada/08_matriz_adyacencia.csv
    Data Cruda/**/limite_municipal_jalisco_iieg.gpkg

Salidas:
    Data Procesada/14_papiroflexia_interactiva.html
    Data Procesada/14_energia_denue_permutaciones.csv
    Data Procesada/14_resumen_energia_denue.csv

El movimiento es una interpolacion visual de coordenadas:
no es una deformacion fisica ni una estimacion de riesgo.
"""

# ============================================
# 1. IMPORTAR BIBLIOTECAS
# ============================================

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from shapely import wkb


# ============================================
# 2. CONFIGURACION GENERAL
# ============================================

RAIZ = Path(__file__).resolve().parent.parent

PROCESADA = RAIZ / "Data Procesada"
CRUDA = RAIZ / "Data Cruda"

N_PERMUTACIONES = 1999
SEMILLA = 20261111


def csv(nombre, **opciones):

    ruta = PROCESADA / nombre

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe: {ruta}"
        )

    return pd.read_csv(
        ruta,
        encoding="utf-8-sig",
        **opciones
    )


# ============================================
# 3. CARGAR LOS MUNICIPIOS
# ============================================

nodos = csv(
    "13_embedding_espectral.csv",
    dtype={"cvegeo": "string"}
)

nodos["cvegeo"] = (
    nodos["cvegeo"].str.strip()
)

nodos = (
    nodos.sort_values("cvegeo")
    .reset_index(drop=True)
)

claves = nodos["cvegeo"].tolist()

if len(claves) != 125 or len(set(claves)) != 125:
    raise ValueError(
        "Se esperan 125 municipios con claves unicas."
    )


# ============================================
# 4. RECUPERAR LA ADYACENCIA REAL
# ============================================

A_df = csv(
    "08_matriz_adyacencia.csv",
    index_col=0
)

A_df.index = A_df.index.map(str)
A_df.columns = A_df.columns.map(str)

if (
    set(claves) != set(A_df.index)
    or set(claves) != set(A_df.columns)
):
    raise ValueError(
        "La adyacencia y el embedding "
        "no contienen las mismas claves."
    )

# Ordenar filas y columnas exactamente
# como nuestros municipios.

A = A_df.loc[
    claves, claves
].to_numpy(dtype=float)

# Verificar simetria, valores binarios
# y ausencia de conexiones consigo mismo.

if (
    not np.isfinite(A).all()
    or not np.allclose(A, A.T)
    or not np.isin(A, [0, 1]).all()
    or not np.allclose(np.diag(A), 0)
):
    raise ValueError(
        "Matriz de adyacencia invalida."
    )

# Recuperar cada arista una sola vez.
i_aristas, j_aristas = np.where(
    np.triu(A, k=1) == 1
)


# ============================================
# 5. LEER GEOMETRIAS DEL GEOPACKAGE
# ============================================

archivos = list(
    CRUDA.rglob(
        "limite_municipal_jalisco_iieg.gpkg"
    )
)

if len(archivos) != 1:
    raise FileNotFoundError(
        "Se necesita exactamente un "
        "GeoPackage municipal."
    )


def geometria_geopackage(blob):

    if blob is None or bytes(blob[:2]) != b"GP":
        raise ValueError(
            "Geometria GeoPackage invalida."
        )

    # La cabecera GeoPackage indica
    # el tipo de envolvente espacial.

    tipo_envolvente = (
        blob[3] >> 1
    ) & 7

    largos = {
        0: 0,
        1: 32,
        2: 48,
        3: 48,
        4: 64
    }

    if tipo_envolvente not in largos:
        raise ValueError(
            "Envolvente GeoPackage desconocida."
        )

    # Descartar cabecera y recuperar WKB.
    inicio = 8 + largos[tipo_envolvente]

    return wkb.loads(
        bytes(blob[inicio:])
    )


# ============================================
# 6. OBTENER UN PUNTO POR MUNICIPIO
# ============================================

with sqlite3.connect(archivos[0]) as conexion:

    registros = conexion.execute(
        """
        SELECT clave_geo, geom
        FROM limite_municipal
        """
    ).fetchall()

puntos = {}

for clave, blob in registros:

    geom = geometria_geopackage(blob)

    if geom.is_empty or not geom.is_valid:
        raise ValueError(
            f"Geometria invalida en municipio {clave}."
        )

    # Punto representativo que pertenece
    # al interior del poligono municipal.
    punto = geom.representative_point()

    puntos[str(clave).strip()] = (
        punto.x,
        punto.y
    )

if set(puntos) != set(claves):
    raise ValueError(
        "Faltan municipios al leer los poligonos."
    )


# ============================================
# 7. NORMALIZAR POSICIONES GEOGRAFICAS
# ============================================

geografia_xy = np.array(
    [puntos[c] for c in claves],
    dtype=float
)

# Centrar los puntos.
geografia_xy -= geografia_xy.mean(axis=0)

# Escalar para que entren en la escena.
escala_geo = max(
    float(
        np.ptp(
            geografia_xy,
            axis=0
        ).max()
    ) / 2,
    1e-12
)

geografia = np.column_stack((
    geografia_xy / escala_geo,
    np.zeros(len(claves))
))


# ============================================
# 8. NORMALIZAR POSICIONES ESPECTRALES
# ============================================

espectral = nodos[
    [
        "espectral_x",
        "espectral_y",
        "espectral_z"
    ]
].to_numpy(float)

if not np.isfinite(espectral).all():
    raise ValueError(
        "Coordenadas espectrales no finitas."
    )

# Centrar el embedding.
espectral -= espectral.mean(axis=0)

# Llevarlo a una escala visual comparable.
escala_espectral = max(
    float(np.abs(espectral).max()),
    1e-12
)

espectral /= escala_espectral


# ============================================
# 9. CONSTRUIR LA SENAL DENUE
# ============================================

negocios = pd.to_numeric(
    nodos[
        "establecimientos_denue_mayo_2025"
    ],
    errors="coerce"
).to_numpy(float)

area = pd.to_numeric(
    nodos["area_km2"],
    errors="coerce"
).to_numpy(float)

if (
    not np.isfinite(negocios).all()
    or not np.isfinite(area).all()
    or (negocios < 0).any()
    or (area <= 0).any()
):
    raise ValueError(
        "DENUE o superficies invalidas."
    )

# Establecimientos por km2,
# transformados mediante log(1 + x).

senal = np.log1p(
    negocios / area
)


# ============================================
# 10. CALCULAR ENERGIA DEL GRAFO
# ============================================

def energia(x):

    # Cada arista no dirigida cuenta
    # una sola vez.

    diferencias = (
        x[i_aristas] - x[j_aristas]
    )

    return float(
        np.sum(diferencias ** 2)
    )


energia_obs = energia(senal)


# ============================================
# 11. VALIDAR CONTRA LA ETAPA 13
# ============================================

resumen_13 = csv(
    "13_resumen_espectral.csv"
)

energia_anterior = float(
    resumen_13[
        "energia_denue"
    ].iloc[0]
)

if not np.isclose(
    energia_obs,
    energia_anterior,
    rtol=1e-8,
    atol=1e-7
):
    raise ValueError(
        "La energia no coincide "
        "con la Etapa 13."
    )


# ============================================
# 12. PRUEBA DE PERMUTACIONES
# ============================================

generador = np.random.default_rng(
    SEMILLA
)

energias_aleatorias = np.array([
    energia(
        generador.permutation(senal)
    )
    for _ in range(N_PERMUTACIONES)
])

# Contraste de suavidad espacial:
# energia inusualmente pequena.

p_suavidad = (
    1 + int(
        np.count_nonzero(
            energias_aleatorias <= energia_obs
        )
    )
) / (N_PERMUTACIONES + 1)

# Contraste de contrastes espaciales:
# energia inusualmente grande.

p_contraste = (
    1 + int(
        np.count_nonzero(
            energias_aleatorias >= energia_obs
        )
    )
) / (N_PERMUTACIONES + 1)


# ============================================
# 13. GUARDAR PRUEBA ESTADISTICA
# ============================================

pd.DataFrame({
    "permutacion": np.arange(
        1,
        N_PERMUTACIONES + 1
    ),
    "energia_aleatoria": energias_aleatorias
}).to_csv(
    PROCESADA
    / "14_energia_denue_permutaciones.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame([{
    "municipios": len(claves),
    "aristas": len(i_aristas),
    "energia_observada": energia_obs,
    "media_energia_aleatoria": float(
        energias_aleatorias.mean()
    ),
    "p_suavidad_unilateral": p_suavidad,
    "p_contraste_unilateral": p_contraste,
    "permutaciones": N_PERMUTACIONES,
    "semilla": SEMILLA
}]).to_csv(
    PROCESADA
    / "14_resumen_energia_denue.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================
# 14. CREAR INFORMACION DE CADA NODO
# ============================================

texto_nodos = []

for idx, fila in nodos.iterrows():

    atus = fila.get(
        "registros_atus_2025"
    )

    atus_txt = (
        "Sin dato"
        if pd.isna(atus)
        else f"{int(float(atus)):,}"
    )

    texto_nodos.append(
        f"<b>{fila['municipio_cartografia']}</b>"
        f"<br>Clave: {fila['cvegeo']}"
        f"<br>Region IIEG: {fila['region_iieg']}"
        f"<br>DENUE: {int(negocios[idx]):,} establecimientos"
        f"<br>Densidad DENUE: "
        f"{negocios[idx] / area[idx]:.2f} est./km²"
        f"<br>ATUS 2025: {atus_txt}"
    )


# ============================================
# 15. DIBUJAR LAS CONEXIONES DEL GRAFO
# ============================================

def dibujar_aristas(pos):

    xs, ys, zs = [], [], []

    for i, j in zip(i_aristas, j_aristas):

        xs.extend([
            pos[i, 0],
            pos[j, 0],
            None
        ])

        ys.extend([
            pos[i, 1],
            pos[j, 1],
            None
        ])

        zs.extend([
            pos[i, 2],
            pos[j, 2],
            None
        ])

    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(
            color="rgba(143,153,181,0.34)",
            width=2
        ),
        hoverinfo="skip",
        showlegend=False,
        name="Fronteras compartidas"
    )


# ============================================
# 16. DIBUJAR LOS MUNICIPIOS
# ============================================

def dibujar_nodos(pos):

    return go.Scatter3d(
        x=pos[:, 0],
        y=pos[:, 1],
        z=pos[:, 2],
        mode="markers",
        marker=dict(
            size=5,
            color=senal,
            colorscale="Viridis",
            cmin=float(senal.min()),
            cmax=float(senal.max()),
            opacity=0.96,
            colorbar=dict(
                title="log(1+est./km²)",
                thickness=14
            )
        ),
        text=texto_nodos,
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
        name="Municipios"
    )


# ============================================
# 17. INTERPOLAR LAS POSICIONES
# ============================================

def interpolar(fraccion):

    return (
        (1 - fraccion) * geografia
        + fraccion * espectral
    )


# ============================================
# 18. GENERAR FOTOGRAMAS
# ============================================

N_PASOS = 20
fotogramas = []

for paso in range(N_PASOS + 1):

    p = interpolar(
        paso / N_PASOS
    )

    fotogramas.append(
        go.Frame(
            data=[
                dibujar_aristas(p),
                dibujar_nodos(p)
            ],
            name=str(paso),
            traces=[0, 1]
        )
    )


# ============================================
# 19. CONSTRUIR LA FIGURA INTERACTIVA
# ============================================

figura = go.Figure(
    data=[
        dibujar_aristas(geografia),
        dibujar_nodos(geografia)
    ],
    frames=fotogramas
)

pasos_slider = [
    dict(
        method="animate",
        label=f"{paso / N_PASOS:.2f}",
        args=[
            [str(paso)],
            {
                "mode": "immediate",
                "frame": {
                    "duration": 0,
                    "redraw": True
                },
                "transition": {
                    "duration": 0
                }
            }
        ]
    )
    for paso in range(N_PASOS + 1)
]


# ============================================
# 20. CONFIGURAR APARIENCIA Y CONTROLES
# ============================================

figura.update_layout(
    title=(
        "HOTSPOT | Papiroflexia espectral de Jalisco"
        "<br><sup>0 = geometria municipal normalizada"
        " · 1 = autovectores u₂, u₃ y u₄"
        " · Color = densidad de establecimientos DENUE</sup>"
    ),
    template="plotly_dark",
    paper_bgcolor="#0b1020",
    height=750,
    margin=dict(
        l=0,
        r=0,
        b=40,
        t=100
    ),
    scene=dict(
        xaxis=dict(
            visible=False,
            range=[-1.35, 1.35]
        ),
        yaxis=dict(
            visible=False,
            range=[-1.35, 1.35]
        ),
        zaxis=dict(
            visible=False,
            range=[-1.35, 1.35]
        ),
        aspectmode="cube",
        camera=dict(
            eye=dict(
                x=0,
                y=0,
                z=2.2
            )
        ),
        bgcolor="#0b1020"
    ),
    sliders=[
        dict(
            active=0,
            steps=pasos_slider,
            x=0.14,
            y=0.02,
            len=0.77,
            currentvalue=dict(
                prefix="Transicion: "
            ),
            pad=dict(t=20)
        )
    ],
    updatemenus=[
        dict(
            type="buttons",
            showactive=False,
            x=0.015,
            y=0.025,
            buttons=[
                dict(
                    label="▶ Animar",
                    method="animate",
                    args=[
                        None,
                        {
                            "fromcurrent": True,
                            "frame": {
                                "duration": 120,
                                "redraw": True
                            },
                            "transition": {
                                "duration": 0
                            }
                        }
                    ]
                ),
                dict(
                    label="⏸ Pausar",
                    method="animate",
                    args=[
                        [None],
                        {
                            "mode": "immediate",
                            "frame": {
                                "duration": 0,
                                "redraw": False
                            },
                            "transition": {
                                "duration": 0
                            }
                        }
                    ]
                )
            ]
        )
    ],
    annotations=[
        dict(
            text=(
                "Prototipo visual: las alturas espectrales "
                "no son riesgo y DENUE no mide delitos."
            ),
            x=0.5,
            y=-0.08,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                size=12,
                color="#aab4d0"
            )
        )
    ]
)


# ============================================
# 21. EXPORTAR HTML INTERACTIVO
# ============================================

salida_html = (
    PROCESADA
    / "14_papiroflexia_interactiva.html"
)

figura.write_html(
    salida_html,
    include_plotlyjs=True,
    full_html=True,
    auto_play=False
)


# ============================================
# 22. MOSTRAR RESULTADOS
# ============================================

print(
    "\n=== ETAPA 14: "
    "PAPIROFLEXIA INTERACTIVA ==="
)

print(
    "Municipios:",
    len(claves)
)

print(
    "Aristas:",
    len(i_aristas)
)

print(
    "Energia observada DENUE:",
    round(energia_obs, 6)
)

print(
    "Media energia aleatoria:",
    round(
        float(energias_aleatorias.mean()),
        6
    )
)

print(
    "p suavidad espacial:",
    round(p_suavidad, 6)
)

print(
    "p contraste espacial:",
    round(p_contraste, 6)
)

print(
    "Visualizacion:",
    salida_html
)

print(
    "AVISO: la transicion interpola "
    "coordenadas, no riesgo ni datos fisicos."
)
