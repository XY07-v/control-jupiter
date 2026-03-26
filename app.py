from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_v21_stable"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000 
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

# --- CSS FIJO (RESTABLECIDO SEGÚN TU FOTO) ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); min-height: 100vh; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); }
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    
    /* MODALES AJUSTADOS A PANTALLA */
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 600px; border-radius: 25px; padding: 25px; max-height: 85vh; overflow-y: auto; position: relative; box-sizing: border-box; }
    
    /* BUSCADORES */
    .search-container { display: flex; gap: 8px; margin-bottom: 15px; }
    .search-input { flex: 1; padding: 12px; border-radius: 12px; border: 1px solid #D1D1D6; }
    .btn-search { background: var(--ios-blue); color: white; border: none; border-radius: 12px; width: 45px; cursor: pointer; }

    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #F2F2F7; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    
    @media (max-width: 768px) { 
        .sidebar { display:none; } 
        .main-content { margin-left: 0; width: 100%; }
        .modal-content { width: 95%; margin: 2% auto; max-height: 95vh; }
    }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(50))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v.get("pv","")}</b><br><small>{v.get("fecha","")} - {v.get("n_documento","")}</small></div>' for v in visitas])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:13px; font-weight:bold;">{session['user_name']}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Datos</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content">
            <h3>Historial de Visitas</h3>
            <div class="search-container">
                <input type="text" id="q_hist" class="search-input" placeholder="Buscar en historial...">
                <button class="btn-search" onclick="buscarH()">🔍</button>
            </div>
            <div id="cont_h">{rows}</div>
        </div>
        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="f_csv" accept=".csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar</button>
        </div></div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            
            async function buscarH() {{
                const q = document.getElementById('q_hist').value;
                const r = await fetch('/api/search?tipo=historial&q='+q);
                const data = await r.json();
                let html = '';
                data.forEach(v => html += `<div class="card" onclick="verVisita('${{v._id}}')"><b>${{v.pv}}</b><br><small>${{v.fecha}} - ${{v.n_documento}}</small></div>`);
                document.getElementById('cont_h').innerHTML = html || '<p>Sin resultados</p>';
            }}

            async function cargaP() {{
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Puntos</h3>';
                h += '<div class="search-container"><input type="text" id="q_p" class="search-input"><button class="btn-search" onclick="buscarP()">🔍</button></div><div id="tab_p"></div>';
                document.getElementById('cont_p_modal').innerHTML = h;
                buscarP();
            }}
            async function buscarP() {{
                const q = document.getElementById('q_p')?.value || '';
                const r = await fetch('/api/search?tipo=puntos&q='+q);
                const data = await r.json();
                let h = '<table><tr><th>Punto</th><th>BMB</th></tr>';
                data.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p.BMB||''}}</td></tr>`);
                document.getElementById('tab_p').innerHTML = h + '</table>';
            }}

            async function cargaU() {{
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Usuarios</h3>';
                h += '<div id="tab_u"></div>';
                document.getElementById('cont_u_modal').innerHTML = h;
                const r = await fetch('/api/get/usuarios');
                const data = await r.json();
                let t = '<table>';
                data.forEach(u => t += `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td></tr>`);
                document.getElementById('tab_u').innerHTML = t + '</table>';
            }}

            async function verVisita(id) {{
                openM('m_det');
                const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeM()">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}" style="width:100%;"><img src="${{d.f2}}" style="width:100%;">`;
                const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
            }}
            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                location.reload();
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}" if f and f.filename else ""
        pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        bmb_orig = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        
        visitas_col.insert_one({
            "pv": pv_in, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, "distancia": round(dist, 1),
            "estado": "Pendiente", "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        gc.collect()
        return redirect('/formulario?msg=OK')
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px; margin:auto; padding:20px;">
            <div class="card">
                <h2 style="text-align:center; color:var(--ios-blue);">Nestlé BI</h2>
                <label>1. Buscar Punto</label>
                <div class="search-container">
                    <input type="text" id="bus_pv" class="search-input" placeholder="Nombre del punto...">
                    <button class="btn-search" onclick="buscarPunto()">🔍</button>
                </div>
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="pv" id="res_pv" readonly placeholder="Seleccione un punto" required style="background:#f9f9f9">
                    <label>BMB Base de Datos</label>
                    <input type="text" id="res_bmb" readonly style="background:#f9f9f9">
                    <label>2. Confirmar BMB Físico</label>
                    <input type="text" name="bmb" placeholder="Escriba el BMB actual" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        <div id="m_bus" class="modal"><div class="modal-content">
            <h4>Resultados</h4><div id="res_list"></div>
            <button class="btn btn-light" onclick="document.getElementById('m_bus').style.display='none'">Cerrar</button>
        </div></div>
        <script>
            async function buscarPunto() {{
                const q = document.getElementById('bus_pv').value;
                const r = await fetch('/api/search?tipo=puntos&q='+q);
                const data = await r.json();
                const m = document.getElementById('m_bus');
                const l = document.getElementById('res_list');
                m.style.display='block'; l.innerHTML = '';
                data.forEach(p => {{
                    const d = document.createElement('div'); d.className='card'; d.style.padding='10px';
                    d.innerHTML = `<b>${{p['Punto de Venta']}}</b>`;
                    d.onclick = () => {{
                        document.getElementById('res_pv').value = p['Punto de Venta'];
                        document.getElementById('res_bmb').value = p.BMB || 'N/A';
                        m.style.display='none';
                    }};
                    l.appendChild(d);
                }});
            }}
        </script>
    </body></html>
    """)

@app.route('/api/search')
def api_search():
    tipo, q = request.args.get('tipo'), request.args.get('q', '')
    col = visitas_col if tipo == 'historial' else puntos_col if tipo == 'puntos' else usuarios_col
    query = {}
    if q:
        if tipo == 'puntos': query["Punto de Venta"] = {"$regex": q, "$options": "i"}
        else: query["pv"] = {"$regex": q, "$options": "i"}
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/get/<tipo>')
def api_get(tipo):
    col = puntos_col if tipo == 'puntos' else usuarios_col
    res = list(col.find().limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/get_img/<id>')
def api_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})

@app.route('/validacion_admin')
def validacion():
    pends = list(visitas_col.find({"estado": "Pendiente"}, {"f_bmb":0, "f_fachada":0}))
    rows = "".join([f'<div class="card"><b>{p["pv"]}</b><br><button class="btn btn-blue" onclick="vF(\'{p["_id"]}\',\'aprobar\')">Aprobar</button></div>' for p in pends])
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body><div class='main-content'><h2>Pendientes</h2>{rows}</div><script>async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

@app.route('/api/v_final/<id>/<op>')
def v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    return jsonify({"s":"ok"})

@app.route('/descargar')
def desc():
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'BMB']); return Response(si.getvalue(), mimetype="text/csv")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
