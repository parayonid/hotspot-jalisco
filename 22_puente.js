
/*
 HOTSPOT | ETAPA 22.1

 Adaptador de comunicación
 entre los visores y la aplicación.

 Conserva:
   - Municipio seleccionado
   - Indicador municipal
   - Año
   - Visibilidad de siniestros
   - Celda urbana seleccionada

 Solo acepta mensajes del mismo origen.
*/

(() => {

  "use strict";

  // ======================================
  // 1. IDENTIFICAR VISTA
  // ======================================

  const view =
    document.currentScript?.dataset.hotspotView;

  if (
    !["municipal", "urbano"].includes(view)
    ||
    window === window.parent
  ) {
    return;
  }

  const $ = id =>
    document.getElementById(id);

  // ======================================
  // 2. ENVIAR MENSAJE A APP PRINCIPAL
  // ======================================

  const send = (
    type,
    detail = {}
  ) => {

    window.parent.postMessage(

      {
        app: "hotspot22",
        type,
        view,
        detail
      },

      location.origin
    );
  };

  // ======================================
  // 3. LEER ESTADO MUNICIPAL
  // ======================================

  function readMunicipal() {

    return {

      municipio:
        $("municipio")?.value ?? "",

      indicador:
        $("indicador")?.value ??
        "denue_mayo_2025",

      anio:
        $("anio")?.value ?? "2025",

      puntos:
        Boolean(
          $("mostrarSiniestros")?.checked
        )
    };
  }

  // ======================================
  // 4. PUBLICAR CAMBIOS MUNICIPALES
  // ======================================

  function reportMunicipal() {

    if (view === "municipal") {

      send(
        "STATE",
        readMunicipal()
      );
    }
  }

  if (view === "municipal") {

    document.addEventListener(
      "change",
      event => {

        if (
          [
            "municipio",
            "indicador",
            "anio",
            "mostrarSiniestros"
          ].includes(event.target?.id)
        ) {

          reportMunicipal();
        }
      }
    );

    // El visor municipal puede cambiar
    // municipio.value al hacer clic
    // sobre un polígono sin emitir change.

    $("map")?.addEventListener(

      "click",

      () => {

        requestAnimationFrame(
          reportMunicipal
        );
      }
    );

  } else {

    // ====================================
    // 5. SELECCION URBANA
    // ====================================

    document.addEventListener(

      "hotspot:celda-seleccionada",

      event => {

        const id =
          event.detail?.id;

        if (typeof id === "string") {

          send(
            "STATE",
            {
              celda: id
            }
          );
        }
      }
    );
  }

  // ======================================
  // 6. DATOS PENDIENTES DE RESTAURAR
  // ======================================

  const pending = new Map();

  let action = "";

  let preferredCell = "";

  let cellRestored = false;

  // ======================================
  // 7. RESTAURAR SELECTOR
  // ======================================

  function selectValue(
    id,
    value
  ) {

    const element = $(id);

    if (!element) {
      return false;
    }

    const found = Array
      .from(element.options)
      .some(
        option =>
          option.value === String(value)
      );

    if (!found) {
      return false;
    }

    if (
      element.value !== String(value)
    ) {

      element.value =
        String(value);

      element.dispatchEvent(

        new Event(
          "change",
          {
            bubbles: true
          }
        )
      );
    }

    return true;
  }

  // ======================================
  // 8. APLICAR ESTADO RESTAURADO
  // ======================================

  function applyRestore() {

    if (view === "municipal") {

      // Restaurar filtros existentes.

      for (
        const [id, value] of pending
      ) {

        if (
          id === "mostrarSiniestros"
        ) {

          const input = $(id);

          if (input) {

            if (
              input.checked !==
              Boolean(value)
            ) {

              input.checked =
                Boolean(value);

              input.dispatchEvent(

                new Event(
                  "change",
                  {
                    bubbles: true
                  }
                )
              );
            }

            pending.delete(id);
          }

        } else if (
          selectValue(id, value)
        ) {

          pending.delete(id);
        }
      }

    } else if (
      preferredCell &&
      !cellRestored
    ) {

      // Esperar la carga del mapa urbano.

      if (
        (
          $("status")?.textContent ||
          ""
        ).includes("Selecciona una celda")
      ) {

        cellRestored = true;

        document.dispatchEvent(

          new CustomEvent(

            "hotspot:seleccionar-desde-3d",

            {
              detail: {
                id: preferredCell
              }
            }
          )
        );
      }
    }

    // ====================================
    // 9. ABRIR MODULO SOLICITADO
    // ====================================

    if (action) {

      const selectors = {

        municipal3d: ".pap-launch",

        urbano3d: "#open3d",

        ciencia: ".ci-launch"
      };

      const button =
        document.querySelector(
          selectors[action]
        );

      if (button) {

        // Evitar doble apertura.
        action = "";

        button.click();
      }
    }
  }

  // ======================================
  // 10. DETECTAR ELEMENTOS ASINCRONOS
  // ======================================

  // Algunos selectores se llenan después
  // de que el HTML termina de cargar.
  // MutationObserver detecta sus cambios.

  const observer =
    new MutationObserver(
      applyRestore
    );

  observer.observe(
    document.body,

    {
      childList: true,

      subtree: true,

      characterData: true
    }
  );

  // ======================================
  // 11. RECIBIR ESTADO GLOBAL
  // ======================================

  window.addEventListener(

    "message",

    event => {

      if (
        event.source !== window.parent
        ||
        event.origin !== location.origin
      ) {
        return;
      }

      const msg =
        event.data;

      if (
        msg?.app !== "hotspot22" ||
        msg.type !== "RESTORE" ||
        msg.view !== view
      ) {
        return;
      }

      const state =
        msg.detail || {};

      // ==================================
      // 12. RESTAURAR DATOS MUNICIPALES
      // ==================================

      if (view === "municipal") {

        if (
          state.indicador != null
        ) {

          pending.set(
            "indicador",
            state.indicador
          );
        }

        if (
          state.anio != null
        ) {

          pending.set(
            "anio",
            state.anio
          );
        }

        if (
          state.municipio
        ) {

          pending.set(
            "municipio",
            state.municipio
          );
        }

        if (
          typeof state.puntos ===
          "boolean"
        ) {

          pending.set(
            "mostrarSiniestros",
            state.puntos
          );
        }

      } else if (
        state.celda
      ) {

        // ==================================
        // 13. RESTAURAR CELDA URBANA
        // ==================================

        preferredCell =
          String(state.celda);

        cellRestored = false;
      }

      // ==================================
      // 14. PREPARAR ACCION
      // ==================================

      const validActions =
        view === "municipal"

          ? [
              "municipal3d",
              "ciencia"
            ]

          : [
              "urbano3d"
            ];

      action = validActions.includes(
        state.action
      )

        ? state.action

        : "";

      applyRestore();
    }
  );

  // ======================================
  // 15. AVISAR QUE CARGO EL DOCUMENTO
  // ======================================

  window.addEventListener(

    "load",

    () => {

      send(
        "READY",
        {}
      );
    }
  );

})();
