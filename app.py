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
auditoria_col = db['auditoria_bmb']

# --- FUNCIÓN DISTANCIA ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); z-index: 2000; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; box-shadow: 0 0 50px rgba(0,0,0,0.9); }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 13px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; border: 1px solid var(--accent); }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    # Visitas normales (aprobadas y sin cambios de BMB pendientes)
    cursor = visitas_col.find({"estado": "Aprobado", "bmb_pendiente": {"$ne": True}}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">BI NESTLÉ</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <a href="/validacion_bmb" class="nav-link" style="color:#FFD97D;">Validación BMB 📋</a>
            <a href="/validacion_visitas" class="nav-link">Validación GPS 📍</a>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px;">☰ Menú</button>
            <h2>Visitas Recientes</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = 'block'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            function openModal(id) {{ closeAll(); document.getElementById(id).style.display='block'; document.getElementById('overlay').style.display='block'; }}
            async function verDetalle(id) {{
                const res = await fetch('/get_visita/'+id); const r = await res.json();
                document.getElementById('det_body').innerHTML = `<h3>${{r.pv}}</h3><p>BMB: ${{r.bmb}}<br>Asesor: ${{r.n_documento}}<br>Fecha: ${{r.fecha}}</p><img src="${{r.f_bmb}}" class="img-preview"><img src="${{r.f_fachada}}" class="img-preview">`;
                openModal('modal_detalle');
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        pv_nombre = request.form.get('pv')
        bmb_input = request.form.get('bmb')
        gps = request.form.get('ubicacion')
        punto = puntos_col.find_one({"Punto de Venta": pv_nombre})
        
        bmb_original = punto.get('BMB') if punto else ""
        bmb_cambio_pendiente = False
        
        # Si el BMB es diferente, marcamos para validación manual
        if bmb_input != bmb_original:
            bmb_cambio_pendiente = True

        dist = calcular_distancia(gps, punto.get('Ruta')) if punto else 0
        puntos_col.update_one({"Punto de Venta": pv_nombre}, {"$set": {"Ruta": gps}})
        estado = "Pendiente" if dist > 100 else "Aprobado"
        
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        
        visitas_col.insert_one({
            "pv": pv_nombre, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_original, # Se mantiene el original en el registro principal hasta que se valide
            "bmb_propuesto": bmb_input,
            "bmb_pendiente": bmb_cambio_pendiente,
            "motivo": request.form.get('motivo'), "ubicacion": gps, "estado": estado, "distancia": round(dist,1),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">REGISTRO DE VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{opts}</datalist>
                <label>BMB (Editable para cambio)</label><input type="text" name="bmb" id="bmb_i">
                <label>Motivo</label><select name="motivo"><option>Visita a POC</option><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
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

@app.route('/validacion_bmb')
def validacion_bmb():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pendientes = list(visitas_col.find({"bmb_pendiente": True}))
    rows = "".join([f"""
        <div class='card' style='margin-bottom:20px;'>
            <h3>{r['pv']}</h3>
            <p>Asesor: {r['n_documento']} | Fecha: {r['fecha']}</p>
            <p style='color:#FFD97D;'><b>BMB Actual:</b> {r['bmb']} <br> <b>BMB Propuesto:</b> {r['bmb_propuesto']}</p>
            <div style='display:flex; gap:10px;'>
                <img src='{r['f_bmb']}' style='width:48%; border-radius:5px;'>
                <img src='{r['f_fachada']}' style='width:48%; border-radius:5px;'>
            </div>
            <button class='btn btn-primary' onclick="validarBmb('{r['_id']}')">VALIDAR CAMBIO ✅</button>
            <button class='btn btn-gray' onclick="rechazarBmb('{r['_id']}')">RECHAZAR CAMBIO ❌</button>
        </div>
    """ for r in pendientes])
    
    return render_template_string(f"""
    <html><head>{CSS_BI}</head><body>
        <div style="padding:20px;">
            <h2>Validación de Cambios BMB</h2>
            {rows if pendientes else '<p>No hay cambios pendientes de validación.</p>'}
            <br><a href="/" class="btn btn-gray">Volver al Menú</a>
        </div>
        <script>
            async function validarBmb(id) {{
                if(confirm("¿Confirmas que el nuevo BMB es veraz según las fotos?")) {{
                    await fetch('/api/confirmar_bmb/'+id); location.reload();
                }}
            }}
            async function rechazarBmb(id) {{
                if(confirm("¿Rechazar cambio? Se mantendrá el BMB original.")) {{
                    await fetch('/api/rechazar_bmb/'+id); location.reload();
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/api/confirmar_bmb/<id>')
def api_confirmar(id):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    # 1. Actualizar Punto de Venta con el BMB propuesto
    puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto']}})
    # 2. Actualizar la visita (ahora el bmb oficial es el nuevo)
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"bmb": v['bmb_propuesto'], "bmb_pendiente": False}})
    # 3. Log de auditoría
    auditoria_col.insert_one({"pv": v['pv'], "f": datetime.now(), "admin": session['user_name'], "accion": "Aprobado", "nuevo": v['bmb_propuesto']})
    return jsonify({"s": "ok"})

@app.route('/api/rechazar_bmb/<id>')
def api_rechazar(id):
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"bmb_pendiente": False}})
    return jsonify({"s": "ok"})

@app.route('/get_visita/<id>')
def get_v(id):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    v['_id'] = str(v['_id'])
    return jsonify(v)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>ACCESO BI</h2><form method='POST'><input type='text' name='usuario' placeholder='User'><input type='password' name='password' placeholder='Pass'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
