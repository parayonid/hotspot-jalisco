"""Transforma el CSV de eventos deduplicados en datos ligeros para la demo.
No inventa ubicaciones: solo usa las intersecciones próximas registradas.
"""
import csv, json, pathlib, collections
ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT.parent/'hotspot_siniestros_eventos_2015_2025.csv'
with SRC.open(encoding='utf-8-sig', newline='') as f:
    rows=list(csv.DictReader(f))
valid=[]
for r in rows:
    if r['coordenadas_validas'] != '1':continue
    try:
        lon=float(r['longitud_interseccion_proxima']); lat=float(r['latitud_interseccion_proxima'])
    except ValueError: continue
    if not (-106 < lon < -101 and 18 < lat < 23): continue
    valid.append((r,lon,lat))
munis=sorted({r['municipio'] for r,_,_ in valid})
types=sorted({r['tipo_siniestro'] for r,_,_ in valid})
mi={m:i for i,m in enumerate(munis)}
ti={t:i for i,t in enumerate(types)}
entries=[]
for r,lon,lat in valid:
    date=r['fecha']; ym=date.split('-'); year=int(r['anio']); month=int(ym[1])
    entries.append([round(lon,6),round(lat,6),year,month,mi[r['municipio']],ti[r['tipo_siniestro']],int(r['personas_fallecidas']),int(r['personas_lesionadas']),date,r['id_siniestro'],r['rango_hora'],r['calle_1'],r['calle_2']])
payload={'municipios':munis, 'tipos':types, 'eventos':entries, 'total_raw_rows':50433, 'total_unicos':len(rows), 'total_geo':len(entries),'fuente':'IIEG Jalisco / Siniestralimap 2015-2025'}
(ROOT/'data.js').write_text('window.HOTSPOT_DATA='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
print('unique',len(rows),'geo',len(entries),'mun',collections.Counter(r['municipio'] for r,_,_ in valid),'sizeMB',round((ROOT/'data.js').stat().st_size/1e6,2))
