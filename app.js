(() => {
  'use strict';
  const raw = window.HOTSPOT_DATA;
  const $ = (id) => document.getElementById(id);
  const countFmt = new Intl.NumberFormat('es-MX');
  const meses = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
  const elements = {year:$('year'),municipio:$('municipio'),tipo:$('tipo')};
  if (!raw || !Array.isArray(raw.eventos)) { $('loading').textContent = 'No se pudo abrir data.js. Comprueba que esté en la misma carpeta.'; return; }
  const events = raw.eventos.map(row => ({
    longitude:row[0],latitude:row[1],year:row[2],month:row[3],munCode:row[4],typeCode:row[5],deaths:row[6],injured:row[7],date:row[8],id:row[9],hours:row[10],street1:row[11],street2:row[12]
  }));
  const state = {year:'2025',municipio:'all',tipo:'all',mode:'heatmap'};
  let map, activePopup = null, loaded=false;
  const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const options = (select,arr) => { for (const [val,title] of arr) { const opt=document.createElement('option');opt.value=val;opt.textContent=title;select.appendChild(opt); } };
  options(elements.year,[['all','Todos los años (2015–2025)'],...Array.from({length:11},(_,i)=>[String(2025-i),String(2025-i)])]);
  options(elements.municipio,[['all','Todos los municipios'],...raw.municipios.map((m,i)=>[String(i),m])]);
  options(elements.tipo,[['all','Todos los tipos'],...raw.tipos.map((t,i)=>[String(i),t])]);
  for(const [key,input] of Object.entries(elements)) {input.value=state[key];input.addEventListener('change',() => {state[key]=input.value; update(); if(key==='municipio') focusMunicipio();});}
  $('clear').addEventListener('click',()=> { state.year='2025';state.municipio='all';state.tipo='all';for (const [key,el] of Object.entries(elements)) el.value=state[key]; update(); if (map) map.flyTo({center:[-103.350,20.669],zoom:10.7,duration:900}); });
  for(const b of document.querySelectorAll('[data-mode]')) b.addEventListener('click',()=> {state.mode=b.dataset.mode;for(const other of document.querySelectorAll('[data-mode]')){let active=other===b;other.classList.toggle('active',active);other.setAttribute('aria-pressed',active?'true':'false');} setMode();});
  function filteredEvents() {return events.filter(e=> (state.year==='all'||e.year===+state.year) && (state.municipio==='all'||e.munCode===+state.municipio) && (state.tipo==='all'||e.typeCode===+state.tipo));}
  function features(items) {return {type:'FeatureCollection', features: items.map(e=>({type:'Feature',geometry:{type:'Point',coordinates:[e.longitude,e.latitude]},properties:{id:e.id,year:e.year,month:e.month,date:e.date,municipio:raw.municipios[e.munCode],tipo:raw.tipos[e.typeCode],injured:e.injured,deaths:e.deaths,hours:e.hours,street1:e.street1,street2:e.street2}}))};}
  function chart(items) {
    let buckets=[], labels=[];
    if(state.year==='all') {labels=Array.from({length:11},(_,i)=>String(2015+i)); buckets=labels.map(y=>items.filter(e=>e.year===+y).length);$('period-unit').textContent='AÑOS';}
    else { labels=meses; buckets=labels.map((_,i)=>items.filter(e=>e.month===i+1).length); $('period-unit').textContent='MESES'; }
    const max=Math.max(...buckets,1);
    const chart=$('chart');chart.replaceChildren();
    buckets.forEach((n,i)=>{const bar=document.createElement('div');bar.className='spark-bar';bar.style.setProperty('--h',`${n ? Math.max(5,(n/max)*100) : 2}%`);bar.title=`${labels[i]}: ${countFmt.format(n)} siniestros`;chart.appendChild(bar);});
    $('chart-first').textContent=labels[0];$('chart-last').textContent=labels[labels.length-1];
  }
  function update() {
    const items=filteredEvents(), total=items.length;
    $('count').textContent=countFmt.format(total);
    $('injured').textContent=countFmt.format(items.reduce((s,e)=>s+e.injured,0));
    $('fatal').textContent=countFmt.format(items.reduce((s,e)=>s+e.deaths,0));
    $('active-period').textContent=state.year==='all'?'2015–2025':state.year;
    $('floating-count').textContent=countFmt.format(total)+' siniestros filtrados';
    $('map-subtitle').textContent=`${state.year==='all'?'2015–2025':state.year} · ${state.municipio==='all'?'Siete municipios principales + registros sin municipio':raw.municipios[+state.municipio]}`;
    chart(items);
    if(activePopup){activePopup.remove(); activePopup=null;}
    if(loaded && map.getSource('events')) map.getSource('events').setData(features(items));
  }
  function setMode() {
    if (!loaded)return;
    map.setLayoutProperty('heat','visibility',state.mode==='heatmap'?'visible':'none');
    map.setLayoutProperty('points','visibility',state.mode==='points'?'visible':'none');
    $('legend-title').textContent=state.mode==='heatmap'?'DENSIDAD RELATIVA DE SINIESTROS':'LEYENDA DE INTENSIDAD (VISTA CALOR)';
    document.querySelector('.map-bottom-left').style.display=state.mode==='heatmap'?'block':'none';
    $('map-tip').innerHTML=state.mode==='heatmap'?'Cambia a <strong>Puntos</strong> para inspeccionar eventos.':'Selecciona un <strong>punto</strong> para ver la ficha.';
  }
  function focusMunicipio() {
    if (!map || state.municipio==='all')return;
    const items=filteredEvents(); if (!items.length)return;
    const bounds=new maplibregl.LngLatBounds(); for(const e of items)bounds.extend([e.longitude,e.latitude]);
    map.fitBounds(bounds,{padding:65,maxZoom:12.4,duration:950});
  }
  function popupHtml(p) {
    const row=(key,val)=>`<div class="popup-row"><span>${key}</span><span>${escapeHtml(val)}</span></div>`;
    return `<div class="popup-head">${escapeHtml(p.tipo)}</div>${row('Municipio',p.municipio)}${row('Fecha',p.date)}${row('Horario',p.hours||'Sin dato')}${row('Vialidades',[p.street1,p.street2].filter(Boolean).join(' / ')||'No registradas')}${row('Lesionados*',p.injured)}${row('Fallecidos*',p.deaths)}<div class="popup-note">Punto aproximado: intersección vial más cercana. *Datos consolidados por siniestro.</div>`;
  }
  function initMap() {
    if (!window.maplibregl) { $('loading').innerHTML='<div style="padding:24px;max-width:440px;line-height:1.5;text-align:center">No se pudo cargar MapLibre. Abre este archivo con conexión a internet; si hay restricciones de red, usa un servidor local.</div>';return; }
    map=new maplibregl.Map({container:'map',style:'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',center:[-103.35,20.669],zoom:10.7,pitch:0,attributionControl:false});
    map.addControl(new maplibregl.NavigationControl({showCompass:true}), 'top-right');
    map.addControl(new maplibregl.AttributionControl({compact:true}),'bottom-right');
    let mapReady=false;
    map.on('load',()=>{
      mapReady=true;
      map.addSource('events',{type:'geojson',data:features(filteredEvents()),generateId:true});
      map.addLayer({id:'heat',type:'heatmap',source:'events',maxzoom:18,paint:{'heatmap-weight':1,'heatmap-intensity':['interpolate',['linear'],['zoom'],8,0.65,13,1.2,16,1.6],'heatmap-radius':['interpolate',['linear'],['zoom'],8,11,12,27,15,47],'heatmap-opacity':['interpolate',['linear'],['zoom'],9,0.95,16,0.72], 'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(0,0,0,0)',0.08,'rgba(42,196,210,0.1)',0.22,'#22bbd3',0.39,'#4e86e8',0.55,'#eabf2b',0.76,'#f9802c',1,'#f04446']}});
      map.addLayer({id:'points',type:'circle',source:'events',layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['linear'],['zoom'],8,2,11,3.5,15,6.5],'circle-color':['case',['>', ['get','deaths'],0],'#ff876f','#3fe0c8'],'circle-opacity':0.8,'circle-stroke-width':0.5,'circle-stroke-color':'#07212b'}});
      map.on('click','points',e=>{if(!e.features||!e.features.length)return;const feature=e.features[0];activePopup=new maplibregl.Popup({maxWidth:'340px',closeButton:true}).setLngLat(feature.geometry.coordinates).setHTML(popupHtml(feature.properties)).addTo(map);});
      map.on('mouseenter','points',()=>map.getCanvas().style.cursor='pointer');
      map.on('mouseleave','points',()=>map.getCanvas().style.cursor='');
      loaded=true;setMode();update();$('loading').classList.add('hidden');
    });
    map.on('error',evt=>{if(!mapReady){const issue=$('loading');issue.innerHTML='<div style="padding:24px;line-height:1.5;max-width:380px;text-align:center">No se pudo cargar el mapa base. Comprueba tu conexión a internet. Los filtros y la serie temporal siguen disponibles.</div>';}});
  }
  update();initMap();
})();
