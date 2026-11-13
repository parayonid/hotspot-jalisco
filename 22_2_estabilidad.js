
/*
 HOTSPOT 22.2

 Estabilidad descriptiva de concentraciones
 sobre el mapa urbano 2D.

 Fuente:
   21_estabilidad_zonas_2025.geojson

 No recalcula inferencia ni riesgo vial.
*/

(() => {

  "use strict";

  const $ = id =>
    document.getElementById(id);

  const chk =
    $("22MostrarEstabilidad");

  const threshold =
    $("22Umbral");

  const description =
    $("22ResumenEstabilidad");

  if (
    !chk ||
    !threshold ||
    !description
  ) {
    return;
  }

  let map = null;

  let features = [];

  let metricReady = false;

  // ========================================
  // 1. FILTRO MAPLIBRE
  // ========================================

  const filt = () => [

    "all",

    [
      ">",
      ["get", "n_2025"],
      0
    ],

    [
      ">=",

      [
        "coalesce",

        [
          "get",
          "promedio_estabilidad_eventos"
        ],

        -1
      ],

      Number(threshold.value)
    ]
  ];

  // ========================================
  // 2. ACTUALIZAR CAPA
  // ========================================

  function refresh() {

    if (
      !map ||
      !metricReady ||
      !map.getLayer("22_stability")
    ) {
      return;
    }

    map.setFilter(
      "22_stability",
      filt()
    );

    map.setLayoutProperty(

      "22_stability",

      "visibility",

      chk.checked
        ? "visible"
        : "none"
    );

    // ======================================
    // 3. CALCULAR RESUMEN
    // ======================================

    const visible = features.filter(
      feature =>

        Number(
          feature.properties?.n_2025
        ) > 0

        &&

        Number(
          feature.properties
            ?.promedio_estabilidad_eventos
        ) >= Number(threshold.value)
    );

    const amount = visible.reduce(

      (total, feature) =>

        total +
        Number(
          feature.properties.n_2025
        ),

      0
    );

    description.textContent =

      `${visible.length} celdas ` +

      `con promedio ≥ ` +

      `${Math.round(
        Number(threshold.value) * 100
      )}% · ` +

      `${amount.toLocaleString("es-MX")} ` +

      "registros. Criterio descriptivo, no riesgo.";
  }

  // ========================================
  // 4. RECIBIR EL MAPA YA INICIALIZADO
  // ========================================

  window.addEventListener(

    "hotspot:urbano-ready",

    event => {

      map =
        event.detail.map;

      features =
        event.detail.zonas.features;

      metricReady = features.some(
        feature =>

          feature.properties

          &&

          "promedio_estabilidad_eventos"
            in feature.properties
      );

      if (!metricReady) {

        description.textContent =
          "Falta ejecutar la Etapa 21.5.";

        return;
      }

      // ====================================
      // 5. AGREGAR CAPA TURQUESA
      // ====================================

      map.addLayer(

        {

          id: "22_stability",

          type: "line",

          source: "zones",

          filter: filt(),

          paint: {

            "line-color": "#43e1c3",

            "line-width": 2.6,

            "line-opacity": 0.97
          }

        },

        "selected"
      );

      refresh();
    }
  );

  // ========================================
  // 6. CONTROLES
  // ========================================

  chk.addEventListener(
    "change",
    refresh
  );

  threshold.addEventListener(
    "change",
    refresh
  );

})();
