
/*
 * HOTSPOT | ETAPA 18
 * Panel científico: Seguridad regional y
 * resultados de inferencia estadística.
 *
 * Entradas:
 *   ./datos/seguridad.json
 *   ./datos/modelos.json
 *
 * No modifica el mapa ni la papiroflexia.
 */

(() => {
  "use strict";

  // =========================================
  // 1. RECUPERAR LA INTERFAZ
  // =========================================

  const aside = document.querySelector("aside");
  const main = document.querySelector("main");
  const ficha = document.getElementById("ficha");

  if (!aside || !main || !ficha) {
    console.error(
      "No se encontró la interfaz de Hotspot."
    );
    return;
  }

  // =========================================
  // 2. ESTILOS DEL PANEL
  // =========================================

  const style = document.createElement("style");

  style.textContent = `
    .ci-launch {
      display: block;
      width: 100%;
      margin: 12px 0;
      padding: 12px;
      border: 1px solid #38bdf8;
      border-radius: 10px;
      background: #15344b;
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }

    .ci-panel {
      position: absolute;
      inset: 0;
      z-index: 20;
      overflow: auto;
      background: #0b1020;
      padding: 20px;
      color: #edf0fa;
    }

    .ci-panel[hidden] {
      display: none !important;
    }

    .ci-header,
    .ci-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .ci-header h2 {
      font-size: 20px;
      margin: 0;
    }

    .ci-btn {
      background: #24314c;
      border: 1px solid #526382;
      border-radius: 8px;
      color: #fff;
      padding: 9px 12px;
      cursor: pointer;
    }

    .ci-btn[aria-pressed="true"] {
      border-color: #a78bfa;
      background: #49336a;
    }

    .ci-controls {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 18px 0;
    }

    .ci-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 175px;
      flex: 1;
    }

    .ci-field label {
      margin: 0;
      font-size: 12px;
      color: #bbc9df;
    }

    .ci-field select {
      width: 100%;
      max-width: none;
    }

    .ci-card {
      background: #172238;
      border: 1px solid #34445f;
      border-radius: 12px;
      padding: 16px;
      margin: 14px 0;
      overflow-x: auto;
    }

    .ci-note {
      font-size: 12px;
      line-height: 1.6;
      color: #aebdd4;
    }

    .ci-chart {
      width: 100%;
      min-height: 300px;
      display: block;
    }

    .ci-table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
    }

    .ci-table th,
    .ci-table td {
      padding: 9px;
      text-align: left;
      border-bottom: 1px solid #34445f;
    }

    .ci-table th {
      color: #b8cae6;
    }

    .ci-warn {
      color: #fbbf24;
    }

    .ci-stat {
      font-size: 25px;
      font-weight: 700;
      color: #d0bbff;
    }
  `;

  document.head.appendChild(style);

  // =========================================
  // 3. BOTÓN PARA ABRIR EL PANEL
  // =========================================

  const launch = document.createElement("button");

  launch.type = "button";
  launch.className = "ci-launch";
  launch.textContent = "▤ Abrir panel científico";

  aside.insertBefore(launch, ficha);

  // =========================================
  // 4. CONSTRUIR EL PANEL
  // =========================================

  const panel = document.createElement("section");

  panel.className = "ci-panel";
  panel.hidden = true;

  panel.innerHTML = `
    <div class="ci-header">

      <h2>
        HOTSPOT · Panel científico
      </h2>

      <button
        class="ci-btn"
        id="ciClose"
        type="button"
      >
        ← Volver al mapa
      </button>

    </div>

    <div
      class="ci-actions"
      style="justify-content:flex-start;margin-top:18px"
    >

      <button
        class="ci-btn"
        id="ciTabSeg"
        type="button"
        aria-pressed="true"
      >
        Seguridad regional
      </button>

      <button
        class="ci-btn"
        id="ciTabMod"
        type="button"
        aria-pressed="false"
      >
        Modelos y validación
      </button>

    </div>

    <p
      id="ciStatus"
      class="ci-note"
      role="status"
    >
      Los datos se cargarán al abrir el panel.
    </p>

    <!-- VISTA DE SEGURIDAD -->

    <div id="ciSeg">

      <div class="ci-controls">

        <div class="ci-field">
          <label for="ciRegion">Región</label>
          <select id="ciRegion"></select>
        </div>

        <div class="ci-field">
          <label for="ciDelito">Indicador / delito</label>
          <select id="ciDelito"></select>
        </div>

        <div class="ci-field">
          <label for="ciMedida">Medida</label>
          <select id="ciMedida"></select>
        </div>

      </div>

      <div class="ci-card">

        <h3 id="ciTitle">
          Serie mensual
        </h3>

        <div id="ciChart"></div>

        <p
          id="ciDetail"
          class="ci-note"
        ></p>

      </div>

      <p class="ci-note">
        Fuente: Plataforma de Seguridad.
        Los datos están agregados por región
        y mes. No representan ubicaciones
        municipales ni puntos delictivos.

        Los meses ausentes no se rellenan con
        cero. Los registros marcados REVISAR
        requieren especial cautela.
      </p>

    </div>

    <!-- VISTA DE INFERENCIA -->

    <div id="ciMod" hidden>

      <div class="ci-card">
        <h3>Diagnósticos de modelos</h3>
        <div id="ciModels"></div>
      </div>

      <div class="ci-card">
        <h3>Dependencia espacial — ATUS/DENUE</h3>
        <div id="ciMoran"></div>
      </div>

      <div class="ci-card">
        <h3>Energía espectral — DENUE</h3>
        <div id="ciEnergy"></div>
      </div>

      <p class="ci-note">
        Los resultados inferenciales son
        exploratorios. La autocorrelación
        temporal y los posibles sesgos de
        cobertura todavía requieren tratamiento.

        Estos modelos no generan probabilidades
        individuales de delito ni mapas de
        riesgo validados.
      </p>

    </div>
  `;

  main.appendChild(panel);

  // =========================================
  // 5. HERRAMIENTAS
  // =========================================

  const el = id => document.getElementById(id);

  const escapeHtml = value =>
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

  const num = value => {

    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "Sin dato";
    }

    const n = Number(value);

    return Number.isFinite(n)
      ? n.toLocaleString("es-MX", {
          maximumFractionDigits: 4
        })
      : "Sin dato";
  };

  const decimal = (value, digits = 4) => {

    const n = Number(value);

    return value == null || !Number.isFinite(n)
      ? "Sin dato"
      : n.toFixed(digits);
  };

  const setStatus = text => {
    el("ciStatus").textContent = text;
  };

  let seguridad = null;
  let modelos = null;
  let pendingLoad = null;

  // =========================================
  // 6. CARGAR JSON
  // =========================================

  async function load(url) {

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(
        `${url}: HTTP ${response.status}`
      );
    }

    return response.json();
  }

  const distinct = array => [
    ...new Set(
      array.filter(
        value => value != null && value !== ""
      )
    )
  ];

  // =========================================
  // 7. LLENAR SELECTORES
  // =========================================

  function options(id, values, preferred) {

    const select = el(id);

    select.replaceChildren(
      ...values.map(
        value => new Option(value, value)
      )
    );

    select.value = values.includes(preferred)
      ? preferred
      : values[0] ?? "";
  }

  function updateMeasures() {

    const records = seguridad.filter(row =>
      row.region === el("ciRegion").value &&
      row.delito === el("ciDelito").value
    );

    options(
      "ciMedida",
      distinct(
        records.map(r => String(r.medida))
      ).sort(),
      el("ciMedida").value
    );

    drawSecurity();
  }

  function updateDelitos() {

    const records = seguridad.filter(row =>
      row.region === el("ciRegion").value
    );

    options(
      "ciDelito",
      distinct(
        records.map(r => String(r.delito))
      ).sort(
        (a, b) => a.localeCompare(b, "es")
      ),
      el("ciDelito").value
    );

    updateMeasures();
  }

  // =========================================
  // 8. CONSTRUIR LA GRÁFICA TEMPORAL
  // =========================================

  function drawSecurity() {

    if (!seguridad) return;

    const region = el("ciRegion").value;
    const delito = el("ciDelito").value;
    const medida = el("ciMedida").value;

    const rows = seguridad
      .filter(row =>
        row.region === region &&
        row.delito === delito &&
        row.medida === medida &&
        /^\d{4}-\d{2}$/.test(
          String(row.periodo)
        ) &&
        row.cantidad !== null &&
        row.cantidad !== "" &&
        Number.isFinite(
          Number(row.cantidad)
        )
      )
      .map(row => ({
        periodo: String(row.periodo),
        cantidad: Number(row.cantidad),

        marcado:
          String(
            row.control_regional ?? ""
          ).toUpperCase() === "REVISAR"
      }))
      .sort(
        (a, b) =>
          a.periodo.localeCompare(b.periodo)
      );

    el("ciTitle").textContent =
      `${delito} · ${medida} · ${region}`;

    if (!rows.length) {

      el("ciChart").textContent =
        "No hay observaciones disponibles.";

      el("ciDetail").textContent = "";

      return;
    }

    // Convertir un periodo a número de mes.

    const monthIndex = period =>
      Number(period.slice(0, 4)) * 12 +
      Number(period.slice(5, 7)) - 1;

    const t0 = monthIndex(
      rows[0].periodo
    );

    const t1 = monthIndex(
      rows[rows.length - 1].periodo
    );

    const span = Math.max(1, t1 - t0);

    const max = Math.max(
      1,
      ...rows.map(r => r.cantidad)
    );

    // Dimensiones SVG.

    const W = 940;
    const H = 330;

    const L = 66;
    const R = 24;
    const T = 22;
    const B = 45;

    const x = row =>
      L +
      (monthIndex(row.periodo) - t0) /
      span * (W - L - R);

    const y = value =>
      T +
      (1 - value / max) *
      (H - T - B);

    // Construir segmentos.
    // Si falta un mes, la línea se interrumpe.

    const parts = [];

    let previousMonth = null;

    for (const row of rows) {

      const current = monthIndex(
        row.periodo
      );

      const command =
        previousMonth !== null &&
        current === previousMonth + 1
          ? "L"
          : "M";

      parts.push(
        `${command}${x(row).toFixed(2)},` +
        `${y(row.cantidad).toFixed(2)}`
      );

      previousMonth = current;
    }

    // Líneas horizontales y escala vertical.

    let grid = "";

    for (let k = 0; k <= 4; k++) {

      const value = max * k / 4;
      const gy = y(value);

      grid += `
        <line
          x1="${L}"
          y1="${gy}"
          x2="${W - R}"
          y2="${gy}"
          stroke="#334155"
        />
      `;

      grid += `
        <text
          x="${L - 9}"
          y="${gy + 4}"
          fill="#b8c8de"
          text-anchor="end"
          font-size="12"
        >
          ${num(Math.round(value))}
        </text>
      `;
    }

    // Etiquetas anuales.

    const yearMarks = rows.filter(
      row => row.periodo.endsWith("-01")
    );

    const ticks = yearMarks.map(row => `
      <text
        x="${x(row)}"
        y="${H - 12}"
        fill="#b8c8de"
        text-anchor="middle"
        font-size="12"
      >
        ${row.periodo.slice(0, 4)}
      </text>
    `).join("");

    // Señalar observaciones marcadas REVISAR.

    const circles = rows
      .filter(row => row.marcado)
      .map(row => `
        <circle
          cx="${x(row)}"
          cy="${y(row.cantidad)}"
          r="6"
          fill="#fbbf24"
          stroke="#ffffff"
          stroke-width="1"
        >
          <title>
            ${escapeHtml(row.periodo)}:
            ${num(row.cantidad)} (REVISAR)
          </title>
        </circle>
      `)
      .join("");

    // Dibujar SVG.

    el("ciChart").innerHTML = `
      <svg
        class="ci-chart"
        viewBox="0 0 ${W} ${H}"
        role="img"
        aria-label="Serie mensual de
          ${escapeHtml(delito)} en
          ${escapeHtml(region)}"
      >

        ${grid}

        <path
          d="${parts.join(" ")}"
          fill="none"
          stroke="#a78bfa"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        />

        ${circles}
        ${ticks}

      </svg>
    `;

    // Resumen de la serie.

    const marked = rows.filter(
      row => row.marcado
    ).length;

    el("ciDetail").textContent =
      `${rows.length} meses con registro. ` +
      `Primer periodo: ${rows[0].periodo}. ` +
      `Último periodo: ` +
      `${rows[rows.length - 1].periodo}. ` +
      `Meses marcados REVISAR: ${marked}. ` +
      "Los huecos temporales no se interpolan.";
  }

  // =========================================
  // 9. MOSTRAR RESULTADOS ESTADÍSTICOS
  // =========================================

  function renderModels() {

    const diags = Array.isArray(
      modelos.diagnosticos
    )
      ? modelos.diagnosticos
      : [];

    const cells = diags.map(d => `
      <tr>
        <td>${escapeHtml(d.analisis)}</td>
        <td>${escapeHtml(d.modelo)}</td>
        <td>${num(d.n)}</td>
        <td>${decimal(d.aic, 2)}</td>
        <td>${decimal(d.dispersion_pearson, 2)}</td>
      </tr>
    `).join("");

    el("ciModels").innerHTML = `
      <table class="ci-table">

        <thead>
          <tr>
            <th>Análisis</th>
            <th>Modelo</th>
            <th>n</th>
            <th>AIC</th>
            <th>Dispersión Pearson</th>
          </tr>
        </thead>

        <tbody>
          ${cells}
        </tbody>

      </table>

      <p class="ci-note">
        El AIC solo debe compararse entre
        modelos ajustados sobre los mismos
        datos y la misma variable respuesta.
      </p>
    `;

    // =====================================
    // 10. RESULTADOS DE MORAN
    // =====================================

    const mo = Array.isArray(
      modelos.moran_atus
    )
      ? modelos.moran_atus[0]
      : null;

    el("ciMoran").innerHTML = mo
      ? `
        <p class="ci-stat">
          I = ${decimal(mo.I_moran, 4)}
        </p>

        <p>
          p unilateral, agrupamiento positivo:
          <strong>
            ${decimal(
              mo.p_agrupamiento_positivo,
              4
            )}
          </strong>
        </p>

        <p class="ci-note">
          Residuos NB2 en
          ${num(mo.n_utilizados_moran)}
          municipios. No detectar agrupamiento
          significativo no demuestra
          independencia espacial.
        </p>
      `
      : "<p>No hay resultados de Moran.</p>";

    // =====================================
    // 11. ENERGÍA TERRITORIAL DENUE
    // =====================================

    const en = Array.isArray(
      modelos.energia_denue
    )
      ? modelos.energia_denue[0]
      : null;

    el("ciEnergy").innerHTML = en
      ? `
        <p class="ci-stat">
          E = ${decimal(
            en.energia_observada,
            3
          )}
        </p>

        <p>
          Media aleatoria:
          <strong>
            ${decimal(
              en.media_energia_aleatoria,
              3
            )}
          </strong>
        </p>

        <p>
          p suavidad:
          <strong>
            ${decimal(
              en.p_suavidad_unilateral,
              4
            )}
          </strong>

          · p contraste:
          <strong>
            ${decimal(
              en.p_contraste_unilateral,
              4
            )}
          </strong>
        </p>

        <p class="ci-note">
          Energía de la densidad DENUE
          transformada sobre el grafo.
          No es un indicador de violencia.
        </p>
      `
      : "<p>No hay resultados de energía.</p>";
  }

  // =========================================
  // 12. CARGAR DATOS UNA SOLA VEZ
  // =========================================

  async function prepare() {

    if (seguridad && modelos) {
      return;
    }

    if (!pendingLoad) {

      pendingLoad = Promise.all([
        load("./datos/seguridad.json"),
        load("./datos/modelos.json")
      ]);
    }

    try {

      const [s, m] = await pendingLoad;

      if (
        !Array.isArray(s.registros) ||
        !Array.isArray(m.diagnosticos)
      ) {
        throw new Error(
          "Formato JSON inesperado."
        );
      }

      seguridad = s.registros;
      modelos = m;

      options(
        "ciRegion",
        distinct(
          seguridad.map(
            row => String(row.region)
          )
        ).sort(),
        "ESTADO"
      );

      updateDelitos();
      renderModels();

      setStatus(
        `${seguridad.length.toLocaleString("es-MX")} ` +
        "observaciones de Seguridad cargadas."
      );

    } catch (error) {

      pendingLoad = null;
      throw error;
    }
  }

  // =========================================
  // 13. CAMBIAR ENTRE PESTAÑAS
  // =========================================

  function showTab(which) {

    el("ciSeg").hidden = which !== "seg";
    el("ciMod").hidden = which !== "mod";

    el("ciTabSeg").setAttribute(
      "aria-pressed",
      String(which === "seg")
    );

    el("ciTabMod").setAttribute(
      "aria-pressed",
      String(which === "mod")
    );
  }

  // =========================================
  // 14. ABRIR Y CERRAR PANEL
  // =========================================

  launch.addEventListener(
    "click",
    async () => {

      // Cerrar la papiroflexia si está abierta.

      const closePap =
        document.getElementById("papClose");

      if (
        closePap &&
        !closePap.closest(".pap-panel")?.hidden
      ) {
        closePap.click();
      }

      panel.hidden = false;

      try {
        await prepare();
      } catch (error) {
        setStatus(
          `Error: ${error.message}`
        );
        console.error(error);
      }
    }
  );

  el("ciClose").addEventListener(
    "click",
    () => {
      panel.hidden = true;
    }
  );

  // =========================================
  // 15. REGISTRAR CONTROLES
  // =========================================

  el("ciTabSeg").addEventListener(
    "click",
    () => showTab("seg")
  );

  el("ciTabMod").addEventListener(
    "click",
    () => showTab("mod")
  );

  el("ciRegion").addEventListener(
    "change",
    updateDelitos
  );

  el("ciDelito").addEventListener(
    "change",
    updateMeasures
  );

  el("ciMedida").addEventListener(
    "change",
    drawSecurity
  );

  // Si se abre la papiroflexia,
  // ocultar este panel.

  document.querySelector(".pap-launch")
    ?.addEventListener(
      "click",
      () => {
        panel.hidden = true;
      }
    );

})();
