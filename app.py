from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v11_fixed"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS CON FONDO BORROSO Y FOCO ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; overflow-x: hidden; }
    
    .overlay { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); 
        z-index: 2000; 
    }

    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }

    .modal-box { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; 
        padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; box-shadow: 0 0 50px rgba(0,0,0,0.9);
    }

    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    .btn-logout { background: #BC4749; color: white; }

    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    
    .list-item { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; border-left: 5px solid var(--accent); cursor: pointer; }
    #map { height: 250px; width: 100%; border-radius: 15px; margin: 15px 0; display: none; }
    .img-tech { width: 100%; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid var(--accent); }
</style>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>SISTEMA BI</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">Andres BI</h3>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">📍 Gestión de Puntos</div>
            <a href="/descargar" class="nav-link">📊 Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">⚙️ Carga Masiva CSV</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">👥 Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">🚪 Cerrar Sesión</a>
        </div>
        <div class="main-content">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰ MENÚ</button>
            <h2 style="margin-top:20px;">Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>

        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button></div>
        
        <div id="modal_puntos" class="modal-box">
            <h3>📍 Gestión de Puntos</h3>
            <input type="text" id="f_pv" placeholder="Filtrar por nombre..." onkeyup="filtrarPuntos()">
            <div style="overflow-x:auto;"><table><thead><tr><th>Punto</th><th>BMB</th><th>Acción</th></tr></thead><tbody id="puntos_table"></tbody></table></div>
            <div id="edit_punto_form" style="display:none; margin-top:20px; border-top:1px solid var(--accent); padding-top:10px;">
                <input type="hidden" id="ep_id">
                <label>Nombre</label><input type="text" id="ep_nombre">
                <label>BMB</label><input type="text" id="ep_bmb">
                <button class="btn btn-primary" onclick="actualizarPunto()">Guardar Cambios</button>
            </div>
            <button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button>
        </div>

        <div id="modal_csv" class="modal-box">
            <h3>⚙️ Carga Masiva</h3>
            <input type="file" id="fileCsv" accept=".csv">
            <button onclick="subirCsv()" class="btn btn-primary">Procesar Archivo</button>
            <button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button>
        </div>

        <div id="modal_usuarios" class="modal-box">
            <h3>👥 Gestión de Usuarios</h3>
            <table><thead><tr><th>Nombre</th><th>Rol</th><th>Acción</th></tr></thead><tbody id="user_table"></tbody></table>
            <button onclick="closeAll()" class="btn btn-gray">REGRESAR (ESC)</button>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            document.addEventListener('keydown', (e) => {{ if(e.key === "Escape") closeAll(); }});

            function toggleMenu() {{ 
                document.getElementById('sidebar').classList.toggle('active'); 
                document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none';
            }}

            function openModal(id) {{ 
                closeAll();
                document.getElementById('overlay').style.display='block'; 
                document.getElementById(id).style.display='block'; 
                if(id==='modal_puntos') cargarPuntos();
                if(id==='modal_usuarios') cargarUsuarios();
            }}

            function closeAll() {{ 
                document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); 
                document.getElementById('sidebar').classList.remove('active'); 
                document.getElementById('overlay').style.display='none'; 
            }}

            async function cargarPuntos() {{
                const res = await fetch('/api/puntos'); const puntos = await res.json();
                window.allPuntos = puntos; renderPuntos(puntos);
            }}
            function renderPuntos(lista) {{
                document.getElementById('puntos_table').innerHTML = lista.map(p => `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td><td><button onclick='editarPunto(${{JSON.stringify(p)}})' style='color:#B7E4C7; background:none; border:none; cursor:pointer;'>Editar</button></td></tr>`).join('');
            }}
            function filtrarPuntos() {{
                const f = document.getElementById('f_pv').value.toLowerCase();
                renderPuntos(window.allPuntos.filter(p => p['Punto de Venta'].toLowerCase().includes(f)));
            }}
            function editarPunto(p) {{
                document.getElementById('edit_punto_form').style.display='block';
                document.getElementById('ep_id').value=p._id; document.getElementById('ep_nombre').value=p['Punto de Venta']; document.getElementById('ep_bmb').value=p['BMB'];
            }}
            async function actualizarPunto() {{
                await fetch('/api/actualizar_punto', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:document.getElementById('ep_id').value, nom:document.getElementById('ep_nombre').value, bmb:document.getElementById('ep_bmb').value}}) }});
                alert("✅ Punto Actualizado"); cargarPuntos();
            }}

            async function cargarUsuarios() {{
                const res = await fetch('/api/usuarios'); const users = await res.json();
                document.getElementById('user_table').innerHTML = users.map(u => `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td><td>---</td></tr>`).join('');
            }}

            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Nota: ${{nota}}</p><button id="ld_b" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map"></div><img id="im1" class="img-tech"><img id="im2" class="img-tech">`; 
                openModal('modal_detalle'); 
            }}
            async function loadM(id, gps) {{ 
                const res = await fetch('/get_img/'+id); const d = await res.json(); 
                if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }} 
                if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }} 
                if(gps) {{ document.getElementById('map').style.display='block'; const map = L.map('map').setView(gps.split(','), 16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); L.marker(gps.split(',')).addTo(map); }} 
                document.getElementById('ld_b').style.display='none'; 
            }}
            async function subirCsv() {{
                const formData = new FormData(); formData.append('file_csv', document.getElementById('fileCsv').files[0]);
                const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }});
                const data = await res.json();
                if(res.ok) alert("✅ Cargado: " + data.count + " registros");
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg_ok = request.args.get('msg') == 'OK'
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        f_val = request.form.get('fecha')
        visitas_col.insert_one({
            "pv": request.form.get('pv'), "n_documento": session['user_name'], "fecha": f_val, "mes": f_val[:7], 
            "bmb": request.form.get('bmb'), "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'), 
            "Nota": request.form.get('nota'), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div id="over" class="overlay" style="display:{'block' if msg_ok else 'none'};" onclick="location.href='/formulario'"></div>
        <div class="modal-box" style="display:{'block' if msg_ok else 'none'}; text-align:center; max-width:350px;">
            <h1 style="font-size:60px; margin:0;">✅</h1><h2>¡Éxito!</h2>
            <button onclick="location.href='/formulario'" class="btn btn-primary">Aceptar</button>
        </div>
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center; color:#B7E4C7; margin-top:0;">REPORTE DE VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{options}</datalist>
                <label>BMB</label><input type="text" name="bmb" id="bmb_i" readonly style="opacity:0.6;">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Dificultades Trade</option><option>Fuera de rango</option></select>
                <label>Nota</label><textarea name="nota" rows="2"></textarea>
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">GUARDAR REGISTRO</button>
                {f'<a href="/" class="btn btn-gray">VOLVER PANEL</a>' if session['role']=='admin' else ''}
                <a href="/logout" class="btn btn-logout">CERRAR SESIÓN</a>
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
    </body></html>
    """)

@app.route('/api/puntos')
def api_puntos():
    p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]
    return jsonify(p)

@app.route('/api/actualizar_punto', methods=['POST'])
def update_p():
    data = request.json
    puntos_col.update_one({"_id": ObjectId(data['id'])}, {"$set": {"Punto de Venta": data['nom'], "BMB": data['bmb']}})
    return jsonify({"status": "ok"})

@app.route('/api/usuarios')
def api_users():
    users = list(usuarios_col.find()); [u.update({"_id": str(u["_id"])}) for u in users]
    return jsonify(users)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Nota'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('Nota')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/get_img/<id>')
def get_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
