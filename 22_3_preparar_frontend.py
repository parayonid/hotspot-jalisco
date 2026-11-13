
"""HOTSPOT - Etapa 22.3
Consolidacion inicial del frontend.

Ejecutar:
    ..\\.venv\\Scripts\\python.exe .\\22_3_preparar_frontend.py

Genera:
    22_3_index.html
    app/22_3.css
    app/22_3.js

Reporte:
    ../Data Procesada/22_3_validacion_integracion.json

No modifica los visores originales.
"""

from pathlib import Path
from textwrap import dedent
import json


# ==========================================
# 1. CONFIGURACION
# ==========================================

BASE = Path(__file__).resolve().parent

DATOS = BASE / "datos"

REPORTES = BASE.parent / "Data Procesada"


REQUERIDOS = [
    "22_visor_municipal.html",
    "22_2_visor_urbano.html",
    "22_puente.js",
    "18_panel_cientifico.js",
    "19_papiroflexia_three.js",
    "22_2_red_espectral_three.js",
    "22_2_contexto_urbano.js",
    "22_2_estabilidad.js",
    "datos/21_embedding_siniestros_2025.json",
    "datos/21_estabilidad_zonas_2025.geojson",
    "datos/22_2_contexto_urbano.json",
]


# ==========================================
# 2. PLANTILLA HTML
# ==========================================

HTML = dedent("""\
<!doctype html>
<html lang="es">

<head>
  <meta charset="utf-8">

  <meta
    name="viewport"
    content="width=device-width,initial-scale=1"
  >

  <meta
    name="description"
    content="Hotspot: observatorio territorial de Jalisco"
  >

  <title>HOTSPOT · Observatorio</title>

  <link
    rel="stylesheet"
    href="./app/22_3.css"
  >

  <script
    src="./app/22_3.js"
    defer
  ></script>
</head>

<body>

  <div class="shell">

    <header class="topbar">

      <div class="brand">
        <strong>HOTSPOT<span>.</span></strong>
        <small>OBSERVATORIO TERRITORIAL</small>
      </div>

      <nav
        class="tabs"
        aria-label="Navegación principal"
      >

        <button
          type="button"
          data-mode="territorio"
        >
          Territorio
        </button>

        <button
          type="button"
          data-mode="red"
        >
          Red urbana
        </button>

        <button
          type="button"
          data-mode="municipal3d"
        >
          Grafo municipal 3D
        </button>

        <button
          type="button"
          data-mode="urbano3d"
        >
          Grafo de siniestros 3D
        </button>

        <button
          type="button"
          data-mode="ciencia"
        >
          Panel científico
        </button>

      </nav>

      <div
        class="connection"
        id="appStatus"
        role="status"
        aria-live="polite"
      >
        Iniciando...
      </div>

    </header>

    <main class="workspace">

      <iframe
        id="module"
        title="Vista de Hotspot"
        loading="eager"
      ></iframe>

      <div
        class="loading"
        id="loading"
        role="status"
      >

        <div class="loading-card">

          <div
            class="loading-icon"
            aria-hidden="true"
          >
            ◈
          </div>

          <strong id="loadingTitle">
            Preparando módulo...
          </strong>

          <p id="loadingDetail">
            Cargando recursos locales
          </p>

          <button
            id="retry"
            type="button"
            hidden
          >
            Reintentar
          </button>

        </div>
      </div>

    </main>

    <footer class="footer">

      <span>
        ATUS · DENUE · Siniestralimap ·
        Seguridad regional
      </span>

      <span>
        Conteos observados ≠ riesgo vial ·
        Cobertura y ubicaciones limitadas
      </span>

    </footer>

  </div>

</body>
</html>
""")


# ==========================================
# 3. PLANTILLA CSS
# ==========================================

CSS = dedent("""\
:root {
  color-scheme: dark;
  font-family: system-ui, sans-serif;
  background: #0b1020;
  color: #edf0fb;
}

* {
  box-sizing: border-box;
}

html, body {
  height: 100%;
  margin: 0;
}

.shell {
  height: 100dvh;
  min-height: 450px;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 76px;
  padding: 11px 20px;
  background: #141c30;
  border-bottom: 1px solid #364366;
}

.brand {
  flex-shrink: 0;
  line-height: 1.15;
}

.brand strong {
  font-size: 23px;
  letter-spacing: .11em;
}

.brand strong span {
  color: #ae91ff;
}

.brand small {
  display: block;
  margin-top: 4px;
  color: #9caccc;
  font-size: 9px;
  letter-spacing: .1em;
}

.tabs {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  flex-wrap: wrap;
  gap: 5px;
}

.tabs button {
  font: 600 12px system-ui;
  padding: 10px 11px;
  border: 1px solid transparent;
  color: #bcc9df;
  background: transparent;
  border-radius: 9px;
  cursor: pointer;
}

.tabs button:hover,
.tabs button:focus-visible {
  background: #293550;
  color: white;
  outline-color: #aa8bff;
}

.tabs button[aria-current="page"] {
  background: #39285f;
  border-color: #9270d1;
  color: white;
}

.connection {
  min-width: 120px;
  max-width: 170px;
  font-size: 11px;
  color: #acbdd6;
  text-align: right;
}

.workspace {
  position: relative;
  flex: 1;
  min-height: 0;
}

#module {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #0b1020;
}

.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: #0b1020f5;
  z-index: 3;
  padding: 20px;
}

.loading[hidden],
#retry[hidden] {
  display: none;
}

.loading-card {
  text-align: center;
  border-radius: 16px;
  background: #18233a;
  border: 1px solid #354765;
  padding: 25px;
  max-width: 460px;
}

.loading-icon {
  color: #ae91ff;
  font-size: 40px;
}

.loading p {
  color: #b7c4d8;
  font-size: 13px;
  line-height: 1.5;
}

#retry {
  margin-top: 8px;
  background: #513a82;
  border: 1px solid #a38bd7;
  color: white;
  padding: 9px 17px;
  border-radius: 8px;
  cursor: pointer;
}

.footer {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px 20px;
  padding: 8px 17px;
  border-top: 1px solid #2c3955;
  font-size: 11px;
  color: #a2b0cb;
  background: #10172a;
}

@media (max-width: 1050px) {
  .topbar {
    flex-wrap: wrap;
    gap: 8px;
    padding: 10px 13px;
  }

  .tabs {
    flex: 1 1 100%;
    order: 3;
    justify-content: flex-start;
  }

  .tabs button {
    font-size: 11px;
    padding: 8px;
  }

  .connection {
    margin-left: auto;
  }
}

@media (max-width: 600px) {
  .brand strong {
    font-size: 20px;
  }

  .brand small {
    display: none;
  }

  .connection {
    font-size: 10px;
  }

  .footer {
    font-size: 10px;
  }
}
""")


# ==========================================
# 4. PLANTILLA JAVASCRIPT
# ==========================================

JS = dedent("""\
/*
 HOTSPOT 22.3
 Navegacion y estado de la aplicacion.
*/

(() => {
  "use strict";

  const $ = id =>
    document.getElementById(id);

  const frame = $("module");
  const status = $("appStatus");
  const loading = $("loading");
  const title = $("loadingTitle");
  const detail = $("loadingDetail");
  const retry = $("retry");

  const tabs = [
    ...document.querySelectorAll("[data-mode]")
  ];

  const ROUTES = Object.freeze({
    territorio: {
      view: "municipal",
      file: "22_visor_municipal.html",
      action: ""
    },

    red: {
      view: "urbano",
      file: "22_2_visor_urbano.html",
      action: ""
    },

    municipal3d: {
      view: "municipal",
      file: "22_visor_municipal.html",
      action: "municipal3d"
    },

    urbano3d: {
      view: "urbano",
      file: "22_2_visor_urbano.html",
      action: "urbano3d"
    },

    ciencia: {
      view: "municipal",
      file: "22_visor_municipal.html",
      action: "ciencia"
    }
  });

  const state = {
    municipio: "",
    indicador: "denue_mayo_2025",
    anio: "2025",
    puntos: false,
    celda: ""
  };

  let mode = null;
  let ready = false;
  let token = 0;
  let watchdog = null;

  function clearWatchdog() {
    if (watchdog !== null) {
      clearTimeout(watchdog);
    }
    watchdog = null;
  }

  function showLoading(message, extra, canRetry = false) {
    loading.hidden = false;
    title.textContent = message;
    detail.textContent = extra;
    retry.hidden = !canRetry;
  }

  function markTabs() {
    for (const tab of tabs) {
      if (tab.dataset.mode === mode) {
        tab.setAttribute("aria-current", "page");
      } else {
        tab.removeAttribute("aria-current");
      }
    }
  }

  async function navigate(nextMode, force = false) {
    const route = ROUTES[nextMode];

    if (!route || (!force && nextMode === mode)) {
      return;
    }

    mode = nextMode;
    ready = false;

    const currentToken = ++token;

    clearWatchdog();
    markTabs();

    showLoading(
      "Abriendo " + nextMode,
      "Comprobando el módulo local..."
    );

    status.textContent = "Cargando...";

    try {
      const response = await fetch(
        route.file,
        {
          method: "HEAD",
          cache: "no-store"
        }
      );

      if (currentToken !== token) return;

      if (!response.ok) {
        throw new Error(
          "HTTP " + response.status +
          " · " + route.file
        );
      }

    } catch (error) {
      if (currentToken !== token) return;

      showLoading(
        "No se pudo abrir la vista",
        String(error.message),
        true
      );

      status.textContent = "Archivo no disponible";
      return;
    }

    if (currentToken !== token) return;

    showLoading(
      "Cargando " + nextMode,
      "Inicializando mapa y controles..."
    );

    frame.src = route.file;
    frame.title = "Hotspot · " + nextMode;

    watchdog = setTimeout(() => {
      if (currentToken !== token || ready) return;

      loading.hidden = true;
      status.textContent = "Revisa la vista y la consola";
      console.warn("Módulo sin READY:", route.file);
    }, 15000);

    if (location.hash !== "#" + nextMode) {
      history.replaceState(
        null,
        "",
        "#" + nextMode
      );
    }
  }

  window.addEventListener("message", event => {
    if (
      event.origin !== location.origin ||
      event.source !== frame.contentWindow
    ) {
      return;
    }

    const message = event.data;

    if (
      !message ||
      message.app !== "hotspot22"
    ) {
      return;
    }

    const route = ROUTES[mode];

    if (!route || message.view !== route.view) {
      return;
    }

    if (message.type === "READY" && !ready) {
      ready = true;
      clearWatchdog();

      loading.hidden = true;
      status.textContent = "Vista lista · " + mode;

      frame.contentWindow.postMessage(
        {
          app: "hotspot22",
          type: "RESTORE",
          view: route.view,
          detail: {
            ...state,
            action: route.action
          }
        },
        location.origin
      );
    }

    if (
      message.type === "STATE" &&
      message.detail &&
      typeof message.detail === "object"
    ) {
      const next = message.detail;

      for (const key of Object.keys(state)) {
        if (
          Object.prototype.hasOwnProperty.call(
            next, key
          )
        ) {
          state[key] = next[key];
        }
      }
    }
  });

  for (const tab of tabs) {
    tab.addEventListener(
      "click",
      () => navigate(tab.dataset.mode)
    );
  }

  retry.addEventListener(
    "click",
    () => {
      if (mode) navigate(mode, true);
    }
  );

  window.addEventListener(
    "hashchange",
    () => {
      const requested = location.hash.slice(1);

      if (
        Object.prototype.hasOwnProperty.call(
          ROUTES, requested
        )
      ) {
        navigate(requested);
      }
    }
  );

  const initial = location.hash.slice(1);

  navigate(
    Object.prototype.hasOwnProperty.call(
      ROUTES, initial
    )
      ? initial
      : "territorio"
  );
})();
""")


# ==========================================
# 5. AUDITAR ARCHIVOS
# ==========================================

def inspect():

    errores = []

    for relativo in REQUERIDOS:
        archivo = BASE / relativo

        if not archivo.is_file():
            errores.append(
                f"Falta: {relativo}"
            )

    if errores:
        raise FileNotFoundError(
            "\n".join(errores)
        )

    # Comprobar visores integrados.

    municipal = (
        BASE / "22_visor_municipal.html"
    ).read_text(encoding="utf-8-sig")

    urbano = (
        BASE / "22_2_visor_urbano.html"
    ).read_text(encoding="utf-8-sig")

    for html, nombre in [
        (municipal, "municipal"),
        (urbano, "urbano")
    ]:
        if "22_puente.js" not in html:
            errores.append(
                f"Falta el puente en {nombre}"
            )

    if "22_2_red_espectral_three.js" not in urbano:
        errores.append(
            "No se encontro el motor 3D urbano."
        )

    if "22_2_estabilidad.js" not in urbano:
        errores.append(
            "No se encontro la capa de estabilidad."
        )

    # ======================================
    # 6. VALIDAR EMBEDDING URBANO
    # ======================================

    embedding = json.loads(
        (
            DATOS /
            "21_embedding_siniestros_2025.json"
        ).read_text(encoding="utf-8-sig")
    )

    nodos = embedding.get("nodos", [])
    aristas = embedding.get("aristas", [])

    if len(nodos) != 447:
        errores.append(
            f"Se esperaban 447 nodos, hay {len(nodos)}."
        )

    if len(aristas) != 1034:
        errores.append(
            f"Se esperaban 1034 aristas, hay {len(aristas)}."
        )

    cantidad_embedding = sum(
        n.get("espectral_xyz") is not None
        for n in nodos
    )

    if cantidad_embedding != 347:
        errores.append(
            "Se esperaban 347 embeddings."
        )

    eventos = sum(
        int(n.get("conteo_2025", 0))
        for n in nodos
    )

    if eventos != 1337:
        errores.append(
            f"Se esperaban 1337 eventos, hay {eventos}."
        )

    # ======================================
    # 7. VALIDAR ESTABILIDAD
    # ======================================

    estabilidad = json.loads(
        (
            DATOS /
            "21_estabilidad_zonas_2025.geojson"
        ).read_text(encoding="utf-8-sig")
    )

    celdas = len(
        estabilidad.get("features", [])
    )

    if celdas != 764:
        errores.append(
            f"Se esperaban 764 celdas, hay {celdas}."
        )

    # ======================================
    # 8. VALIDAR MAPA DE GUADALAJARA
    # ======================================

    contexto = json.loads(
        (
            DATOS /
            "22_2_contexto_urbano.json"
        ).read_text(encoding="utf-8-sig")
    )

    teselas = len(
        contexto.get("teselas", [])
    )

    if not 0 < teselas <= 32:
        errores.append(
            f"Cantidad de teselas invalida: {teselas}"
        )

    if not contexto.get("contornos_guadalajara"):
        errores.append(
            "Falta el limite de Guadalajara."
        )

    if errores:
        raise ValueError(
            "Auditoria fallida:\n" +
            "\n".join(errores)
        )

    return {
        "estado": "integridad_verificada",
        "nodos": len(nodos),
        "aristas": len(aristas),
        "embeddings": cantidad_embedding,
        "eventos_2025": eventos,
        "celdas_historicas": celdas,
        "teselas": teselas,
        "avisos": [
            "El documento cargado no garantiza "
            "que todas sus capas esten listas.",
            "Quedan pruebas visuales y de rendimiento.",
            "La cartografia ligera no es apropiada "
            "para analisis geometrico cientifico."
        ]
    }


# ==========================================
# 9. ESCRITURA SEGURA
# ==========================================

def guardar_seguro(ruta, contenido):

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if ruta.exists():
        actual = ruta.read_text(
            encoding="utf-8-sig"
        )

        if actual != contenido:
            raise FileExistsError(
                f"{ruta.name} ya existe con cambios. "
                "Respaldalo antes de continuar."
            )

    ruta.write_text(
        contenido,
        encoding="utf-8"
    )

    print(
        f"Generado: {ruta.relative_to(BASE)}"
    )


# ==========================================
# 10. EJECUCION PRINCIPAL
# ==========================================

def main():

    print(
        "\n=== ETAPA 22.3 | FRONTEND ==="
    )

    resultado = inspect()

    # Generar entrada web y recursos.

    guardar_seguro(
        BASE / "22_3_index.html",
        HTML
    )

    guardar_seguro(
        BASE / "app" / "22_3.css",
        CSS
    )

    guardar_seguro(
        BASE / "app" / "22_3.js",
        JS
    )

    # Guardar auditoria.

    REPORTES.mkdir(
        parents=True,
        exist_ok=True
    )

    archivo = (
        REPORTES /
        "22_3_validacion_integracion.json"
    )

    archivo.write_text(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Reporte generado: {archivo.name}"
    )

    print(
        "\nETAPA 22.3 LISTA."
    )

    print(
        "Abre: http://localhost:8000/22_3_index.html"
    )

    print(
        "Los visores originales no fueron modificados."
    )


if __name__ == "__main__":
    main()
