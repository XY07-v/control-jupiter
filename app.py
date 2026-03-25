from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
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

# --- CSS CON MENÚ LATERAL Y BOTONES UNIFORMES ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; }
    
    /* Sidebar Lateral Izquierdo */
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); }
    
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); }
    
    /* Botones Uniformes */
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-green { background: #34C759; color: white; }
    .btn-red { background: #FF3B30; color: white; }

    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 600px; border-radius: 25px; padding: 25px; max-height: 85vh; overflow-y: auto; }
    
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #F2F2F7; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    
    @media (max-width: 768px) {
        .sidebar { width: 70px; padding: 10px; }
        .sidebar span, .sidebar h2 { display: none; }
        .main-content { margin-left: 70px; width: calc(100% - 70px); }
    }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v["pv"]}</b><br><small>{v["fecha"]} - {v["n_documento"]}</small></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:11px; color:#8e8e93;">Hola, {session['user_name']}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Validaciones</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Datos</a>
            <div style="margin-top:auto;">
                <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                <p style="font-size:9px; color:#ccc; text-align:center;">Andres Vanegas &copy; 2026</p>
            </div>
        </div>

        <div class="main-content">
            <h3>Visitas Aprobadas</h3>
            {rows}
        </div>

        <div id="m_puntos" class="modal"><div class="modal-content" style="max-width:850px;">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Base de Puntos</h3>
            <input type="text" class="search-box" id="bus_p" placeholder="Buscar punto..." onkeyup="filP()">
            <div id="cont_p" style="overflow-x:auto;"></div>
        </div></div>

        <div id="m_users" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Usuarios</h3>
            <button class="btn btn-blue" onclick="editU()">+ Nuevo Usuario</button>
            <div id="cont_u"></div>
        </div></div>

        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="f_csv">
            <button class="btn btn-blue" onclick="subirCSV()">Procesar</button>
        </div></div>

        <div id="m_det" class="modal"><div class="modal-content"><div id="det_body"></div></div></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let pts_data = [];
            document.addEventListener('keydown', e => {{ if(e.key === 'Escape') closeM(); }});
            function openM(id) {{ 
                document.getElementById(id).style.display='block'; 
                if(id=='m_puntos') cargaP(); 
                if(id=='m_users') cargaU(); 
            }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargaP() {{
                const r = await fetch('/api/puntos'); pts_data = await r.json(); renderP(pts_data);
            }}
            function renderP(data) {{
                let h = '<table><tr><th>Punto</th><th>BMB</th><th>Acción</th></tr>';
                data.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td><td><button class="btn btn-light" onclick='editP(${{JSON.stringify(p)}})'>Editar</button></td></tr>`);
                document.getElementById('cont_p').innerHTML = h + '</table>';
            }}
            function filP() {{
                const v = document.getElementById('bus_p').value.toLowerCase();
                renderP(pts_data.filter(p => Object.values(p).some(x => String(x).toLowerCase().includes(v))));
            }}

            function editP(p) {{
                let form = '<h3>Editar Punto</h3>';
                Object.keys(p).forEach(k => {{ if(k!='_id') form += `<label>${{k}}</label><input type="text" id="ed_${{k}}" value="${{p[k]}}">`; }});
                form += `<button class="btn btn-blue" onclick="saveP('${{p._id}}')">Guardar</button>
                         <button class="btn btn-light" onclick="cargaP()">Regresar</button>`;
                document.getElementById('m_puntos').querySelector('.modal-content').innerHTML = form;
            }}
            async function saveP(id) {{
                let d = {{}}; document.querySelectorAll('[id^="ed_"]').forEach(i => d[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:d}})}});
                cargaP();
            }}

            async function cargaU() {{
                const r = await fetch('/api/usuarios'); const us = await r.json();
                let h = '<table><tr><th>Nombre</th><th>Acción</th></tr>';
                us.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td><button class="btn btn-light" onclick='editU(${{JSON.stringify(u)}})'>Editar</button></td></tr>`);
                document.getElementById('cont_u').innerHTML = h + '</table>';
            }}
            function editU(u={{}}) {{
                const form = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor" ${{u.rol=='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol=='admin'?'selected':''}}>Admin</option></select>
                <button class="btn btn-blue" onclick="saveU('${{u._id||''}}')">Guardar</button>
                <button class="btn btn-light" onclick="cargaU()">Regresar</button>`;
                document.getElementById('m_users').querySelector('.modal-content').innerHTML = form;
            }}
            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                cargaU();
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); closeM();
            }}
            async function verVisita(id) {{
                openM('m_det'); const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeM()">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}" style="width:100%; border-radius:15px; margin-bottom:10px;"><img src="${{d.f2}}" style="width:100%; border-radius:15px;">`;
                const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = ""
    for r in pends:
        rows += f'''<div class="card" style="border-left: 8px solid #FF9500;">
            <h3 style="margin:0;">{r['pv']}</h3>
            <p style="font-size:13px; margin:5px 0;"><b>Motivo:</b> {r.get('motivo')} | <b>Distancia:</b> {r.get('distancia')}m</p>
            <div style="background:#f9f9f9; padding:10px; border-radius:10px; margin-bottom:10px; font-size:12px;">
                <b>BMB Actual:</b> {r.get('bmb')} <br>
                <b style="color:var(--ios-blue);">BMB Propuesto:</b> {r.get('bmb_propuesto')}
            </div>
            <div style="display:flex; gap:10px; margin-bottom:15px;">
                <img src="{r['f_bmb']}" style="width:50%; border-radius:12px;">
                <img src="{r['f_fachada']}" style="width:50%; border-radius:12px;">
            </div>
            <div style="display:flex; gap:10px;">
                <button class="btn btn-green" onclick="vF('{r['_id']}', 'aprobar')">Aprobar Cambio</button>
                <button class="btn btn-red" onclick="vF('{r['_id']}', 'rechazar')">Rechazar</button>
            </div>
        </div>'''
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px;">Nestlé BI</h2>
            <a href="/" class="btn btn-light">← Volver al Panel</a>
        </div>
        <div class="main-content">
            <h2>Pendientes de Validación</h2>
            <p style="color:#8e8e93; font-size:12px;">Se requiere validación por cambio de BMB o distancia mayor a 100m.</p>
            {rows or '<p>No hay pendientes por revisar.</p>'}
        </div>
        <script>async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script>
    </body></html>
    """)

# --- APIS (SIN TOCAR LÓGICA EXISTENTE) ---
@app.route('/api/v_final/<id>/<op>')
def api_v_final(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        pv = request.form.get('pv'); bmb_in = request.form.get('bmb'); gps = request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_orig = pnt.get('BMB') if pnt else ""; dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "motivo": request.form.get('motivo'), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    msg = '<div id="m" style="background:#34C759; color:white; padding:15px; border-radius:15px; text-align:center;">✓ Reporte Enviado</div><script>setTimeout(()=>document.getElementById("m").remove(),4000)</script>' if request.args.get('msg') else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px; margin:auto; padding-top:20px;">
            {msg}
            <div class="card">
                <h3 style="text-align:center;">Nueva Visita</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Punto de Venta" onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue">Enviar</button>
                    <a href="/" class="btn btn-light">Volver</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/api/puntos')
def api_p(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/actualizar_punto', methods=['POST'])
def api_up_p(): d = request.json; puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']}); return jsonify({"s": "ok"})
@app.route('/api/usuarios')
def api_u(): u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/actualizar_usuario', methods=['POST'])
def api_up_u():
    d = request.json
    if d['id']: usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}})
    else: usuarios_col.insert_one({"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']})
    return jsonify({"s": "ok"})
@app.route('/get_img/<id>')
def api_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
