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
auditoria_col = db['auditoria_bmb'] # Nueva colección para registro de cambios

# --- FUNCIÓN DISTANCIA (HAVERSINE) ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000 # Radio de la Tierra en metros
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
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
    .modal-mini { max-width: 450px; z-index: 4000; border: 2px solid var(--accent); }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    .btn-logout { background: #BC4749; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 13px; }
    th { background: rgba(0,0,0,0.3); position: sticky; top: 0; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); white-space: nowrap; }
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
    # Solo mostrar visitas que NO estén en validación en el feed principal
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">Desarrollo de Andres Vanegas</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Gestión de Puntos</div>
            <a href="/validacion_visitas" class="nav-link">Validación Visitas POC</a>
            <a href="/descargar" class="nav-link">Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva CSV</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div class="main-content" style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰ Menú</button>
            <h2 style="margin-top:20px;">Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Gestión de Puntos</h3><input type="text" id="f_pv" placeholder="Filtrar por cualquier campo..." onkeyup="filtrarPuntos()"><div style="overflow-x:auto;"><table id="table_main_puntos"><thead></thead><tbody id="puntos_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <div id="modal_usuarios" class="modal-box"><h3>👥 Usuarios</h3><div style="overflow-x:auto;"><table><thead><tr><th>Nombre</th><th>Usuario</th><th>Acción</th></tr></thead><tbody id="user_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <div id="modal_edit_punto" class="modal-box modal-mini"></div>
        <div id="modal_edit_user" class="modal-box modal-mini"><h3>Editar Usuario</h3><input type="hidden" id="eu_id"><label>Nombre</label><input type="text" id="eu_nombre"><label>Usuario</label><input type="text" id="eu_user"><label>Pass</label><input type="password" id="eu_pass"><label>Rol</label><select id="eu_rol"><option value="admin">Admin</option><option value="asesor">Asesor</option></select><button class="btn btn-primary" onclick="actualizarUsuario()">Guardar</button><button onclick="document.getElementById('modal_edit_user').style.display='none'" class="btn btn-gray">Cancelar</button></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva</h3><input type="file" id="fileCsv" accept=".csv"><button onclick="subirCsv()" class="btn btn-primary">Procesar</button><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            document.addEventListener('keydown', (e) => {{ if(e.key === "Escape") closeAll(); }});
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); const puntos = await res.json(); window.allPuntos = puntos; renderPuntos(puntos); }}
            function renderPuntos(lista) {{ 
                if(!lista || lista.length === 0) return;
                const columnas = Object.keys(lista[0]).filter(k => k !== '_id');
                const thead = document.querySelector('#table_main_puntos thead');
                thead.innerHTML = '<tr>' + columnas.map(c => `<th>${{c}}</th>`).join('') + '<th>Acción</th></tr>';
                document.getElementById('puntos_table').innerHTML = lista.map(p => `<tr>${{columnas.map(c => `<td>${{p[c] || ''}}</td>`).join('')}}<td><button onclick='abrirPopPunto(${{JSON.stringify(p)}})' style='color:#B7E4C7; background:none; border:none; cursor:pointer; font-weight:bold;'>EDITAR</button></td></tr>`).join(''); 
            }}
            function filtrarPuntos() {{ 
                const f = document.getElementById('f_pv').value.toLowerCase(); 
                const filtrados = window.allPuntos.filter(p => Object.values(p).some(val => String(val).toLowerCase().includes(f)));
                renderPuntos(filtrados); 
            }}
            function abrirPopPunto(p) {{ 
                const container = document.getElementById('modal_edit_punto');
                const columnas = Object.keys(p).filter(k => k !== '_id');
                let html = `<h3>Editar Punto de Venta</h3><input type="hidden" id="ep_id" value="${{p._id}}">`;
                columnas.forEach(col => {{ html += `<label style="font-size:12px; color:#B7E4C7;">${{col}}</label><input type="text" class="edit-field" data-key="${{col}}" value="${{p[col] || ''}}">`; }});
                html += `<button class="btn btn-primary" onclick="actualizarPunto()">Guardar Cambios</button><button onclick="document.getElementById('modal_edit_punto').style.display='none'" class="btn btn-gray">Cancelar</button>`;
                container.innerHTML = html; container.style.display = 'block'; 
            }}
            async function actualizarPunto() {{ 
                const id = document.getElementById('ep_id').value; const campos = {{}};
                document.querySelectorAll('.edit-field').forEach(input => {{ campos[input.getAttribute('data-key')] = input.value; }});
                await fetch('/api/actualizar_punto', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id: id, datos: campos}}) }}); 
                document.getElementById('modal_edit_punto').style.display='none'; cargarPuntos(); 
            }}
            async function cargarUsuarios() {{ const res = await fetch('/api/usuarios'); const users = await res.json(); document.getElementById('user_table').innerHTML = users.map(u => `<tr><td>${{u.nombre_completo}}</td><td>${{u.usuario}}</td><td><button onclick='abrirPopUser(${{JSON.stringify(u)}})' style='color:#B7E4C7; background:none; border:none; cursor:pointer;'>EDITAR</button></td></tr>`).join(''); }}
            function abrirPopUser(u) {{ document.getElementById('eu_id').value=u._id; document.getElementById('eu_nombre').value=u.nombre_completo; document.getElementById('eu_user').value=u.usuario; document.getElementById('eu_pass').value=u.password; document.getElementById('eu_rol').value=u.rol; document.getElementById('modal_edit_user').style.display='block'; }}
            async function actualizarUsuario() {{ const d = {{ id:document.getElementById('eu_id').value, nom:document.getElementById('eu_nombre').value, usr:document.getElementById('eu_user').value, pas:document.getElementById('eu_pass').value, rol:document.getElementById('eu_rol').value }}; await fetch('/api/actualizar_usuario', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d) }}); document.getElementById('modal_edit_user').style.display='none'; cargarUsuarios(); }}
            async function subirCsv() {{ const formData = new FormData(); formData.append('file_csv', document.getElementById('fileCsv').files[0]); const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }}); const data = await res.json(); if(res.ok) {{ alert("✅ Cargado: " + data.count + " registros"); closeAll(); }} }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Nota: ${{nota}}</p><button id="ld_b" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map" style="height:200px; display:none;"></div><img id="im1" class="img-tech" style="width:100%; border-radius:10px; margin-top:10px;"><img id="im2" class="img-tech" style="width:100%; border-radius:10px; margin-top:10px;">`; openModal('modal_detalle'); }}
            async function loadM(id, gps) {{ const res = await fetch('/get_img/'+id); const d = await res.json(); if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }} if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }} if(gps) {{ document.getElementById('map').style.display='block'; const map = L.map('map').setView(gps.split(','), 16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); L.marker(gps.split(',')).addTo(map); }} document.getElementById('ld_b').style.display='none'; }}
        </script>
        {FOOTER_HTML}
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg = request.args.get('msg')
    msg_ok = msg == 'OK'
    msg_fail = msg == 'RANGO'
    
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        
        pv_nombre = request.form.get('pv')
        nuevo_bmb = request.form.get('bmb')
        gps_actual = request.form.get('ubicacion')
        f_val = request.form.get('fecha')
        
        # Buscar Punto de Venta para BMB y Ruta
        punto_doc = puntos_col.find_one({"Punto de Venta": pv_nombre})
        bmb_original = punto_doc.get('BMB') if punto_doc else ""
        ruta_referencia = punto_doc.get('Ruta') if punto_doc else ""
        
        # 1. Auditoría y Actualización de BMB si cambió
        if nuevo_bmb != bmb_original:
            auditoria_col.insert_one({
                "pv": pv_nombre, "fecha": datetime.now(), "usuario": session['user_name'],
                "cambio": f"BMB: {bmb_original} -> {nuevo_bmb}"
            })
            puntos_col.update_one({"Punto de Venta": pv_nombre}, {"$set": {"BMB": nuevo_bmb}})

        # 2. Validación de Distancia (> 100m)
        distancia = calcular_distancia(gps_actual, ruta_referencia)
        estado_visita = "Aprobado"
        if distancia > 100:
            estado_visita = "Pendiente"

        # 3. Actualizar última ubicación en columna Ruta
        puntos_col.update_one({"Punto de Venta": pv_nombre}, {"$set": {"Ruta": gps_actual}})

        # 4. Insertar Visita
        visitas_col.insert_one({
            "pv": pv_nombre, "n_documento": session['user_name'], "fecha": f_val, "mes": f_val[:7], 
            "bmb": nuevo_bmb, "motivo": request.form.get('motivo'), "ubicacion": gps_actual, 
            "distancia": round(distancia, 2), "estado": estado_visita, "Nota": request.form.get('nota'), 
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        
        return redirect('/formulario?msg=OK' if estado_visita == "Aprobado" else '/formulario?msg=RANGO')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p.get("Punto de Venta","")}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div id="over" class="overlay" style="display:{'block' if msg_ok or msg_fail else 'none'};" onclick="location.href='/formulario'"></div>
        <div class="modal-box" style="display:{'block' if msg_ok or msg_fail else 'none'}; text-align:center; max-width:350px;">
            <h1>{'✅' if msg_ok else '⚠️'}</h1>
            <h2>{'¡Éxito!' if msg_ok else 'Fuera de Rango'}</h2>
            <p>{'Visita registrada correctamente.' if msg_ok else 'El POC está a más de 100m. La visita fue enviada a validación.'}</p>
            <button onclick="location.href='/formulario'" class="btn btn-primary">Aceptar</button>
        </div>
        <div class="card" style="max-width:480px;">
            <p style="text-align:center; color:#B7E4C7; margin:0;">Bienvenido, <b>{session['user_name']}</b></p>
            <h2 style="text-align:center; margin-top:5px;">NUEVA VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{options}</datalist>
                <label>BMB (Editable)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label>
                <select name="motivo">
                    <option>Visita a POC</option>
                    <option>Máquina Retirada</option>
                    <option>Punto Cerrado</option>
                    <option>Dificultades Trade</option>
                </select>
                <label>Nota</label><textarea name="nota" rows="2"></textarea>
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g"><button class="btn btn-primary">GUARDAR VISITA</button>
                {f'<a href="/" class="btn btn-gray">VOLVER</a>' if session['role']=='admin' else ''}<a href="/logout" class="btn btn-logout">CERRAR SESIÓN</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ 
                const v = document.getElementById('pv_i').value; 
                const o = document.getElementById('p').childNodes; 
                for (let i=0; i<o.length; i++) if(o[i].value===v) document.getElementById('bmb_i').value=o[i].getAttribute('data-bmb'); 
            }}
        </script>
        {FOOTER_HTML}
    </body></html>
    """)

@app.route('/validacion_visitas')
def validacion_visitas():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pendientes = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f'<tr><td>{r["pv"]}</td><td>{r["n_documento"]}</td><td>{r["distancia"]}m</td><td><button onclick="aprobar(\'{r["_id"]}\')" style="color:#B7E4C7; background:none; border:none; cursor:pointer;">APROBAR</button></td></tr>' for r in pendientes])
    return render_template_string(f"""
    <html><head>{CSS_BI}</head><body>
        <div style="padding:20px;">
            <h2>Validación Visitas POC (>100m)</h2>
            <div style="overflow-x:auto;">
                <table><thead><tr><th>Punto</th><th>Asesor</th><th>Distancia</th><th>Acción</th></tr></thead>
                <tbody>{rows}</tbody></table>
            </div>
            <br><a href="/" class="btn btn-gray">Volver al Menú</a>
        </div>
        <script>
            async function aprobar(id) {{ 
                if(confirm("¿Aprobar esta visita fuera de rango?")) {{
                    await fetch('/api/aprobar_visita/'+id); location.reload(); 
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/api/aprobar_visita/<id>')
def api_aprobar(id):
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    return jsonify({"s": "ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        if lista:
            puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/api/puntos')
def api_puntos(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/usuarios')
def api_users(): u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/actualizar_punto', methods=['POST'])
def up_p(): d = request.json; puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']}); return jsonify({"s": "ok"})
@app.route('/api/actualizar_usuario', methods=['POST'])
def up_u(): d = request.json; usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}}); return jsonify({"s": "ok"})
@app.route('/descargar')
def desc():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Nota', 'Distancia', 'Ubicacion'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('Nota'), r.get('distancia'), r.get('ubicacion')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})
@app.route('/get_img/<id>')
def get_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
