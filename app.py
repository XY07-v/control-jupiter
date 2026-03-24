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
auditoria_col = db['auditoria_bmb'] # Colección para registros de cambios

# --- FUNCIÓN DISTANCIA SIMPLE ---
def calcular_distancia(p1, p2):
    if not p1 or not p2: return 0
    try:
        lat1, lon1 = map(float, p1.split(','))
        lat2, lon2 = map(float, p2.split(','))
        # Cálculo aproximado en metros para evitar carga pesada
        return math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2) * 111320
    except: return 0

# --- CSS ORIGINAL ---
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
            <h3 style="color:#B7E4C7; text-align:center;">BI Nestlé</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <a href="/validacion" class="nav-link">Validación Visitas POC</a>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div class="main-content" style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰ Menú</button>
            <h2>Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = 'block'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Nota: ${{nota}}</p>`; openModal('modal_detalle'); }}
            function openModal(id) {{ document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg = request.args.get('msg')
    if request.method == 'POST':
        pv = request.form.get('pv')
        nbmb = request.form.get('bmb')
        gps = request.form.get('ubicacion')
        punto = puntos_col.find_one({"Punto de Venta": pv})
        
        # Auditoría y actualización BMB
        if punto and punto.get('BMB') != nbmb:
            auditoria_col.insert_one({"pv": pv, "usr": session['user_name'], "ant": punto.get('BMB'), "new": nbmb, "f": datetime.now()})
            puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"BMB": nbmb}})
        
        # Validación distancia y columna Ruta
        dist = calcular_distancia(gps, punto.get('Ruta')) if punto else 0
        puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"Ruta": gps}})
        est = "Pendiente" if dist > 100 else "Aprobado"

        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        visitas_col.insert_one({"pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'), "bmb": nbmb, "motivo": request.form.get('motivo'), "ubicacion": gps, "estado": est, "distancia": round(dist, 1), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))})
        return redirect(f'/formulario?msg={"OK" if est=="Aprobado" else "FUERA DE RANGO: Validación"}')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            {f'<p style="text-align:center; color:#40916C;">{msg}</p>' if msg else ''}
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{opts}</datalist>
                <label>BMB (Editable)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Visita a POC</option><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Dificultades Trade</option></select>
                <label>Foto 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g"><button class="btn btn-primary">GUARDAR</button>
                <a href="/" class="btn btn-gray">VOLVER</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ 
                const v = document.getElementById('pv_i').value;
                const o = Array.from(document.getElementById('p').options).find(opt => opt.value === v);
                if(o) document.getElementById('bmb_i').value = o.dataset.bmb;
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion')
def validacion():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f"<tr><td>{r['pv']}</td><td>{r['n_documento']}</td><td>{r['distancia']}m</td><td><a href='/aprobar/{r['_id']}'>Aprobar</a></td></tr>" for r in pends])
    return render_template_string(f"<html><head>{CSS_BI}</head><body><div style='padding:20px;'><h2>Validación</h2><table><tr><th>PV</th><th>Asesor</th><th>Dist</th><th>Acción</th></tr>{rows}</table><br><a href='/'>Volver</a></div></body></html>")

@app.route('/aprobar/<id>')
def aprobar(id):
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    return redirect('/validacion')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
