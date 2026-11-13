
/*
 HOTSPOT 22.2

 Capa cartografica estatica para la
 papiroflexia urbana.

 El fondo no modifica las coordenadas
 ni los resultados espectrales.
*/

export async function cargarContextoUrbano({
  THREE,
  scene,
  redibujar
}) {

  const status =
    document.getElementById("22EstadoMapa");

  const toggleMapa =
    document.getElementById("22MostrarMapa");

  const toggleLimite =
    document.getElementById("22MostrarLimite");

  if (
    !scene ||
    !toggleMapa ||
    !toggleLimite
  ) {
    return;
  }

  // ========================================
  // 1. CARGAR CONTEXTO
  // ========================================

  const response = await fetch(
    "./datos/22_2_contexto_urbano.json"
  );

  if (!response.ok) {

    throw new Error(
      `Contexto urbano: HTTP ${response.status}`
    );
  }

  const data = await response.json();

  const tiles = data.teselas;

  if (
    !Array.isArray(tiles) ||
    tiles.length > 32 ||
    !Array.isArray(data.contornos_guadalajara)
  ) {

    throw new Error(
      "Contexto cartografico invalido"
    );
  }

  // ========================================
  // 2. CREAR GRUPOS THREE.JS
  // ========================================

  const mapa = new THREE.Group();

  const limite = new THREE.Group();

  scene.add(mapa);
  scene.add(limite);

  mapa.visible = toggleMapa.checked;
  limite.visible = toggleLimite.checked;

  // ========================================
  // 3. CONTROLES DE VISIBILIDAD
  // ========================================

  toggleMapa.addEventListener(
    "change",
    () => {

      mapa.visible = toggleMapa.checked;

      redibujar();
    }
  );

  toggleLimite.addEventListener(
    "change",
    () => {

      limite.visible = toggleLimite.checked;

      redibujar();
    }
  );

  // ========================================
  // 4. LIMITE DE GUADALAJARA
  // ========================================

  const lineMat =
    new THREE.LineBasicMaterial({

      color: 0xffd78c,

      transparent: true,

      opacity: 0.97
    });

  for (
    const anillo of
    data.contornos_guadalajara
  ) {

    if (
      !Array.isArray(anillo) ||
      anillo.length < 3
    ) {
      continue;
    }

    const pts = anillo.map(
      ([x, z]) =>
        new THREE.Vector3(
          x,
          -0.012,
          z
        )
    );

    limite.add(

      new THREE.LineLoop(

        new THREE.BufferGeometry()
          .setFromPoints(pts),

        lineMat
      )
    );
  }

  redibujar();

  // ========================================
  // 5. CARGAR MAPA DE CALLES
  // ========================================

  const loader =
    new THREE.TextureLoader();

  let ok = 0;
  let error = 0;

  if (status) {

    status.textContent =
      `Límite local listo · cargando hasta ` +
      `${tiles.length} teselas visibles...`;
  }

  for (const tile of tiles) {

    if (
      tile.vertices?.length !== 4
    ) {
      continue;
    }

    const pos = [];

    for (
      const [x, z] of
      tile.vertices
    ) {

      pos.push(
        x,
        -0.078,
        z
      );
    }

    // ======================================
    // 6. GEOMETRIA Y COORDENADAS UV
    // ======================================

    // Orden:
    // Suroeste, sureste, noreste, noroeste.

    const geo =
      new THREE.BufferGeometry();

    geo.setAttribute(

      "position",

      new THREE.Float32BufferAttribute(
        pos,
        3
      )
    );

    geo.setAttribute(

      "uv",

      new THREE.Float32BufferAttribute(

        [
          0, 0,
          1, 0,
          1, 1,
          0, 1
        ],

        2
      )
    );

    geo.setIndex(
      [
        0, 1, 2,
        0, 2, 3
      ]
    );

    // ======================================
    // 7. MATERIAL DEL MAPA
    // ======================================

    const material =
      new THREE.MeshBasicMaterial({

        color: 0xb8c1e8,

        transparent: true,

        opacity: 0.53,

        depthWrite: false,

        side: THREE.DoubleSide
      });

    const mesh = new THREE.Mesh(
      geo,
      material
    );

    mapa.add(mesh);

    // ======================================
    // 8. SOLICITAR TESELA
    // ======================================

    const url =
      `https://tile.openstreetmap.org/` +
      `${tile.z}/${tile.x}/${tile.y}.png`;

    loader.load(

      url,

      texture => {

        texture.colorSpace =
          THREE.SRGBColorSpace;

        texture.anisotropy = 1;

        material.map = texture;

        material.needsUpdate = true;

        ok += 1;

        if (status) {

          status.textContent =
            `Calles: ${ok}/${tiles.length} ` +
            `teselas · ${error} fallidas`;
        }

        redibujar();
      },

      undefined,

      () => {

        error += 1;

        if (status) {

          status.textContent =
            `Mapa incompleto: ` +
            `${ok} teselas cargadas, ` +
            `${error} fallidas`;
        }
      }
    );
  }
}
