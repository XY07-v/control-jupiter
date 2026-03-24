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
auditoria_col = db['auditoria_bmb'] # Para el registro de cambios solicitado

# --- FUNCIÓN DISTANCIA ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        rad = math.pi / 180
        dlat = (lat2 - lat1) * rad
        dlon = (lon2 - lon1) * rad
        a = math.sin(dlat/2)**2 + math.cos(lat1*rad) * math.cos(lat2*rad) * math.sin(dlon/2)**2
        return 2 * 6371000 * math.asin(math.sqrt(a))
    except: return 0

# --- CSS (TU ORIGINAL) ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); z-index: 2000; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; box-shadow: 0 0 50px rgba(0,0,0,0.9); }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    .btn-logout { background: #BC4749; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 14px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .footer-text { text-align: center; padding: 20px; font-size: 11px; color: rgba(255,255,255,0.4); margin-top: auto; }
</style>
"""
FOOTER_HTML = '<div class="footer-text">Desarrollo de Andres Vanegas - Inteligencia de Negocio. Derechos Reservados.</div>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>CMR ASISTENCIA A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div>{FOOTER_HTML}</body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">BI Nestlé POC</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Gestión de Puntos</div>
            <a href="/validacion_visitas" class="nav-link">Validación Visitas POC</a>
            <a href="/descargar" class="nav-link">Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div class="main-content" style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰ Menú</button>
            <h2 style="margin-top:20px;">Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Gestión de Puntos</h3><div id="puntos_table_cont"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); }}
            async function cargarPuntos() {{
                const res = await fetch('/api/puntos'); const puntos = await res.json();
                let html = '<table><tr><th>Punto</th><th>BMB</th><th>Ruta (GPS)</th></tr>';
                puntos.forEach(p => {{ html += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td><td>${{p['Ruta'] || ''}}</td></tr>`; }});
                document.getElementById('puntos_cont').innerHTML = html + '</table>';
            }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Nota: ${{nota}}</p><button id="ld_b" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map" style="height:200px; display:none;"></div><img id="im1" style="width:100%; display:none;"><img id="im2" style="width:100%; display:none;">`; openModal('modal_detalle'); }}
            async function loadM(id, gps) {{ const res = await fetch('/get_img/'+id); const d = await res.json(); if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }} if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }} if(gps) {{ document.getElementById('map').style.display='block'; const map = L.map('map').setView(gps.split(','), 16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); L.marker(gps.split(',')).addTo(map); }} document.getElementById('ld_b').style.display='none'; }}
        </script>
        {FOOTER_HTML}
    </body></html>
    """)

@app.route('/validacion_visitas')
def validacion_visitas():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    cursor = visitas_col.find({"estado": "Pendiente"})
    rows = "".join([f"<tr><td>{r['pv']}</td><td>{r['n_documento']}</td><td>{r['distancia']}m</td><td><button onclick='aprobar(\"{r['_id']}\")'>Aprobar</button></td></tr>" for r in cursor])
    return render_template_string(f"<html><head>{CSS_BI}</head><body><div style='padding:20px;'><h2>Validación Visitas POC (>100m)</h2><table><tr><th>Punto</th><th>Asesor</th><th>Distancia</th><th>Acción</th></tr>{rows}</table><br><a href='/' class='btn btn-gray'>Volver</a></div><script>async function aprobar(id){{ await fetch('/api/aprobar/'+id); location.reload(); }}</script></body></html>")

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg = request.args.get('msg')
    if request.method == 'POST':
        pv = request.form.get('pv')
        n_bmb = request.form.get('bmb')
        gps = request.form.get('ubicacion')
        punto_doc = puntos_col.find_one({"Punto de Venta": pv})
        
        # --- LÓGICA DE ACTUALIZACIÓN BMB Y AUDITORÍA ---
        bmb_ant = punto_doc.get('BMB')
        if n_bmb != bmb_ant:
            auditoria_col.insert_one({"punto": pv, "fecha": datetime.now(), "usuario": session['user_name'], "anterior": bmb_ant, "nuevo": n_bmb})
            puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"BMB": n_bmb}})

        # --- LÓGICA DE RUTA Y DISTANCIA ---
        dist = calcular_distancia(gps, punto_doc.get('Ruta'))
        puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"Ruta": gps}})
        estado = "Pendiente" if dist > 100 else "Aprobado"
        
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        visitas_col.insert_one({"pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'), "bmb": n_bmb, "motivo": request.form.get('motivo'), "ubicacion": gps, "distancia": round(dist,1), "estado": estado, "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))})
        
        res_msg = "OK" if estado == "Aprobado" else "FUERA DE RANGO: Enviado a Validación"
        return redirect(f'/formulario?msg={res_msg}')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            {f'<p style="color:#B7E4C7; text-align:center;">{msg}</p>' if msg else ''}
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{options}</datalist>
                <label>BMB (Editable)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Visita a POC</option><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Dificultades Trade</option></select>
                <label>Foto 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g"><button class="btn btn-primary">GUARDAR</button>
                <a href="/" class="btn btn-gray">VOLVER</a>
            </form>
        </div>
        <script>function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
        function upBMB() {{ const v = document.getElementById('pv_i').value; const o = Array.from(document.getElementById('p').options).find(opt => opt.value === v); if(o) document.getElementById('bmb_i').value = o.dataset.bmb; }}</script>
    </body></html>
    """)

@app.route('/api/puntos')
def api_puntos(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/aprobar/<id>')
def api_aprobar(id): visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}}); return jsonify({"s": "ok"})
@app.route('/get_img/<id>')
def get_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
