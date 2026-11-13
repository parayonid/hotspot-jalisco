
/*
 HOTSPOT | ETAPA 21.4

 Papiroflexia espectral urbana con GPU.

 447 nodos del grafo de 2025.
 1,034 aristas de vecindad.

 347 nodos se transforman al embedding.
 100 nodos permanecen geográficos.

 No se recalcula el laplaciano.
 No se modifican datos científicos.
*/

import * as THREE from "three";

import {
  OrbitControls
} from "three/addons/controls/OrbitControls.js";


// ==========================================
// 1. RECUPERAR ELEMENTOS
// ==========================================

const $ = id =>
  document.getElementById(id);

const panel = $("spectralPanel");

const host = $("threeHost");


// ==========================================
// 2. VARIABLES
// ==========================================

let data = null;

let scene;
let camera;
let renderer;
let orbit;

let mesh;
let lines;
let attribute;
let floorTiles;
let highlight;

let positions;
let nodeIndex;

let selection = "";

let requestFrame = 0;

let playing = false;

let animFrame = 0;

let startTime = 0;

let fromT = 0;

const dummy = new THREE.Object3D();


// ==========================================
// 3. UTILIDADES
// ==========================================

const numeric = n =>
  Number(n).toLocaleString("es-MX");

const updateStatus = message => {

  $("threeStatus").textContent = message;
};


// ==========================================
// 4. RENDERIZAR
// ==========================================

function draw() {

  if (
    !renderer ||
    panel.hidden
  ) {
    return;
  }

  renderer.render(
    scene,
    camera
  );
}


function requestDraw() {

  if (
    requestFrame ||
    panel.hidden ||
    !renderer
  ) {
    return;
  }

  requestFrame = requestAnimationFrame(
    () => {

      requestFrame = 0;

      draw();
    }
  );
}


// ==========================================
// 5. SINCRONIZAR SELECCIÓN
// ==========================================

function updateSelection() {

  if (
    !highlight ||
    !data
  ) {
    return;
  }

  const i = nodeIndex.get(
    selection
  );

  highlight.visible =
    i !== undefined;

  if (i !== undefined) {

    highlight.position.set(

      positions[i * 3],

      positions[i * 3 + 1],

      positions[i * 3 + 2]
    );

    const n = data.nodos[i];

    $("threeSelected").textContent =

      `${n.id} · ` +

      `${numeric(n.conteo_2025)} ` +

      "siniestros registrados · " +

      (
        n.en_componente_mayor
          ? "con embedding"
          : "sin embedding espectral"
      );

  } else {

    $("threeSelected").textContent =
      "Haz clic en un nodo para " +
      "resaltarlo también sobre el mapa.";
  }
}


// ==========================================
// 6. ACTUALIZAR POSICIONES DEL GRAFO
// ==========================================

function updatePositions(t) {

  $("tValue").textContent =
    t.toFixed(2);

  // Transformación:
  //
  // P(t) = (1-t)G + tS
  //
  // Para los nodos sin embedding:
  // S = G, por lo que no se mueven.

  for (
    let i = 0;
    i < data.nodos.length;
    i++
  ) {

    const n = data.nodos[i];

    const end =
      n.espectral_xyz ??
      n.geo_xyz;

    for (let j = 0; j < 3; j++) {

      positions[i * 3 + j] =

        n.geo_xyz[j] * (1 - t)

        + end[j] * t;
    }

    dummy.position.set(

      positions[i * 3],

      positions[i * 3 + 1],

      positions[i * 3 + 2]
    );

    dummy.updateMatrix();

    mesh.setMatrixAt(
      i,
      dummy.matrix
    );
  }

  // Actualizar instancias existentes.

  mesh.instanceMatrix.needsUpdate = true;

  // ========================================
  // 7. ACTUALIZAR ARISTAS EXISTENTES
  // ========================================

  for (
    let k = 0;
    k < data.aristas.length;
    k++
  ) {

    const a = nodeIndex.get(
      data.aristas[k].source
    );

    const b = nodeIndex.get(
      data.aristas[k].target
    );

    for (let j = 0; j < 3; j++) {

      attribute.array[
        k * 6 + j
      ] = positions[
        a * 3 + j
      ];

      attribute.array[
        k * 6 + 3 + j
      ] = positions[
        b * 3 + j
      ];
    }
  }

  attribute.needsUpdate = true;

  updateSelection();

  // Durante la animación se dibuja
  // dentro del propio bucle.

  if (!playing) {

    requestDraw();
  }
}


// ==========================================
// 8. AJUSTAR EL LIENZO
// ==========================================

function resize() {

  if (
    !renderer ||
    panel.hidden
  ) {
    return;
  }

  const width = Math.max(
    200,
    host.clientWidth
  );

  const height = Math.max(
    240,
    host.clientHeight
  );

  renderer.setSize(
    width,
    height,
    false
  );

  camera.aspect = width / height;

  camera.updateProjectionMatrix();

  requestDraw();
}


// ==========================================
// 9. PREPARAR ESCENA
// ==========================================

async function prepare() {

  if (data) {
    return;
  }

  updateStatus(
    "Cargando 447 nodos y preparando WebGL..."
  );

  const response = await fetch(
    "./datos/21_embedding_siniestros_2025.json"
  );

  if (!response.ok) {

    throw new Error(
      `Archivo de embedding: HTTP ${response.status}`
    );
  }

  const incoming = await response.json();

  // ========================================
  // 10. VALIDAR EL JSON
  // ========================================

  if (

    incoming.nodos?.length !== 447 ||

    incoming.aristas?.length !== 1034 ||

    incoming.nodos.filter(
      n => n.espectral_xyz !== null
    ).length !== 347

  ) {

    throw new Error(
      "El archivo no coincide con " +
      "los resultados de la Etapa 21.3."
    );
  }

  const index = new Map(

    incoming.nodos.map(
      (n, i) => [
        n.id,
        i
      ]
    )
  );

  if (

    index.size !== 447 ||

    incoming.aristas.some(
      e =>
        !index.has(e.source) ||
        !index.has(e.target)
    )

  ) {

    throw new Error(
      "Identificadores duplicados " +
      "o aristas desconocidas."
    );
  }

  if (

    incoming.nodos.some(
      n =>

        !Array.isArray(
          n.geo_xyz
        ) ||

        n.geo_xyz.length !== 3 ||

        (
          n.espectral_xyz !== null &&

          (
            !Array.isArray(
              n.espectral_xyz
            ) ||

            n.espectral_xyz.length !== 3
          )
        )
    )

  ) {

    throw new Error(
      "Coordenadas inválidas en el embedding."
    );
  }

  nodeIndex = index;

  // ========================================
  // 11. CREAR RENDERIZADOR WEBGL
  // ========================================

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
    0x0b1120
  );

  host.appendChild(
    renderer.domElement
  );

  // ========================================
  // 12. CONFIGURAR ESCENA Y CÁMARA
  // ========================================

  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(

    43,

    1,

    0.1,

    80
  );

  camera.position.set(
    4.2,
    5.5,
    6.4
  );

  orbit = new OrbitControls(

    camera,

    renderer.domElement
  );

  orbit.target.set(
    0,
    0.35,
    0
  );

  orbit.enableDamping = false;

  orbit.minDistance = 1.8;

  orbit.maxDistance = 18;

  orbit.addEventListener(
    "change",
    requestDraw
  );

  // ========================================
  // 13. PREPARAR BASE GEOGRÁFICA
  // ========================================

  const geo = incoming.nodos.map(
    n => n.geo_xyz
  );

  const sideNeighbors =
    incoming.aristas

      .map(e => {

        const a = geo[
          index.get(e.source)
        ];

        const b = geo[
          index.get(e.target)
        ];

        return Math.hypot(

          a[0] - b[0],

          a[2] - b[2]
        );
      })

      .filter(
        distance => distance > 1e-7
      );

  const cellSide =
    Math.min(...sideNeighbors) * 0.95;

  const tileGeom = new THREE.PlaneGeometry(

    cellSide,

    cellSide
  );

  tileGeom.rotateX(
    -Math.PI / 2
  );

  // ========================================
  // 14. DIBUJAR CELDAS DEL SUELO
  // ========================================

  floorTiles = new THREE.InstancedMesh(

    tileGeom,

    new THREE.MeshBasicMaterial({

      transparent: true,

      opacity: 0.17,

      depthWrite: false,

      side: THREE.DoubleSide
    }),

    447
  );

  floorTiles.frustumCulled = false;

  const tileColor = new THREE.Color();

  for (let i = 0; i < 447; i++) {

    const n = incoming.nodos[i];

    dummy.position.set(

      n.geo_xyz[0],

      -0.04,

      n.geo_xyz[2]
    );

    dummy.updateMatrix();

    floorTiles.setMatrixAt(
      i,
      dummy.matrix
    );

    tileColor.setHex(

      n.alta_concentracion_2025

        ? 0xf7b65a

        : 0x526c95
    );

    floorTiles.setColorAt(
      i,
      tileColor
    );
  }

  scene.add(floorTiles);

  // ========================================
  // 15. CREAR LOS 447 VÉRTICES
  // ========================================

  const sphere = new THREE.SphereGeometry(

    0.027,

    8,

    6
  );

  mesh = new THREE.InstancedMesh(

    sphere,

    new THREE.MeshBasicMaterial(),

    447
  );

  mesh.instanceMatrix.setUsage(
    THREE.DynamicDrawUsage
  );

  mesh.frustumCulled = false;

  const normalColor = new THREE.Color(
    0x76cfbc
  );

  const focusColor = new THREE.Color(
    0xffaf55
  );

  const otherColor = new THREE.Color(
    0x7c879a
  );

  for (let i = 0; i < 447; i++) {

    const n = incoming.nodos[i];

    mesh.setColorAt(

      i,

      n.en_componente_mayor

        ? (
            n.alta_concentracion_2025
              ? focusColor
              : normalColor
          )

        : otherColor
    );
  }

  scene.add(mesh);

  // ========================================
  // 16. CREAR LAS 1,034 ARISTAS
  // ========================================

  const wireGeometry =
    new THREE.BufferGeometry();

  attribute = new THREE.BufferAttribute(

    new Float32Array(
      1034 * 6
    ),

    3
  );

  attribute.setUsage(
    THREE.DynamicDrawUsage
  );

  wireGeometry.setAttribute(

    "position",

    attribute
  );

  lines = new THREE.LineSegments(

    wireGeometry,

    new THREE.LineBasicMaterial({

      color: 0xa6b9e6,

      transparent: true,

      opacity: 0.45
    })
  );

  lines.frustumCulled = false;

  scene.add(lines);

  // ========================================
  // 17. MARCADOR SELECCIONADO
  // ========================================

  highlight = new THREE.Mesh(

    new THREE.SphereGeometry(

      0.049,

      10,

      8
    ),

    new THREE.MeshBasicMaterial({

      color: 0xffffff
    })
  );

  highlight.visible = false;

  scene.add(highlight);

  // ========================================
  // 18. RESERVAR POSICIONES
  // ========================================

  positions = new Float32Array(
    447 * 3
  );

  data = incoming;

  updatePositions(

    Number(
      $("tRange").value
    )
  );

  // ========================================
  // 19. SELECCIONAR NODO CON EL MOUSE
  // ========================================

  let down = null;

  const raycaster = new THREE.Raycaster();

  const mouse = new THREE.Vector2();

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

      if (

        !down ||

        Math.hypot(

          event.clientX - down[0],

          event.clientY - down[1]

        ) > 6

      ) {

        down = null;

        return;
      }

      down = null;

      const rect = renderer.domElement
        .getBoundingClientRect();

      mouse.set(

        (
          (event.clientX - rect.left)
          / rect.width
        ) * 2 - 1,

        1 -
        (
          (event.clientY - rect.top)
          / rect.height
        ) * 2
      );

      raycaster.setFromCamera(

        mouse,

        camera
      );

      const hits = raycaster.intersectObject(

        mesh,

        false
      );

      if (

        !hits.length ||

        hits[0].instanceId == null

      ) {
        return;
      }

      selection = data.nodos[
        hits[0].instanceId
      ].id;

      updateSelection();

      requestDraw();

      // Sincronizar el mapa territorial.

      document.dispatchEvent(

        new CustomEvent(

          "hotspot:seleccionar-desde-3d",

          {
            detail: {
              id: selection
            }
          }
        )
      );
    }
  );

  // ========================================
  // 20. DETECTAR CAMBIOS DE TAMAÑO
  // ========================================

  new ResizeObserver(
    resize
  ).observe(host);

  resize();

  updateStatus(
    "WebGL listo · 447 celdas · " +
    "1,034 aristas · " +
    "347 nodos espectrales"
  );
}


// ==========================================
// 21. DETENER ANIMACIÓN
// ==========================================

function stop() {

  playing = false;

  if (animFrame) {

    cancelAnimationFrame(
      animFrame
    );
  }

  animFrame = 0;

  $("play3d").textContent =
    "▶ Animar";
}


// ==========================================
// 22. REPRODUCIR PAPIROFLEXIA
// ==========================================

function play() {

  if (
    !data ||
    playing
  ) {
    return;
  }

  playing = true;

  fromT = Number(
    $("tRange").value
  );

  if (fromT >= 1) {

    fromT = 0;

    $("tRange").value = "0";

    updatePositions(0);
  }

  $("play3d").textContent =
    "⏸ Pausar";

  startTime = 0;

  const duration = 3500;

  function frame(now) {

    if (
      !playing ||
      panel.hidden
    ) {

      stop();

      return;
    }

    if (!startTime) {

      startTime = now;
    }

    const t = Math.min(

      1,

      fromT +

      (1 - fromT) *

      (now - startTime) / duration
    );

    $("tRange").value = String(t);

    updatePositions(t);

    draw();

    if (t < 1) {

      animFrame = requestAnimationFrame(
        frame
      );

    } else {

      stop();
    }
  }

  animFrame = requestAnimationFrame(
    frame
  );
}


// ==========================================
// 23. ABRIR VISTA 3D
// ==========================================

$("open3d").addEventListener(

  "click",

  async () => {

    panel.hidden = false;

    try {

      await prepare();

      resize();

      updateSelection();

      requestDraw();

    } catch (error) {

      updateStatus(
        "Error: " + error.message
      );

      console.error(error);
    }
  }
);


// ==========================================
// 24. CERRAR VISTA 3D
// ==========================================

$("close3d").addEventListener(

  "click",

  () => {

    stop();

    panel.hidden = true;
  }
);


// ==========================================
// 25. BOTÓN ANIMAR / PAUSAR
// ==========================================

$("play3d").addEventListener(

  "click",

  () => {

    if (playing) {

      stop();

    } else {

      play();
    }
  }
);


// ==========================================
// 26. CONTROL DESLIZANTE
// ==========================================

$("tRange").addEventListener(

  "input",

  () => {

    stop();

    if (data) {

      updatePositions(

        Number(
          $("tRange").value
        )
      );
    }

    $("tValue").textContent =

      Number(
        $("tRange").value
      ).toFixed(2);
  }
);


// ==========================================
// 27. SELECCIÓN DESDE EL MAPA 2D
// ==========================================

document.addEventListener(

  "hotspot:celda-seleccionada",

  event => {

    selection = event.detail.id;

    if (data) {

      updateSelection();

      requestDraw();
    }
  }
);
