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
auditoria_col = db['auditoria_bmb'] # Nueva colección para logs

# --- FUNCIÓN DISTANCIA (HAVERSINE) ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000 # Radio Tierra en metros
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

# --- CSS ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; --warning: #FFB333; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); z-index: 2000; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); transition: 0.3s; z-index: 2100; padding: 25px; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; }
    .nav-link:hover { background: var(--primary); }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; margin-top: 10px; text-align: center; display: block; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    .btn-logout { background: #BC4749; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .badge-pending { background: var(--warning); color: black; padding: 2px 8px; border-radius: 5px; font-size: 10px; }
</style>
"""
FOOTER_HTML = '<div style="text-align:center; padding:20px; font-size:11px; color:rgba(255,255,255,0.4);">Desarrollo de Andres Vanegas - Inteligencia de Negocio. 2026.</div>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>POC NESTLÉ 2026</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    # Solo mostrar visitas aprobadas en el index
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")} - {r.get("n_documento")}</small></div></div>' for r in cursor])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">BI NESTLÉ</h3>
            <a href="/formulario" class="nav-link">Nueva Visita</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Gestión de Puntos</div>
            <div class="nav-link" onclick="location.href='/validacion'">Validación Visitas POC</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px;">☰ Menú</button>
            <h2>Visitas Aprobadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Puntos de Venta</h3><div id="puntos_cont" style="overflow-x:auto;"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_edit_punto" class="modal-box" style="max-width:400px; z-index:4000;"></div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = 'block'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m=>m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            function openModal(id) {{ closeAll(); document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); }}
            async function cargarPuntos() {{
                const res = await fetch('/api/puntos'); const puntos = await res.json();
                let h = '<table><tr><th>Punto</th><th>BMB</th><th>Ruta (GPS)</th><th>Acción</th></tr>';
                puntos.forEach(p => {{ h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td><td>${{p['Ruta'] || 'Sin capturar'}}</td><td><button onclick=\'abrirPopPunto(${{JSON.stringify(p)}})\'>EDITAR</button></td></tr>`; }});
                document.getElementById('puntos_cont').innerHTML = h + '</table>';
            }}
            function abrirPopPunto(p) {{
                const cont = document.getElementById('modal_edit_punto');
                let inputs = ''; Object.keys(p).filter(k=>k!=='_id').forEach(k=>{{ inputs += `<label>${{k}}</label><input type="text" class="edit-f" data-key="${{k}}" value="${{p[k]||''}}">`; }});
                cont.innerHTML = `<h3>Editar</h3>${{inputs}}<button class="btn btn-primary" onclick="actPunto()">Guardar</button><button class="btn btn-gray" onclick="this.parentElement.style.display='none'">Cancelar</button>`;
                cont.style.display='block';
            }}
            async function actPunto() {{
                const fields = {{}}; document.querySelectorAll('.edit-f').forEach(i=> fields[i.dataset.key] = i.value);
                await fetch('/api/actualizar_punto', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:document.querySelector('.edit-f').parentElement.querySelector('input[data-key="Punto de Venta"]').value, datos:fields}}) }});
                cargarPuntos(); document.getElementById('modal_edit_punto').style.display='none';
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion')
def validacion():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pendientes = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f'<tr><td>{p["pv"]}</td><td>{p["n_documento"]}</td><td>{p["distancia"]}m</td><td><button onclick="aprobar(\'{p["_id"]}\')">Aprobar</button></td></tr>' for p in pendientes])
    return render_template_string(f"<html><head>{CSS_BI}</head><body><div style='padding:20px;'><h2>Validación de Visitas (>100m)</h2><table><tr><th>PV</th><th>Asesor</th><th>Distancia</th><th>Acción</th></tr>{rows}</table><br><a href='/' class='btn btn-gray'>Volver</a></div><script>async function aprobar(id){{ await fetch('/api/aprobar/'+id); location.reload(); }}</script></body></html>")

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        pv_nombre = request.form.get('pv')
        nuevo_bmb = request.form.get('bmb')
        gps_actual = request.form.get('ubicacion')
        
        # 1. Buscar Punto de Venta para validar distancia y BMB antiguo
        punto = puntos_col.find_one({"Punto de Venta": pv_nombre})
        bmb_antiguo = punto.get('BMB')
        gps_referencia = punto.get('Ruta')
        
        # 2. Auditoría si cambió el BMB
        if nuevo_bmb != bmb_antiguo:
            auditoria_col.insert_one({
                "pv": pv_nombre, "fecha": datetime.now(), "usuario": session['user_name'],
                "cambio": f"BMB: {bmb_antiguo} -> {nuevo_bmb}"
            })
            puntos_col.update_one({"Punto de Venta": pv_nombre}, {"$set": {"BMB": nuevo_bmb}})

        # 3. Validar Distancia
        dist = calcular_distancia(gps_actual, gps_referencia)
        estado = "Aprobado"
        if dist > 100: estado = "Pendiente"
        
        # 4. Actualizar Ubicación en Puntos de Venta (Columna Ruta)
        puntos_col.update_one({"Punto de Venta": pv_nombre}, {"$set": {"Ruta": gps_actual}})

        # 5. Insertar Visita
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        visitas_col.insert_one({
            "pv": pv_nombre, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": nuevo_bmb, "motivo": request.form.get('motivo'), "ubicacion": gps_actual,
            "distancia": round(dist, 2), "estado": estado,
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        
        msg = "Visita Guardada" if estado == "Aprobado" else "FUERA DE RANGO: Enviado a Validación"
        return redirect(f'/formulario?msg={msg}')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1, "Ruta": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()">
        <div class="card" style="max-width:450px; margin: 20px auto;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            {f'<div style="background:var(--warning); color:black; padding:10px; border-radius:10px; margin-bottom:10px; text-align:center;">{request.args.get("msg")}</div>' if request.args.get('msg') else ''}
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input list="p" name="pv" id="pv_i" onchange="upBMB()" required>
                <datalist id="p">{options}</datalist>
                
                <label>BMB (Editable)</label>
                <input type="text" name="bmb" id="bmb_i">
                
                <label>Fecha</label>
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                
                <label>Motivo</label>
                <select name="motivo">
                    <option>Visita a POC</option>
                    <option>Máquina Retirada</option>
                    <option>Punto Cerrado</option>
                    <option>Dificultades Trade</option>
                    <option>Fuera de rango</option>
                </select>
                
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">REGISTRAR VISITA</button>
                <a href="/" class="btn btn-gray">VOLVER</a>
            </form>
        </div>
        <script>
            function getGPS(){{ navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude); }}
            function upBMB() {{
                const v = document.getElementById('pv_i').value;
                const o = Array.from(document.getElementById('p').options).find(opt => opt.value === v);
                if(o) document.getElementById('bmb_i').value = o.dataset.bmb;
            }}
        </script>
    </body></html>
    """)

@app.route('/api/aprobar/<id>')
def aprobar(id):
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    return jsonify({"s": "ok"})

@app.route('/api/puntos')
def api_puntos():
    p = list(puntos_col.find())
    for x in p: x["_id"] = str(x["_id"])
    return jsonify(p)

@app.route('/api/actualizar_punto', methods=['POST'])
def up_p():
    d = request.json
    puntos_col.update_one({"Punto de Venta": d['id']}, {"$set": d['datos']})
    return jsonify({"s": "ok"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
