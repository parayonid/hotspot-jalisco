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
