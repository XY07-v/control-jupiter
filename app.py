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

# --- FUNCIÓN DISTANCIA (HAVERSINE) ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000 # Metros
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

# --- CSS ORIGINAL ---
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
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 13px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); white-space: nowrap; }
</style>
"""
FOOTER_HTML = '<div class="footer-text" style="text-align:center; padding:20px; font-size:11px; color:rgba(255,255,255,0.4);">Desarrollo de Andres Vanegas - Inteligencia de Negocio.</div>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>CMR ASISTENCIA A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

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
            <h3 style="color:#B7E4C7; text-align:center;">MENU ADMIN</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <a href="/validacion_admin" class="nav-link" style="color:#FFD97D;">Validación Pendientes 📋</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Gestión de Puntos</div>
            <a href="/descargar" class="nav-link">Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva CSV</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div class="main-content" style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px;">☰ Menú</button>
            <h2>Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Puntos</h3><div style="overflow-x:auto;"><table id="table_main_puntos"><tbody id="puntos_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">CERRAR</button></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva</h3><input type="file" id="fileCsv" accept=".csv"><button onclick="subirCsv()" class="btn btn-primary">Procesar</button></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); const puntos = await res.json(); document.getElementById('puntos_table').innerHTML = puntos.map(p => `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td></tr>`).join(''); }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}</p><button class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map" style="height:250px; margin-top:15px; display:none; border-radius:15px;"></div><img id="im1" style="width:100%; margin-top:10px; display:none;"><img id="im2" style="width:100%; margin-top:10px; display:none;">`; 
                openModal('modal_detalle'); 
            }}
            async function loadM(id, gps) {{ 
                const res = await fetch('/get_img/'+id); const d = await res.json(); 
                document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block';
                document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block';
                if(gps) {{ document.getElementById('map').style.display='block'; setTimeout(()=>{{ const c=gps.split(','); const m=L.map('map').setView(c,16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m); }},200); }}
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        pv = request.form.get('pv')
        bmb_input = request.form.get('bmb')
        gps_actual = request.form.get('ubicacion')
        
        punto_db = puntos_col.find_one({"Punto de Venta": pv})
        bmb_original = punto_db.get('BMB') if punto_db else ""
        gps_anterior = punto_db.get('Ruta') if punto_db else gps_actual

        distancia = calcular_distancia(gps_actual, gps_anterior)
        
        # VALIDACIONES: Si cambia BMB o si distancia > 100m
        bmb_cambio = bmb_input != bmb_original
        fuera_rango = distancia > 100
        
        estado = "Pendiente" if (bmb_cambio or fuera_rango) else "Aprobado"
        
        # Actualizar Ruta en la base (columna Ruta siempre tiene la última)
        puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"Ruta": gps_actual}})

        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_original, "bmb_propuesto": bmb_input, "bmb_pendiente": bmb_cambio,
            "gps_anterior": gps_anterior, "ubicacion": gps_actual, "distancia": round(distancia,1),
            "fuera_rango": fuera_rango, "estado": estado, "Nota": request.form.get('nota'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{opts}</datalist>
                <label>BMB (Corregir si es necesario)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g"><button class="btn btn-primary">GUARDAR</button>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ const v=document.getElementById('pv_i').value; const o=Array.from(document.getElementById('p').options).find(x=>x.value===v); if(o) document.getElementById('bmb_i').value=o.dataset.bmb; }}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f"""
        <div class='card' style='margin-bottom:20px; border-left: 5px solid #FFD97D;'>
            <h3>{r['pv']}</h3>
            <p><b>Asesor:</b> {r['n_documento']} | <b>Fecha:</b> {r['fecha']}</p>
            <p><b>Alerta BMB:</b> {r['bmb']} -> {r['bmb_propuesto'] if r['bmb_pendiente'] else 'Sin cambio'}</p>
            <p><b>Alerta GPS:</b> Distancia de {r['distancia']}m</p>
            <div style='display:flex; gap:5px; margin-bottom:10px;'>
                <img src='{r['f_bmb']}' style='width:50%; border-radius:10px;'>
                <img src='{r['f_fachada']}' style='width:50%; border-radius:10px;'>
            </div>
            <div id='map_{r['_id']}' style='height:300px; border-radius:15px; margin-bottom:10px;'></div>
            <button class='btn btn-primary' onclick="validar('{r['_id']}', 'aprobar')">APROBAR TODO</button>
            <button class='btn btn-gray' onclick="validar('{r['_id']}', 'rechazar')">RECHAZAR</button>
            <script>
                setTimeout(()=>{{
                    const m = L.map('map_{r['_id']}').setView([{r['ubicacion']}], 15);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m);
                    L.marker([{r['gps_anterior']}], {{title: 'Anterior'}}).addTo(m).bindPopup('Ubicación Anterior');
                    L.circle([{r['gps_anterior']}], {{radius: 100, color: 'red'}}).addTo(m);
                    L.marker([{r['ubicacion']}], {{title: 'Actual'}}).addTo(m).bindPopup('Ubicación Actual (Esta Visita)').openPopup();
                }}, 500);
            </script>
        </div>
    """ for r in pends])
    return render_template_string(f"""
    <html><head><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body><div style='padding:20px;'>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <h2>Validación de Pendientes (GPS / BMB)</h2>
        {rows or '<p>No hay registros para validar.</p>'}
        <br><a href='/' class='btn btn-gray'>Volver</a>
    </div>
    <script>async function validar(id, op){{ await fetch('/api/validar_final/'+id+'/'+op); location.reload(); }}</script>
    </body></html>
    """)

@app.route('/api/validar_final/<id>/<op>')
def api_validar_final(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        # Si hubo cambio de BMB, actualizar la maestra de puntos
        if v.get('bmb_pendiente'):
            puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado", "bmb": v['bmb_propuesto']}})
    else:
        # Si se rechaza, simplemente se marca como Rechazado para que no estorbe
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s": "ok"})

@app.route('/api/puntos')
def api_puntos(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/get_img/<id>')
def get_img(id): d=visitas_col.find_one({"_id":ObjectId(id)}); return jsonify({"f1":d.get('f_bmb'),"f2":d.get('f_fachada')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
