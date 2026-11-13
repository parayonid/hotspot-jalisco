
/*
 HOTSPOT - ETAPA 19

 Papiroflexia territorial-espectral
 con Three.js y WebGL.

 Entrada:
   ./datos/19_escena_espectral.json

 Renderizado:
   125 nodos mediante InstancedMesh
   304 aristas mediante BufferGeometry

 No recalcula el laplaciano.
 No modifica los datos científicos.
*/

import * as THREE from "three";

import {
  OrbitControls
} from "three/addons/controls/OrbitControls.js";


// ============================================
// 1. LOCALIZAR LA INTERFAZ
// ============================================

const aside = document.querySelector("aside");

const main = document.querySelector("main");

const ficha = document.getElementById("ficha");

const municipio = document.getElementById("municipio");

if (!aside || !main || !ficha || !municipio) {
  throw new Error(
    "No se encontró la interfaz de Hotspot."
  );
}


// ============================================
// 2. AGREGAR ESTILOS
// ============================================

const css = document.createElement("style");

css.textContent = `
  .pap-launch {
    width: 100%;
    margin: 18px 0 0;
    padding: 12px;
    background: #362659;
    color: white;
    border: 1px solid #a78bfa;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
  }

  .pap-panel {
    position: absolute;
    inset: 0;
    z-index: 15;
    overflow: auto;
    background: #0b1020;
    padding: 16px 18px;
    color: #edf0fa;
  }

  .pap-panel[hidden] {
    display: none !important;
  }

  .pap-head,
  .pap-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }

  .pap-controls {
    justify-content: flex-start;
    padding: 12px 0;
  }

  .pap-controls label {
    margin: 0;
  }

  .pap-controls select {
    max-width: 220px;
    width: auto;
  }

  .pap-controls input[type="range"] {
    flex: 1;
    min-width: 160px;
    accent-color: #a78bfa;
  }

  .pap-panel button {
    background: #30274d;
    border: 1px solid #6b5c96;
    color: white;
    border-radius: 8px;
    padding: 10px 13px;
    cursor: pointer;
  }

  .pap-view {
    height: calc(100vh - 235px);
    min-height: 430px;
    border: 1px solid #293652;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
  }

  .pap-view canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  .pap-hint,
  .pap-selection {
    font-size: 12px;
    color: #b8c6df;
    line-height: 1.6;
  }

  .pap-status {
    font-size: 12px;
    color: #c5b5ff;
    min-height: 22px;
    padding: 6px 0;
  }

  @media (max-width: 750px) {
    .pap-panel {
      padding: 12px;
    }

    .pap-view {
      height: 55vh;
      min-height: 330px;
    }
  }
`;

document.head.appendChild(css);


// ============================================
// 3. CREAR BOTÓN DE PAPIROFLEXIA
// ============================================

const launch = document.createElement("button");

launch.className = "pap-launch";
launch.type = "button";

launch.textContent =
  "◈ Abrir papiroflexia 3D · GPU";

aside.insertBefore(launch, ficha);


// ============================================
// 4. CREAR PANEL 3D
// ============================================

const panel = document.createElement("section");

panel.className = "pap-panel";
panel.hidden = true;

panel.innerHTML = `

  <div class="pap-head">

    <h2>
      HOTSPOT · Papiroflexia territorial-espectral
    </h2>

    <button id="papClose" type="button">
      ← Volver al mapa
    </button>

  </div>

  <div class="pap-controls">

    <label for="papMetric">
      Color
    </label>

    <select id="papMetric">

      <option value="denue">
        Densidad DENUE 2025
      </option>

      <option value="atus">
        ATUS 2025
      </option>

      <option value="siniestralimap">
        Siniestralimap 2025
      </option>

    </select>

    <button id="papPlay" type="button">
      ▶ Animar
    </button>

    <label for="papRange">
      Transformación
      <strong id="papValue">0.00</strong>
    </label>

    <input
      id="papRange"
      type="range"
      min="0"
      max="1"
      step="0.005"
      value="0"
    >

  </div>

  <div
    id="papStatus"
    class="pap-status"
    role="status"
  >
    Escena por cargar.
  </div>

  <div
    id="papView"
    class="pap-view"
  ></div>

  <p
    id="papSelection"
    class="pap-selection"
  >
    Selecciona un nodo haciendo clic.
  </p>

  <p class="pap-hint">
    La silueta de Jalisco permanece fija.

    Los 125 nodos pasan de su posición
    geográfica al embedding espectral.

    Se conservan las 304 conexiones.

    Arrastra para rotar la cámara.
    Usa la rueda para acercarte.

    La elevación no representa riesgo.
  </p>
`;

main.appendChild(panel);


// ============================================
// 5. VARIABLES DEL MOTOR
// ============================================

const $ = id =>
  document.getElementById(id);

const status = message => {
  $("papStatus").textContent = message;
};

let data = null;

let renderer;
let scene;
let camera;
let orbit;

let pointsMesh;
let edgesMesh;
let selectedMesh;

let edgesAttribute;
let currentPositions;

let rafAnimation = 0;
let rafRender = 0;

let initialized = false;
let preparing = null;

let resizeObserver = null;

let fpsFrames = 0;
let fpsStart = 0;


// ============================================
// 6. RENDERIZAR CUANDO SEA NECESARIO
// ============================================

function renderOnce() {

  if (
    panel.hidden ||
    !renderer ||
    rafRender
  ) {
    return;
  }

  rafRender = requestAnimationFrame(() => {

    rafRender = 0;

    if (!panel.hidden) {
      renderer.render(scene, camera);
    }
  });
}


// ============================================
// 7. CREAR ESCENA THREE.JS
// ============================================

async function prepare() {

  if (initialized) {
    return;
  }

  if (preparing) {
    return preparing;
  }

  preparing = (async () => {

    status(
      "Cargando Jalisco y preparando WebGL..."
    );

    const response = await fetch(
      "./datos/19_escena_espectral.json"
    );

    if (!response.ok) {
      throw new Error(
        `Escena HTTP ${response.status}`
      );
    }

    const incoming = await response.json();

    if (
      incoming.nodos?.length !== 125 ||
      incoming.aristas?.length !== 304
    ) {
      throw new Error(
        "Se esperaban 125 nodos y 304 aristas."
      );
    }

    data = incoming;

    // ========================================
    // 8. CREAR RENDERIZADOR WEBGL
    // ========================================

    const canvasHost = $("papView");

    renderer = new THREE.WebGLRenderer({
      antialias: false,
      powerPreference: "high-performance"
    });

    renderer.setPixelRatio(
      Math.min(
        window.devicePixelRatio || 1,
        1.5
      )
    );

    renderer.setClearColor(
      0x0b1020,
      1
    );

    canvasHost.appendChild(
      renderer.domElement
    );

    // Una sola escena.
    scene = new THREE.Scene();

    // ========================================
    // 9. CONFIGURAR CÁMARA
    // ========================================

    camera = new THREE.PerspectiveCamera(
      43,
      1,
      0.1,
      100
    );

    camera.position.set(
      0,
      5.2,
      5.9
    );

    camera.lookAt(
      0,
      0.45,
      0
    );

    orbit = new OrbitControls(
      camera,
      renderer.domElement
    );

    orbit.target.set(
      0,
      0.4,
      0
    );

    orbit.enableDamping = false;

    orbit.maxDistance = 16;
    orbit.minDistance = 2;

    orbit.addEventListener(
      "change",
      renderOnce
    );

    // ========================================
    // 10. DIBUJAR SILUETA DE JALISCO
    // ========================================

    const fillMaterial =
      new THREE.MeshBasicMaterial({

        color: 0x162c53,

        transparent: true,

        opacity: 0.62,

        side: THREE.DoubleSide,

        depthWrite: false
      });

    const outlineMaterial =
      new THREE.LineBasicMaterial({

        color: 0x4e8ba9,

        transparent: true,

        opacity: 0.83
      });

    // La silueta permanece fija.
    // No se recalcula durante la animación.

    for (
      const ring of
      incoming.contornos_jalisco || []
    ) {

      if (ring.length < 4) {
        continue;
      }

      const shape = new THREE.Shape();

      shape.moveTo(
        ring[0][0],
        -ring[0][1]
      );

      for (
        let i = 1;
        i < ring.length;
        i++
      ) {

        shape.lineTo(
          ring[i][0],
          -ring[i][1]
        );
      }

      const fill = new THREE.Mesh(

        new THREE.ShapeGeometry(shape),

        fillMaterial
      );

      fill.rotation.x = -Math.PI / 2;

      fill.position.y = -0.065;

      scene.add(fill);

      const puntos = ring.map(
        ([x, z]) =>
          new THREE.Vector3(
            x,
            -0.06,
            z
          )
      );

      const outline = new THREE.LineLoop(

        new THREE.BufferGeometry()
          .setFromPoints(puntos),

        outlineMaterial
      );

      scene.add(outline);
    }

    // ========================================
    // 11. CREAR LOS 125 NODOS
    // ========================================

    const sphere = new THREE.SphereGeometry(
      0.042,
      9,
      7
    );

    const nodeMaterial =
      new THREE.MeshBasicMaterial();

    pointsMesh = new THREE.InstancedMesh(
      sphere,
      nodeMaterial,
      125
    );

    pointsMesh.instanceMatrix.setUsage(
      THREE.DynamicDrawUsage
    );

    pointsMesh.frustumCulled = false;

    scene.add(pointsMesh);

    // ========================================
    // 12. CREAR LAS 304 ARISTAS
    // ========================================

    const edgesBuffer =
      new THREE.BufferGeometry();

    edgesAttribute =
      new THREE.BufferAttribute(

        new Float32Array(
          304 * 2 * 3
        ),

        3
      );

    edgesAttribute.setUsage(
      THREE.DynamicDrawUsage
    );

    edgesBuffer.setAttribute(
      "position",
      edgesAttribute
    );

    edgesMesh = new THREE.LineSegments(

      edgesBuffer,

      new THREE.LineBasicMaterial({

        color: 0xaac0ef,

        transparent: true,

        opacity: 0.53
      })
    );

    edgesMesh.frustumCulled = false;

    scene.add(edgesMesh);

    // ========================================
    // 13. NODO SELECCIONADO
    // ========================================

    selectedMesh = new THREE.Mesh(

      new THREE.SphereGeometry(
        0.074,
        12,
        9
      ),

      new THREE.MeshBasicMaterial({
        color: 0xffffff
      })
    );

    selectedMesh.visible = false;

    scene.add(selectedMesh);

    // ========================================
    // 14. RESERVAR MEMORIA DE POSICIONES
    // ========================================

    currentPositions = new Float32Array(
      125 * 3
    );

    updateColors();

    updatePositions(0);

    // ========================================
    // 15. SELECCIONAR NODO CON MOUSE
    // ========================================

    const raycaster = new THREE.Raycaster();

    const pointer = new THREE.Vector2();

    let down = null;

    renderer.domElement.addEventListener(
      "pointerdown",
      event => {

        down = [
          event.clientX,
          event.clientY
        ];
      }
    );

    renderer.domElement.addEventListener(
      "pointerup",
      event => {

        const inicio = down;
        down = null;

        if (!inicio) {
          return;
        }

        const distancia = Math.hypot(

          event.clientX - inicio[0],

          event.clientY - inicio[1]
        );

        // Evitar seleccionar mientras
        // el usuario rota la cámara.

        if (distancia > 7) {
          return;
        }

        const bounds =
          renderer.domElement
            .getBoundingClientRect();

        pointer.set(

          (
            event.clientX - bounds.left
          ) / bounds.width * 2 - 1,

          -(
            event.clientY - bounds.top
          ) / bounds.height * 2 + 1
        );

        raycaster.setFromCamera(
          pointer,
          camera
        );

        const hit = raycaster.intersectObject(
          pointsMesh,
          false
        )[0];

        if (
          hit &&
          Number.isInteger(hit.instanceId)
        ) {

          const node =
            data.nodos[hit.instanceId];

          municipio.value = node.id;

          municipio.dispatchEvent(
            new Event(
              "change",
              {
                bubbles: true
              }
            )
          );

          selectNode();
        }
      }
    );

    // ========================================
    // 16. AJUSTAR TAMAÑO DE LA ESCENA
    // ========================================

    function resize() {

      if (panel.hidden) {
        return;
      }

      const w = Math.max(
        300,
        canvasHost.clientWidth
      );

      const h = Math.max(
        300,
        canvasHost.clientHeight
      );

      renderer.setSize(
        w,
        h,
        false
      );

      camera.aspect = w / h;

      camera.updateProjectionMatrix();

      renderOnce();
    }

    resizeObserver = new ResizeObserver(
      resize
    );

    resizeObserver.observe(
      canvasHost
    );

    initialized = true;

    resize();

    status(
      "WebGL activo · 125 nodos · " +
      "304 aristas · sin Plotly."
    );

  })().catch(error => {

    preparing = null;

    throw error;
  });

  return preparing;
}


// ============================================
// 17. OBJETO AUXILIAR PARA LOS NODOS
// ============================================

const dummy = new THREE.Object3D();


// ============================================
// 18. ACTUALIZAR POSICIONES
// ============================================

function updatePositions(t) {

  $("papRange").value = String(t);

  $("papValue").textContent =
    t.toFixed(2);

  // Interpolación:
  // P(t) = (1-t)G + tS

  for (let i = 0; i < 125; i++) {

    const node = data.nodos[i];

    for (let k = 0; k < 3; k++) {

      currentPositions[3 * i + k] =

        node.geo[k] * (1 - t)

        + node.espectral[k] * t;
    }

    dummy.position.set(

      currentPositions[3 * i],

      currentPositions[3 * i + 1],

      currentPositions[3 * i + 2]
    );

    dummy.updateMatrix();

    pointsMesh.setMatrixAt(
      i,
      dummy.matrix
    );
  }

  // Solo actualizar el buffer existente.

  pointsMesh.instanceMatrix.needsUpdate = true;

  pointsMesh.computeBoundingSphere();

  // Actualizar las posiciones de las aristas.

  for (let i = 0; i < 304; i++) {

    const [a, b] = data.aristas[i];

    for (let k = 0; k < 3; k++) {

      edgesAttribute.array[
        i * 6 + k
      ] = currentPositions[
        a * 3 + k
      ];

      edgesAttribute.array[
        i * 6 + 3 + k
      ] = currentPositions[
        b * 3 + k
      ];
    }
  }

  edgesAttribute.needsUpdate = true;

  selectNode();

  renderOnce();
}


// ============================================
// 19. COLOREAR NODOS POR INDICADOR
// ============================================

function updateColors() {

  if (!data || !pointsMesh) {
    return;
  }

  const metric = $("papMetric").value;

  const raw = data.nodos.map(
    node => node.valores?.[metric]
  );

  const values = raw.map(
    value =>
      value == null
        ? null
        : Math.log1p(Number(value))
  );

  const max = Math.max(

    0.001,

    ...values.filter(
      v =>
        v !== null &&
        Number.isFinite(v)
    )
  );

  const cold = new THREE.Color(
    0x6382d9
  );

  const hot = new THREE.Color(
    0xf7b65a
  );

  for (let i = 0; i < 125; i++) {

    const value = values[i];

    let color;

    if (
      value === null ||
      !Number.isFinite(value)
    ) {

      // Sin dato.
      color = new THREE.Color(
        0x6b7280
      );

    } else {

      // Gradiente según el indicador.
      color = cold.clone().lerp(

        hot,

        Math.min(
          1,
          value / max
        )
      );
    }

    pointsMesh.setColorAt(
      i,
      color
    );
  }

  pointsMesh.instanceColor.needsUpdate = true;

  renderOnce();
}


// ============================================
// 20. SINCRONIZAR MUNICIPIO
// ============================================

function selectNode() {

  if (!data || !currentPositions) {
    return;
  }

  const index = data.nodos.findIndex(
    node =>
      node.id === municipio.value
  );

  selectedMesh.visible = index >= 0;

  if (index < 0) {

    $("papSelection").textContent =
      "Selecciona un municipio haciendo clic.";

  } else {

    const node = data.nodos[index];

    selectedMesh.position.set(

      currentPositions[3 * index],

      currentPositions[3 * index + 1],

      currentPositions[3 * index + 2]
    );

    const label = value =>

      value == null
        ? "Sin dato"
        : Number(value).toLocaleString(
            "es-MX",
            {
              maximumFractionDigits: 2
            }
          );

    $("papSelection").textContent =

      `${node.nombre} · `

      + `DENUE/km²: ${
          label(node.valores.denue)
        } · `

      + `ATUS: ${
          label(node.valores.atus)
        } · `

      + `Siniestralimap: ${
          label(node.valores.siniestralimap)
        }`;
  }

  renderOnce();
}


// ============================================
// 21. DETENER ANIMACIÓN
// ============================================

function stop() {

  if (rafAnimation) {

    cancelAnimationFrame(
      rafAnimation
    );
  }

  rafAnimation = 0;

  $("papPlay").textContent =
    "▶ Animar";
}


// ============================================
// 22. ANIMAR MEDIANTE requestAnimationFrame
// ============================================

function play() {

  if (!initialized || rafAnimation) {
    return;
  }

  let first = null;

  let startT = Number(
    $("papRange").value
  );

  if (startT >= 1) {

    startT = 0;

    updatePositions(0);
  }

  fpsFrames = 0;
  fpsStart = 0;

  $("papPlay").textContent =
    "⏸ Pausar";

  const duration = 2600;

  function step(now) {

    if (!first) {
      first = now;
    }

    if (!fpsStart) {
      fpsStart = now;
    }

    const t = Math.min(

      1,

      startT +
        (now - first) / duration
        * (1 - startT)
    );

    updatePositions(t);

    fpsFrames++;

    if (now - fpsStart >= 700) {

      const fps = (
        fpsFrames * 1000 /
        (now - fpsStart)
      ).toFixed(0);

      status(
        `WebGL · ${fps} cuadros/s ` +
        "aproximados del bucle"
      );

      fpsStart = now;
      fpsFrames = 0;
    }

    if (t >= 1 || panel.hidden) {

      stop();

      return;
    }

    rafAnimation = requestAnimationFrame(
      step
    );
  }

  rafAnimation = requestAnimationFrame(
    step
  );
}


// ============================================
// 23. ABRIR PAPIROFLEXIA
// ============================================

launch.addEventListener(
  "click",
  async () => {

    const panelCientifico =
      document.querySelector(
        ".ci-panel"
      );

    if (panelCientifico) {

      panelCientifico.hidden = true;
    }

    panel.hidden = false;

    try {

      await prepare();
        selectNode();

      const host = $("papView");

      renderer.setSize(

        host.clientWidth,

        host.clientHeight,

        false
      );

      camera.aspect =

        host.clientWidth /

        Math.max(
          1,
          host.clientHeight
        );

      camera.updateProjectionMatrix();

      renderOnce();

    } catch (error) {

      status(
        `Error: ${error.message}`
      );

      console.error(error);
    }
  }
);


// ============================================
// 24. CERRAR PAPIROFLEXIA
// ============================================

$("papClose").addEventListener(
  "click",
  () => {

    stop();

    panel.hidden = true;
  }
);


// ============================================
// 25. CONTROLES
// ============================================

$("papMetric").addEventListener(
  "change",
  updateColors
);

$("papRange").addEventListener(
  "input",
  () => {

    stop();

    if (initialized) {

      updatePositions(
        Number(
          $("papRange").value
        )
      );
    }
  }
);

$("papPlay").addEventListener(
  "click",
  () => {

    if (rafAnimation) {
      stop();
    } else {
      play();
    }
  }
);

municipio.addEventListener(
  "change",
  selectNode
);
