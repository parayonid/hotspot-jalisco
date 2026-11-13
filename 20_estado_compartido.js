
/*
 * HOTSPOT | ETAPA 20.2
 *
 * Coordinación entre el mapa territorial
 * y la papiroflexia espectral.
 *
 * No descarga datasets ni modifica modelos.
 *
 * IMPORTANTE:
 * Mapa DENUE = establecimientos totales.
 * Grafo DENUE = establecimientos por km².
 *
 * No se sincronizan automáticamente
 * esas dos variables porque tienen
 * unidades distintas.
 */

(() => {
  "use strict";

  // ======================================
  // 1. RECUPERAR CONTROLES
  // ======================================

  const get = id =>
    document.getElementById(id);

  const mapa = get("indicador");
  const municipio = get("municipio");
  const anio = get("anio");

  if (!mapa || !municipio || !anio) {
    console.error(
      "Hotspot 20.2: faltan controles."
    );
    return;
  }

  // ======================================
  // 2. ESTADO COMPARTIDO
  // ======================================

  let estado = {
    municipio: municipio.value || "",
    indicadorMapa: mapa.value,
    indicadorEspectral:
      get("papMetric")?.value || "denue",
    anioPuntos: anio.value || "2025"
  };

  let sincronizando = false;

  // ======================================
  // 3. PUBLICAR CAMBIOS
  // ======================================

  function publicar(cambio, origen) {

    estado = {
      ...estado,
      ...cambio
    };

    document.dispatchEvent(
      new CustomEvent(
        "hotspot:estado",
        {
          detail: {
            ...estado,
            origen
          }
        }
      )
    );
  }

  // ======================================
  // 4. VARIABLES EQUIVALENTES
  // ======================================

  const mapaAEspectral = {
    atus_2025: "atus",
    siniestralimap_asignados_2025:
      "siniestralimap"
  };

  const espectralAMapa = {
    atus: "atus_2025",
    siniestralimap:
      "siniestralimap_asignados_2025"
  };

  // ======================================
  // 5. CAMBIAR SELECT SIN CREAR CICLOS
  // ======================================

  function cambiarSelect(elemento, valor) {

    if (
      !elemento ||
      elemento.value === valor
    ) {
      return;
    }

    const existe = [
      ...elemento.options
    ].some(
      opcion => opcion.value === valor
    );

    if (!existe) {
      return;
    }

    sincronizando = true;

    try {

      elemento.value = valor;

      elemento.dispatchEvent(
        new Event(
          "change",
          {
            bubbles: true
          }
        )
      );

    } finally {

      sincronizando = false;
    }
  }

  // ======================================
  // 6. ESCUCHAR CAMBIOS DE LA INTERFAZ
  // ======================================

  document.addEventListener(
    "change",
    event => {

      if (sincronizando) {
        return;
      }

      const id = event.target?.id;

      // Municipio.

      if (id === "municipio") {

        publicar(
          {
            municipio: municipio.value
          },
          "selector-municipal"
        );
      }

      // Año de puntos Siniestralimap.

      if (id === "anio") {

        publicar(
          {
            anioPuntos: anio.value
          },
          "filtro-temporal-puntos"
        );
      }

      // Indicador seleccionado en mapa.

      if (id === "indicador") {

        const proximo =
          mapaAEspectral[mapa.value];

        if (proximo) {

          cambiarSelect(
            get("papMetric"),
            proximo
          );
        }

        publicar(
          {
            indicadorMapa: mapa.value,
            indicadorEspectral:
              get("papMetric")?.value ||
              estado.indicadorEspectral
          },
          "indicador-mapa"
        );
      }

      // Indicador seleccionado en grafo.

      if (id === "papMetric") {

        const elegido =
          get("papMetric")?.value;

        const proximo =
          espectralAMapa[elegido];

        if (proximo) {

          cambiarSelect(
            mapa,
            proximo
          );
        }

        publicar(
          {
            indicadorMapa: mapa.value,
            indicadorEspectral: elegido
          },
          "indicador-espectral"
        );
      }
    }
  );

  // ======================================
  // 7. DETECTAR SELECCION EN MAPA
  // ======================================

  // El visor actual actualiza municipio.value
  // al hacer clic sobre un polígono,
  // pero no siempre emite un evento "change".

  const elementoMapa = get("map");

  elementoMapa?.addEventListener(
    "click",
    () => {

      requestAnimationFrame(() => {

        if (
          municipio.value !== estado.municipio
        ) {

          publicar(
            {
              municipio: municipio.value
            },
            "clic-mapa"
          );
        }
      });
    }
  );

  // ======================================
  // 8. ABRIR PAPIROFLEXIA
  // ======================================

  document.addEventListener(
    "click",
    event => {

      if (
        !event.target?.closest?.(
          ".pap-launch"
        )
      ) {
        return;
      }

      const elegido =
        mapaAEspectral[mapa.value];

      if (elegido) {

        cambiarSelect(
          get("papMetric"),
          elegido
        );
      }

      publicar(
        {
          municipio: municipio.value,
          indicadorMapa: mapa.value,
          indicadorEspectral:
            get("papMetric")?.value ||
            estado.indicadorEspectral
        },
        "abrir-papiroflexia"
      );
    }
  );

  // ======================================
  // 9. CONSULTAR ESTADO DESDE CONSOLA
  // ======================================

  window.HotspotEstado = Object.freeze({

    obtener: () =>
      Object.freeze({
        ...estado
      })
  });

  publicar({}, "inicio");

})();
