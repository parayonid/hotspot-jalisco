
/*
 HOTSPOT - ETAPA 17
 Papiroflexia espectral interactiva.

 Entradas:
   ./datos/grafo.json
   ./datos/municipios.json

 Dependencia:
   Plotly.js, cargado al abrir la vista.

 No recalcula modelos estadisticos.
 No modifica los datos originales.
*/

(() => {
  "use strict";

  // ==========================================
  // 1. LOCALIZAR INTERFAZ EXISTENTE
  // ==========================================

  const aside = document.querySelector("aside");
  const main = document.querySelector("main");

  const municipioSelect =
    document.getElementById("municipio");

  const ficha =
    document.getElementById("ficha");

  if (
    !aside ||
    !main ||
    !municipioSelect ||
    !ficha
  ) {
    console.error(
      "No se encontro la interfaz de Hotspot."
    );
    return;
  }

  // ==========================================
  // 2. AGREGAR ESTILOS DE PAPIROFLEXIA
  // ==========================================

  const styles = document.createElement("style");

  styles.textContent = `
    .pap-launch {
      width: 100%;
      margin: 18px 0 0;
      padding: 12px;
      border: 1px solid #a78bfa;
      border-radius: 10px;
      background: #362659;
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }

    .pap-launch:hover {
      background: #4e347d;
    }

    .pap-panel {
      position: absolute;
      inset: 0;
      z-index: 10;
      overflow: auto;
      background: #0b1020;
      padding: 16px 18px;
      color: #edf0fa;
    }

    .pap-panel[hidden] {
      display: none !important;
    }

    .pap-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .pap-panel h2 {
      margin: 0;
      font-size: 19px;
    }

    .pap-close,
    .pap-play {
      border: 1px solid #645484;
      background: #25213b;
      color: white;
      border-radius: 8px;
      padding: 10px 13px;
      cursor: pointer;
    }

    .pap-toolbar {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px 0 6px;
    }

    .pap-toolbar label {
      margin: 0;
    }

    .pap-toolbar select {
      width: auto;
      max-width: 230px;
    }

    .pap-range {
      flex: 1;
      min-width: 160px;
      accent-color: #a78bfa;
    }

    .pap-plot {
      width: 100%;
      height: calc(100vh - 235px);
      min-height: 420px;
    }

    .pap-note {
      color: #aebbd2;
      font-size: 12px;
      line-height: 1.5;
      margin: 8px 0;
    }

    .pap-message {
      font-size: 13px;
      color: #c8bbff;
      min-height: 20px;
    }

    @media (max-width: 750px) {
      .pap-panel {
        padding: 12px;
      }

      .pap-plot {
        min-height: 380px;
        height: 55vh;
      }
    }
  `;

  document.head.appendChild(styles);

  // ==========================================
  // 3. CREAR BOTON Y PANEL 3D
  // ==========================================

  const launch = document.createElement("button");

  launch.className = "pap-launch";
  launch.textContent = "◈ Abrir papiroflexia 3D";
  launch.type = "button";

  aside.insertBefore(launch, ficha);

  const panel = document.createElement("section");

  panel.className = "pap-panel";
  panel.hidden = true;

  panel.innerHTML = `
    <div class="pap-header">

      <h2>
        HOTSPOT · Papiroflexia espectral
      </h2>

      <button
        id="papClose"
        class="pap-close"
        type="button"
      >
        ← Volver al mapa
      </button>

    </div>

    <div class="pap-toolbar">

      <label for="papMetric">
        Color de nodos
      </label>

      <select id="papMetric">
        <option value="denue">
          Densidad DENUE 2025
        </option>

        <option value="atus">
          ATUS 2025
        </option>

        <option value="siniestros">
          Siniestralimap 2025
        </option>
      </select>

      <button
        id="papPlay"
        class="pap-play"
        type="button"
      >
        ▶ Animar
      </button>

      <label for="papRange">
        Transición:
        <strong id="papValue">0.00</strong>
      </label>

      <input
        id="papRange"
        class="pap-range"
        type="range"
        min="0"
        max="1"
        step="0.05"
        value="0"
      >

    </div>

    <div id="papMessage" class="pap-message">
      Preparado para cargar el grafo.
    </div>

    <div id="papPlot" class="pap-plot"></div>

    <p class="pap-note">
      0 = posiciones geográficas normalizadas.
      1 = representación espectral mediante
      los autovectores u₂, u₃ y u₄.

      Las 304 conexiones permanecen iguales.

      Los colores representan densidad
      de establecimientos o conteos registrados,
      no riesgo. Los datos ATUS faltantes
      aparecen en gris.
    </p>
  `;

  main.appendChild(panel);

  // ==========================================
  // 4. VARIABLES AUXILIARES
  // ==========================================

  const byId = id =>
    document.getElementById(id);

  const message = text => {
    byId("papMessage").textContent = text;
  };

  const htmlSafe = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      ch => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[ch])
    );

  let graph = null;
  let municipal = null;

  let positionsGeo = null;
  let positionsSpec = null;
  let edges = null;

  let plotCreated = false;
  let drawing = false;
  let pending = false;
  let timer = null;

  // ==========================================
  // 5. CARGAR PLOTLY BAJO DEMANDA
  // ==========================================

  function loadPlotly() {

    if (window.Plotly) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {

      const script = document.createElement("script");

      script.src =
        "https://cdn.plot.ly/plotly-2.35.2.min.js";

      script.onload = () => {

        if (window.Plotly) {
          resolve();
        } else {
          reject(
            new Error("Plotly no esta disponible.")
          );
        }
      };

      script.onerror = () => {
        reject(
          new Error(
            "No se pudo cargar Plotly desde Internet."
          )
        );
      };

      document.head.appendChild(script);
    });
  }

  // ==========================================
  // 6. LEER JSON
  // ==========================================

  async function json(url) {

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(
        `${url}: HTTP ${response.status}`
      );
    }

    return response.json();
  }

  // ==========================================
  // 7. NORMALIZAR COORDENADAS
  // ==========================================

  function normalize(points) {

    const mean = [0, 1, 2].map(j =>
      points.reduce(
        (total, point) =>
          total + point[j],
        0
      ) / points.length
    );

    const centered = points.map(p =>
      p.map(
        (value, j) => value - mean[j]
      )
    );

    const max = Math.max(
      1e-12,
      ...centered.flat().map(Math.abs)
    );

    return centered.map(p =>
      p.map(value => value / max)
    );
  }

  // ==========================================
  // 8. CARGAR Y VALIDAR EL GRAFO REAL
  // ==========================================

  async function prepare() {

    if (graph) return;

    message(
      "Cargando grafo, municipios y Plotly..."
    );

    const [g, m] = await Promise.all([
      json("./datos/grafo.json"),
      json("./datos/municipios.json"),
      loadPlotly()
    ]);

    if (
      !Array.isArray(g.nodos) ||
      g.nodos.length !== 125 ||
      !Array.isArray(g.aristas) ||
      g.aristas.length !== 304 ||
      !Array.isArray(m.municipios) ||
      m.municipios.length !== 125
    ) {
      throw new Error(
        "Se esperaban 125 nodos, " +
        "304 aristas y 125 municipios."
      );
    }

    const ids = new Map(
      g.nodos.map((node, i) => [
        String(node.id),
        i
      ])
    );

    const byMunicipality = new Map(
      m.municipios.map(x => [
        String(x.cvegeo),
        x
      ])
    );

    if (
      ids.size !== 125 ||
      byMunicipality.size !== 125
    ) {
      throw new Error(
        "Existen claves municipales repetidas."
      );
    }

    // Posicion geografica [lon, lat, 0].

    const geo = g.nodos.map(node => [
      ...node.geografico_lonlat,
      0
    ].map(Number));

    // Coordenadas espectrales [u2, u3, u4].

    const spec = g.nodos.map(node =>
      node.espectral_xyz.map(Number)
    );

    const invalid = [...geo, ...spec].some(p =>
      p.length !== 3 ||
      p.some(v => !Number.isFinite(v))
    );

    if (invalid) {
      throw new Error(
        "Coordenadas invalidas en el grafo."
      );
    }

    // Convertir IDs de las aristas
    // a posiciones en el arreglo de nodos.

    const edgeIndices = g.aristas.map(edge => [
      ids.get(String(edge.source)),
      ids.get(String(edge.target))
    ]);

    const badEdges = edgeIndices.some(
      ([i, j]) =>
        i === undefined ||
        j === undefined ||
        i === j
    );

    if (badEdges) {
      throw new Error(
        "El grafo contiene aristas invalidas."
      );
    }

    if (
      g.nodos.some(
        node => !byMunicipality.has(String(node.id))
      )
    ) {
      throw new Error(
        "Hay nodos sin datos municipales."
      );
    }

    graph = g;
    municipal = byMunicipality;

    positionsGeo = normalize(geo);
    positionsSpec = normalize(spec);

    edges = edgeIndices;
  }

  // ==========================================
  // 9. SELECCIONAR INDICADOR PARA COLORES
  // ==========================================

  function metricFor(node) {

    const m = municipal.get(
      String(node.id)
    );

    const key = byId("papMetric").value;

    let raw;

    if (key === "denue") {
      raw = m.denue_por_km2;
    } else if (key === "atus") {
      raw = m.registros_atus_2025;
    } else {
      raw = m.siniestros_registrados_2025;
    }

    if (
      raw === null ||
      raw === undefined ||
      raw === ""
    ) {
      return null;
    }

    const number = Number(raw);

    if (
      !Number.isFinite(number) ||
      number < 0
    ) {
      return null;
    }

    // Escala cromatica logaritmica.
    return Math.log1p(number);
  }

  // ==========================================
  // 10. TEXTO INFORMATIVO MUNICIPAL
  // ==========================================

  function description(node) {

    const m = municipal.get(
      String(node.id)
    );

    const number = value =>
      value == null
        ? "Sin dato"
        : Number(value).toLocaleString("es-MX");

    return `
      <b>${htmlSafe(node.nombre)}</b>
      <br>
      DENUE: ${
        number(
          m.establecimientos_denue_mayo_2025
        )
      }
      <br>
      ATUS 2025: ${
        number(m.registros_atus_2025)
      }
      <br>
      Siniestralimap 2025: ${
        number(m.siniestros_registrados_2025)
      }
    `;
  }

  // ==========================================
  // 11. INTERPOLAR Y CONSTRUIR GRAFICAS
  // ==========================================

  function tracesAt(t) {

    const pos = positionsGeo.map((p, i) =>
      p.map(
        (value, j) =>
          (1 - t) * value +
          t * positionsSpec[i][j]
      )
    );

    // Coordenadas de las 304 aristas.

    const ex = [];
    const ey = [];
    const ez = [];

    for (const [i, j] of edges) {

      ex.push(pos[i][0], pos[j][0], null);
      ey.push(pos[i][1], pos[j][1], null);
      ez.push(pos[i][2], pos[j][2], null);
    }

    // Valores de la variable elegida.

    const values = graph.nodos.map(metricFor);

    const good = values.flatMap(
      (v, i) => v === null ? [] : [i]
    );

    const absent = values.flatMap(
      (v, i) => v === null ? [i] : []
    );

    const maxValue = Math.max(
      0.1,
      ...good.map(i => values[i])
    );

    const selected = graph.nodos.findIndex(
      node =>
        String(node.id) === municipioSelect.value
    );

    // Crear un conjunto de marcadores.

    const point = (indices, marker, name) => ({
      type: "scatter3d",
      mode: "markers",
      name,

      x: indices.map(i => pos[i][0]),
      y: indices.map(i => pos[i][1]),
      z: indices.map(i => pos[i][2]),

      customdata: indices.map(i =>
        String(graph.nodos[i].id)
      ),

      text: indices.map(i =>
        description(graph.nodos[i])
      ),

      hovertemplate:
        "%{text}<extra></extra>",

      marker
    });

    return [

      // Traza 0: conexiones.

      {
        type: "scatter3d",
        mode: "lines",
        name: "Vecindad",
        hoverinfo: "skip",
        showlegend: false,

        x: ex,
        y: ey,
        z: ez,

        line: {
          color: "rgba(165,176,205,0.36)",
          width: 2
        }
      },

      // Traza 1: municipios con dato.

      point(
        good,
        {
          size: 5,
          opacity: 0.96,

          color: good.map(i => values[i]),

          colorscale: "Viridis",
          cmin: 0,
          cmax: maxValue,

          colorbar: {
            title: {
              text: "log(1+x)"
            },
            thickness: 12,
            len: 0.58
          }
        },
        "Municipios"
      ),

      // Traza 2: municipios sin dato.

      point(
        absent,
        {
          size: 5,
          color: "#768295"
        },
        "Sin dato"
      ),

      // Traza 3: municipio seleccionado.

      point(
        selected < 0 ? [] : [selected],
        {
          size: 11,
          color: "#ffffff",
          symbol: "diamond",

          line: {
            color: "#a78bfa",
            width: 3
          }
        },
        "Municipio seleccionado"
      )
    ];
  }

  // ==========================================
  // 12. CONFIGURACION DE LA ESCENA 3D
  // ==========================================

  const layout = {

    paper_bgcolor: "#0b1020",
    plot_bgcolor: "#0b1020",

    font: {
      color: "#e8eafd"
    },

    margin: {
      l: 0,
      r: 0,
      t: 10,
      b: 0
    },

    showlegend: false,

    uirevision: "camara-papiroflexia",

    scene: {

      xaxis: {
        visible: false,
        range: [-1.25, 1.25]
      },

      yaxis: {
        visible: false,
        range: [-1.25, 1.25]
      },

      zaxis: {
        visible: false,
        range: [-1.25, 1.25]
      },

      aspectmode: "cube",

      bgcolor: "#0b1020",

      camera: {
        eye: {
          x: 1.5,
          y: 1.4,
          z: 1.7
        }
      }
    }
  };

  // ==========================================
  // 13. DIBUJAR O ACTUALIZAR LA ESCENA
  // ==========================================

  async function draw() {

    if (!graph || panel.hidden) {
      return;
    }

    if (drawing) {
      pending = true;
      return;
    }

    drawing = true;

    try {

      do {

        pending = false;

        const t = Number(
          byId("papRange").value
        );

        byId("papValue").textContent =
          t.toFixed(2);

        const traces = tracesAt(t);

        if (!plotCreated) {

          await Plotly.newPlot(
            "papPlot",
            traces,
            layout,
            {
              responsive: true,
              displaylogo: false
            }
          );

          plotCreated = true;

          // Elegir municipio haciendo clic
          // sobre un nodo de la grafica 3D.

          byId("papPlot").on(
            "plotly_click",
            event => {

              const id =
                event.points?.[0]?.customdata;

              if (id) {

                municipioSelect.value =
                  String(id);

                municipioSelect.dispatchEvent(
                  new Event(
                    "change",
                    { bubbles: true }
                  )
                );

                draw();
              }
            }
          );

        } else {

          await Plotly.react(
            "papPlot",
            traces,
            layout,
            {
              responsive: true,
              displaylogo: false
            }
          );
        }

      } while (pending && !panel.hidden);

    } finally {
      drawing = false;
    }
  }

  // ==========================================
  // 14. DETENER LA ANIMACION
  // ==========================================

  function stop() {

    if (timer !== null) {
      clearInterval(timer);
    }

    timer = null;

    byId("papPlay").textContent =
      "▶ Animar";
  }

  // ==========================================
  // 15. ABRIR PAPIROFLEXIA
  // ==========================================

  launch.addEventListener(
    "click",
    async () => {

      panel.hidden = false;

      try {

        await prepare();

        message(
          "125 municipios · 304 conexiones. " +
          "Haz clic en un nodo para seleccionarlo."
        );

        await draw();

        Plotly.Plots.resize(
          byId("papPlot")
        );

      } catch (error) {

        message(
          "Error de papiroflexia: " +
          error.message
        );

        console.error(error);
      }
    }
  );

  // ==========================================
  // 16. REGRESAR AL MAPA
  // ==========================================

  byId("papClose").addEventListener(
    "click",
    () => {

      stop();

      panel.hidden = true;
    }
  );

  // ==========================================
  // 17. CONTROLES INTERACTIVOS
  // ==========================================

  byId("papRange").addEventListener(
    "input",
    draw
  );

  byId("papMetric").addEventListener(
    "change",
    draw
  );

  // Sincronizar seleccion con el mapa 2D.

  municipioSelect.addEventListener(
    "change",
    draw
  );

  // ==========================================
  // 18. REPRODUCIR LA TRANSFORMACION
  // ==========================================

  byId("papPlay").addEventListener(
    "click",
    () => {

      if (!graph) {
        return;
      }

      // Si esta animando, detener.

      if (timer !== null) {
        stop();
        return;
      }

      // Si llego al final,
      // comenzar desde el principio.

      if (
        Number(byId("papRange").value) >= 1
      ) {
        byId("papRange").value = "0";
      }

      byId("papPlay").textContent =
        "⏸ Pausar";

      timer = setInterval(() => {

        const next =
          Number(
            byId("papRange").value
          ) + 0.05;

        if (next > 1.001) {
          stop();
          return;
        }

        byId("papRange").value = String(
          Math.min(
            1,
            Number(next.toFixed(2))
          )
        );

        draw();

      }, 190);
    }
  );

})();
