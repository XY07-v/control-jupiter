from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS (MANTENIDO) ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); min-height: 100vh; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); }
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; transition: 0.2s; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 600px; border-radius: 25px; padding: 25px; max-height: 85vh; overflow-y: auto; position: relative; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #F2F2F7; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    @media (max-width: 768px) { .sidebar { width: 0; padding: 0; display:none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

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

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    
    # Solo traemos los últimos 40 para no saturar memoria
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(40)
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v.get("pv", "N/A")}</b><br><small>{v.get("fecha", "")} - {v.get("n_documento", "")}</small></div>' for v in cursor])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:13px; font-weight:bold;">{session.get('user_name')}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Datos</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content"><h3>Historial Reciente</h3>{rows or '<p>No hay visitas registradas.</p>'}</div>
        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="f_csv" accept=".csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar CSV</button>
        </div></div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargaP() {{
                const r = await fetch('/api/puntos'); const pts = await r.json();
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Puntos</h3><div id="tabla_p"><table><tr><th>Punto</th><th>BMB</th></tr>';
                pts.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']||''}}</td></tr>`);
                document.getElementById('cont_p_modal').innerHTML = h + '</table></div>';
            }}

            async function cargaU() {{
                const r = await fetch('/api/usuarios'); const us = await r.json();
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Usuarios</h3><table>';
                us.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td></tr>`);
                document.getElementById('cont_u_modal').innerHTML = h + '</table>';
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert(res.s || res.error); location.reload();
            }}

            async function verVisita(id) {{
                openM('m_det'); document.getElementById('det_body').innerHTML = "Cargando...";
                const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeM()">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}" style="width:100%; margin-bottom:10px;"><img src="${{d.f2}}" style="width:100%;">`;
                const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        try:
            def b64(f):
                if not f or not f.filename: return ""
                data = base64.b64encode(f.read()).decode()
                f.close()
                return f"data:image/jpeg;base64,{data}"

            pv_in = request.form.get('pv')
            bmb_in = request.form.get('bmb')
            gps = request.form.get('ubicacion')
            
            pnt = puntos_col.find_one({"Punto de Venta": pv_in}, {"BMB": 1, "Ruta": 1})
            bmb_duplicado = puntos_col.find_one({"BMB": bmb_in, "Punto de Venta": {"$ne": pv_in}}, {"Punto de Venta": 1})
            
            bmb_orig = pnt.get('BMB', "") if pnt else "NUEVO"
            ruta_orig = pnt.get('Ruta', "") if pnt else ""
            dist = calcular_distancia(gps, ruta_orig)
            
            # Lógica de aprobación automática o pendiente
            duplicado_en = bmb_duplicado['Punto de Venta'] if bmb_duplicado else ""
            estado_v = "Pendiente" if (bmb_in != bmb_orig or dist > 100 or duplicado_en) else "Aprobado"

            visitas_col.insert_one({
                "pv": pv_in, "n_documento": session.get('user_name'), "fecha": request.form.get('fecha'),
                "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
                "distancia": round(dist, 1), "estado": estado_v,
                "bmb_duplicado_en": duplicado_en, "is_new": not pnt,
                "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
            })

            if estado_v == "Aprobado":
                puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}})
            
            gc.collect()
            return redirect('/formulario?msg=OK')
        except Exception as e:
            return f"Error procesando el formulario: {str(e)}", 500
    
    # Solo nombres para el datalist
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos_col.find({}, {"Punto de Venta": 1, "_id": 0})])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px; margin:auto; padding:20px;">
            <div class="card">
                <h2 style="text-align:center; color:var(--ios-blue);">Nestlé BI</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Punto de Venta" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <label style="font-size:11px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:11px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    if not f: return jsonify({"error": "No hay archivo"}), 400
    try:
        # Leer el contenido una sola vez
        content = f.read().decode("utf-8-sig")
        f.close()
        
        # Detectar delimitador
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        
        lista = []
        for r in reader:
            if r: lista.append({k.strip(): v.strip() for k, v in r.items() if k})
        
        if lista:
            puntos_col.delete_many({})
            puntos_col.insert_many(lista)
            gc.collect()
            return jsonify({"s": f"Se cargaron {len(lista)} puntos con éxito"})
        return jsonify({"error": "El archivo está vacío"}), 400
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route('/api/puntos')
def api_p():
    p = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1, "_id": 0}).limit(100))
    return jsonify(p)

@app.route('/api/usuarios')
def api_u():
    u = list(usuarios_col.find({}, {"nombre_completo": 1, "rol": 1, "_id": 0}))
    return jsonify(u)

@app.route('/get_img/<id>')
def api_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1, "ubicacion": 1})
    if not d: return jsonify({})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: 
            session.permanent = True
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
