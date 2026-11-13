# HOTSPOT — Etapa 01: mapa de siniestros viales

Prototipo de exploración geoespacial de siniestros viales en el Área Metropolitana de Guadalajara y municipios cubiertos por el dataset. Es **un banco de pruebas** para el futuro motor de seguridad ciudadana y la papiroflexia espectral; **no es un mapa de criminalidad**.

## Cómo abrirlo

1. Descomprime el ZIP y deja `index.html`, `styles.css`, `app.js` y `data.js` en la misma carpeta.
2. Abre `index.html` con Chrome, Edge o Safari, **con conexión a internet** (MapLibre y el mapa base se cargan desde Internet).
3. Usa los filtros de año, municipio y tipo; cambia entre **Calor** y **Puntos**. En Puntos puedes hacer clic en cada siniestro.

Si tu navegador bloquea archivos locales o prefieres un servidor: desde esta carpeta ejecuta `python -m http.server 8000` y abre `http://localhost:8000`.

## Fuente y metodología

- **IIEG Jalisco, Siniestralimap 2015–2025:** https://iieg.jalisco.gob.mx/datos-abiertos/es/dataset/sinestralimap-2015-2025
- Archivo inicial suministrado: `siniestralimap_2015-2025.csv` y su diccionario.
- Archivo de eventos deduplicados: `hotspot_siniestros_eventos_2015_2025.csv`.
- **Un evento por `Id` de siniestro**, no una fila por persona. En el conjunto completo hay 18,686 eventos diferentes; 16,957 con coordenadas válidas para esta visualización.
- Campos `x`,`y`: **intersección vial más próxima**, no necesariamente ubicación exacta. No confundir con precisión a nivel inmueble.
- Las métricas `lesionados` y `fallecidos` son consecuencias reportadas en las filas originales, agregadas a nivel de siniestro; no son proyecciones ni tasas.
- El calor es una **visualización de densidad relativa** de incidentes históricos con parámetros de representación del navegador. No indica probabilidad futura, riesgo individual, causalidad o zonas peligrosas de forma absoluta.
- Cobertura territorial: Guadalajara, Zapopan, San Pedro Tlaquepaque, Tonalá, Tlajomulco de Zúñiga, El Salto, Zapotlanejo, con dos registros sin asignación municipal.
- Para análisis entre municipios, normalizar por población o exposición cuando sea pertinente; la densidad bruta depende del volumen de registros y de la calidad del reporte.

## Arquitectura etapa 01

- **MapLibre GL JS** (API en navegador): mapa y heatmap / puntos.
- HTML/CSS/JS: filtros e indicadores.
- `data.js`: copia reducida del GeoJSON proveniente de datos reales, sin dependencias de backend.
- `crear_datos.py`: script reproducible desde el CSV procesado (solo útil si mantienes el CSV fuente junto a la carpeta del proyecto).

## Siguiente etapa — papiroflexia espectral

1. Crear celdas hexagonales/cuadrícula o unidades espaciales para el grafo, evitando convertir cada persona registrada en nodo.
2. Calcular tasas/concentraciones y definir qué significa una arista (vecindad o similitud).
3. Construir `L = D - A` y una incrustación espectral con scipy/scikit-learn.
4. Animar transición entre posiciones reales y proyección espectral con Three.js.
5. Validar que la transformación revele relaciones útiles y sea interpretable.

**Importante:** la cartografía base es servida por terceros y requiere conectividad; no representa un flujo de video ni información en tiempo real.
