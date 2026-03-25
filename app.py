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
        R = 6371000 
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

# --- CSS ORIGINAL (Restaurado 100%) ---
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
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 12px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); white-space: nowrap; }
</style>
"""

# --- INICIO RUTAS ADMIN (INDEX RESTAURADO) ---
@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")} - {r.get("n_documento")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
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
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div class="main-content" style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px;">☰ Menú</button>
            <h2>Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Puntos</h3><input type="text" id="f_pv" placeholder="Filtrar..." onkeyup="filtrarPuntos()"><div style="overflow-x:auto;"><table id="table_main_puntos"><thead></thead><tbody id="puntos_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">CERRAR</button></div>
        <div id="modal_edit_punto" class="modal-box" style="z-index:4000; max-width:450px;"></div>
        <div id="modal_usuarios" class="modal-box"><h3>👥 Usuarios</h3><button class="btn btn-primary" onclick="abrirPopUser()">+ Nuevo Usuario</button><div style="overflow-x:auto;"><table><thead><tr><th>Nombre</th><th>Usuario</th><th>Acción</th></tr></thead><tbody id="user_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR</button></div>
        <div id="modal_edit_user" class="modal-box" style="z-index:4000; max-width:400px;"></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva</h3><input type="file" id="fileCsv" accept=".csv"><button onclick="subirCsv()" class="btn btn-primary">Procesar</button></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Lógica de Sidebar y Modales
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}

            // GESTIÓN DE PUNTOS (TODAS LAS COLUMNAS)
            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); window.allPuntos = await res.json(); renderPuntos(window.allPuntos); }}
            function renderPuntos(lista) {{
                if(!lista.length) return;
                const cols = Object.keys(lista[0]).filter(k => k !== '_id');
                const thead = document.querySelector('#table_main_puntos thead');
                thead.innerHTML = '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '<th>Acción</th></tr>';
                document.getElementById('puntos_table').innerHTML = lista.map(p => `<tr>${{cols.map(c => `<td>${{p[c]||''}}</td>`).join('')}}<td><button onclick='abrirPopPunto(${{JSON.stringify(p)}})'>EDITAR</button></td></tr>`).join('');
            }}
            function filtrarPuntos() {{ 
                const f = document.getElementById('f_pv').value.toLowerCase();
                renderPuntos(window.allPuntos.filter(p => Object.values(p).some(v => String(v).toLowerCase().includes(f))));
            }}
            function abrirPopPunto(p) {{
                let html = `<h3>Editar Punto</h3><input type="hidden" id="ep_id" value="${{p._id}}">`;
                Object.keys(p).filter(k=>k!='_id').forEach(k => {{ html += `<label>${{k}}</label><input type="text" class="e-f" data-k="${{k}}" value="${{p[k]||''}}">`; }});
                html += `<button class="btn btn-primary" onclick="saveP()">Guardar</button>`;
                document.getElementById('modal_edit_punto').innerHTML = html;
                document.getElementById('modal_edit_punto').style.display='block';
            }}
            async function saveP() {{
                const id = document.getElementById('ep_id').value; const d = {{}};
                document.querySelectorAll('.e-f').forEach(i => d[i.dataset.k] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:d}})}});
                closeAll(); cargarPuntos();
            }}

            // GESTIÓN DE USUARIOS
            async function cargarUsuarios() {{ const res = await fetch('/api/usuarios'); const u = await res.json(); document.getElementById('user_table').innerHTML = u.map(x => `<tr><td>${{x.nombre_completo}}</td><td>${{x.usuario}}</td><td><button onclick='abrirPopUser(${{JSON.stringify(x)}})'>EDITAR</button></td></tr>`).join(''); }}
            function abrirPopUser(u={{}}) {{
                document.getElementById('modal_edit_user').innerHTML = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor" ${{u.rol==='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol==='admin'?'selected':''}}>Admin</option></select>
                <button class="btn btn-primary" onclick="saveU('${{u._id||''}}')">Guardar</button>`;
                document.getElementById('modal_edit_user').style.display='block';
            }}
            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                closeAll(); cargarUsuarios();
            }}

            // DETALLE DE VISITA
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Nota: ${{nota}}</p><button class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map" style="height:250px; margin-top:15px; display:none; border-radius:15px;"></div><img id="im1" style="width:100%; margin-top:10px; display:none;"><img id="im2" style="width:100%; margin-top:10px; display:none;">`; 
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

# --- FORMULARIO ASESOR CON VALIDACIÓN ---
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
        bmb_cambio = bmb_input != bmb_original
        fuera_rango = distancia > 100
        
        estado = "Pendiente" if (bmb_cambio or fuera_rango) else "Aprobado"
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_original, "bmb_propuesto": bmb_input, "bmb_pendiente": bmb_cambio,
            "gps_anterior": gps_anterior, "ubicacion": gps_actual, "distancia": round(distancia,1),
            "fuera_rango": fuera_rango, "estado": estado, "Nota": request.form.get('nota'),
            "motivo": request.form.get('motivo'),
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
                <label>BMB (Editar si es necesario)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                <label>Nota</label><textarea name="nota"></textarea>
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

# --- PANEL DE VALIDACIÓN ADMINISTRATIVA (TODOS LOS DATOS + MAPA DUAL) ---
@app.route('/validacion_admin')
def validacion_admin():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f"""
        <div class='card' style='margin-bottom:25px; border-left: 8px solid #FFD97D;'>
            <h3>{r['pv']}</h3>
            <div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:12px;'>
                <div><b>Asesor:</b> {r['n_documento']}</div>
                <div><b>Fecha:</b> {r['fecha']}</div>
                <div><b>BMB Base:</b> {r['bmb']}</div>
                <div style='color:#95D5B2;'><b>BMB Nuevo:</b> {r['bmb_propuesto']}</div>
                <div><b>Distancia:</b> {r['distancia']} metros</div>
                <div><b>Motivo:</b> {r['motivo']}</div>
            </div>
            <p style='font-size:12px;'><b>Nota:</b> {r.get('Nota','')}</p>
            <div style='display:flex; gap:5px; margin-top:10px;'>
                <img src='{r['f_bmb']}' style='width:50%; border-radius:10px;'>
                <img src='{r['f_fachada']}' style='width:50%; border-radius:10px;'>
            </div>
            <div id='map_{r['_id']}' style='height:300px; border-radius:15px; margin:15px 0;'></div>
            <div style='display:flex; gap:10px;'>
                <button class='btn btn-primary' onclick="validar('{r['_id']}', 'aprobar')">APROBAR</button>
                <button class='btn btn-gray' onclick="validar('{r['_id']}', 'rechazar')">RECHAZAR</button>
            </div>
            <script>
                setTimeout(()=>{{
                    const m = L.map('map_{r['_id']}').setView([{r['ubicacion']}], 15);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m);
                    L.marker([{r['gps_anterior']}], {{title: 'Anterior'}}).addTo(m).bindPopup('Ubicación Base');
                    L.circle([{r['gps_anterior']}], {{radius: 100, color: 'red', fill: false}}).addTo(m);
                    L.marker([{r['ubicacion']}], {{title: 'Actual'}}).addTo(m).bindPopup('Ubicación del Asesor').openPopup();
                }}, 500);
            </script>
        </div>
    """ for r in pends])
    return render_template_string(f"<html><head><link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' />{CSS_BI}</head><body><div style='padding:20px;'><script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><h2>Validación de Visitas</h2>{rows or '<p>No hay pendientes</p>'}<br><a href='/' class='btn btn-gray'>Volver</a></div><script>async function validar(id, op){{ await fetch('/api/validar_final/'+id+'/'+op); location.reload(); }}</script></body></html>")

# --- APIS RESTAURADAS Y COMPLETAS ---
@app.route('/api/validar_final/<id>/<op>')
def api_validar_final(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado", "bmb": v['bmb_propuesto']}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s": "ok"})

@app.route('/api/puntos')
def api_puntos(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)

@app.route('/api/actualizar_punto', methods=['POST'])
def up_p(): d=request.json; puntos_col.update_one({"_id":ObjectId(d['id'])}, {"$set":d['datos']}); return jsonify({"s":"ok"})

@app.route('/api/usuarios')
def api_u(): u=list(usuarios_col.find()); [x.update({"_id":str(x["_id"])}) for x in u]; return jsonify(u)

@app.route('/api/actualizar_usuario', methods=['POST'])
def up_u():
    d=request.json
    if d['id']: usuarios_col.update_one({"_id":ObjectId(d['id'])}, {"$set":{"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']}})
    else: usuarios_col.insert_one({"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']})
    return jsonify({"s":"ok"})

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    # Se restauraron todas las columnas para el reporte
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Reportado', 'Motivo', 'Distancia', 'GPS', 'Nota', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('motivo'), r.get('distancia'), r.get('ubicacion'), r.get('Nota'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI_Completo.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>CMR ASISTENCIA A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/get_img/<id>')
def get_img(id): d=visitas_col.find_one({"_id":ObjectId(id)}); return jsonify({"f1":d.get('f_bmb'),"f2":d.get('f_fachada')})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
