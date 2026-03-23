from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_verde_final_v7"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- DISEÑO VERDE OSCURO ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { 
        font-family: 'Segoe UI', sans-serif; 
        background: radial-gradient(circle, #1b4332 0%, #081c15 100%); 
        margin: 0; display: flex; color: white; min-height: 100vh;
    }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    
    .profile-badge { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 8px 15px; border-radius: 30px; border: 1px solid var(--accent); display: flex; flex-direction: column; align-items: flex-end; z-index: 1000; }
    .profile-badge b { color: #D8F3DC; font-size: 14px; }
    
    .main-content { width: 100%; padding: 20px; transition: 0.3s; position: relative; }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border-radius: 24px; padding: 30px; border: 1px solid rgba(255,255,255,0.1); box-sizing: border-box; width: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
    
    .btn { width: 100%; padding: 14px; border-radius: 12px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; text-decoration: none; display: inline-block; font-size: 14px; box-sizing: border-box; margin-top: 15px; text-align: center; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-logout { background: #BC4749; color: white; }
    
    label { display: block; margin-top: 12px; font-size: 13px; color: #B7E4C7; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid var(--accent); border-radius: 10px; background: rgba(0,0,0,0.2); color: white; box-sizing: border-box; }
    
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2500; }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 700px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 85vh; overflow-y: auto; }
    
    .list-item { background: rgba(255,255,255,0.05); padding: 18px; border-radius: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 5px solid var(--accent); }
    #map { height: 250px; width: 100%; border-radius: 15px; margin: 15px 0; display: none; }
    .img-tech { width: 100%; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid var(--accent); }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .debug-box { background: #000; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 11px; margin-top: 15px; display: none; white-space: pre; }
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>SISTEMA POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

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
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7;">Andres BI</h3>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <a href="/descargar" class="nav-link">📊 Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">⚙️ Carga Puntos PDV</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">👥 Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">🚪 Cerrar Sesión</a>
        </div>
        <div class="main-content">
            <button onclick="document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display='block';" style="background:none; border:none; color:white; font-size:24px;">☰</button>
            <h2 style="margin-top:20px;">Visitas Recientes</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeModal('modal_detalle')" class="btn btn-gray">Cerrar</button></div>
        
        <div id="modal_csv" class="modal-box">
            <h3>Carga Masiva de Puntos</h3>
            <input type="file" id="fileCsv" accept=".csv">
            <div id="debug" class="debug-box"></div>
            <button type="button" onclick="subirCsv()" class="btn btn-primary">Actualizar Base PDV</button>
            <button onclick="closeModal('modal_csv')" class="btn btn-gray">Cerrar</button>
        </div>

        <div id="modal_usuarios" class="modal-box">
            <div style="display:flex; justify-content:space-between;"><h3>Usuarios</h3><button onclick="document.getElementById('form_user').style.display='block';" class="btn btn-primary" style="width:auto;">+ Nuevo</button></div>
            <div id="form_user" style="display:none; margin-bottom:20px;">
                <form action="/guardar_usuario" method="POST">
                    <input type="hidden" name="id" id="edit_id"><input type="text" name="nombre" id="edit_nom" placeholder="Nombre" required><input type="text" name="user" id="edit_usr" placeholder="Usuario" required><input type="password" name="pass" id="edit_pas" placeholder="Pass" required><select name="rol" id="edit_rol"><option value="asesor">Asesor</option><option value="admin">Admin</option></select><button class="btn btn-primary">Guardar</button>
                </form>
            </div>
            <table><thead><tr><th>Nombre</th><th>Rol</th><th>Acción</th></tr></thead><tbody id="user_table"></tbody></table>
            <button onclick="closeModal('modal_usuarios')" class="btn btn-gray">Regresar</button>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function openModal(id) {{ document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeModal(id) {{ document.getElementById(id).style.display='none'; document.getElementById('overlay').style.display='none'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            
            async function subirCsv() {{
                const formData = new FormData(); formData.append('file_csv', document.getElementById('fileCsv').files[0]);
                const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }});
                const data = await res.json();
                document.getElementById('debug').style.display = 'block'; document.getElementById('debug').innerText = "VISTA PREVIA:\\n" + data.preview;
                if(res.ok) alert("✅ Cargado con éxito: " + data.count + " registros");
            }}

            async function cargarUsuarios() {{
                const res = await fetch('/api/usuarios'); const users = await res.json();
                document.getElementById('user_table').innerHTML = users.map(u => `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td><td><button onclick='editarU(${{JSON.stringify(u)}})' style='color:#95D5B2; background:none; border:none;'>Editar</button></td></tr>`).join('');
            }}
            function editarU(u) {{ document.getElementById('form_user').style.display='block'; document.getElementById('edit_id').value=u._id; document.getElementById('edit_nom').value=u.nombre_completo; document.getElementById('edit_usr').value=u.usuario; document.getElementById('edit_pas').value=u.password; document.getElementById('edit_rol').value=u.rol; }}

            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p><b>BMB:</b> ${{bmb}}<br><b>Fecha:</b> ${{f}}<br><b>Asesor:</b> ${{doc}}</p><p><b>Nota:</b> ${{nota}}</p><button id="ld_b" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Fotos y Mapa</button><div id="map"></div><img id="im1" class="img-tech"><img id="im2" class="img-tech">`; 
                openModal('modal_detalle'); 
            }}
            async function loadM(id, gps) {{ 
                const res = await fetch('/get_img/'+id); const d = await res.json(); 
                if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }} 
                if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }} 
                if(gps) {{ document.getElementById('map').style.display='block'; const map = L.map('map').setView(gps.split(','), 16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); L.marker(gps.split(',')).addTo(map); }} 
                document.getElementById('ld_b').style.display='none'; 
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
    <body onload="getGPS()" style="justify-content:center; align-items:center; display:flex; padding:20px;">
        <div class="profile-badge"><b>{session['user_name']}</b></div>
        
        <div id="over" class="overlay" style="display:{'block' if msg_ok else 'none'};" onclick="location.href='/formulario'"></div>
        <div class="modal-box" style="display:{'block' if msg_ok else 'none'}; text-align:center;">
            <h1 style="font-size:60px; margin:0;">✅</h1>
            <h2>¡Registro Exitoso!</h2>
            <button onclick="location.href='/formulario'" class="btn btn-primary">Aceptar</button>
        </div>

        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center; color:#B7E4C7; margin-top:0;">REPORTE DE VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{options}</datalist>
                
                <label>Dato BMB (Auto)</label>
                <input type="text" name="bmb" id="bmb_i" readonly style="background:rgba(255,255,255,0.05);">
                
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                
                <label>Motivo</label>
                <select name="motivo">
                    <option>Máquina Retirada</option><option>Punto Cerrado</option>
                    <option>Dificultades Trade</option><option>Fuera de rango</option>
                </select>
                
                <label>Observaciones (Nota)</label>
                <textarea name="nota" rows="2" placeholder="Escriba aquí..."></textarea>
                
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">ENVIAR REGISTRO</button>
                {f'<a href="/" class="btn btn-gray" style="background:#64748B; color:white;">Volver al Panel</a>' if session['role']=='admin' else ''}
                <a href="/logout" class="btn btn-logout">SALIDA / DESLOGUEO</a>
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

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"preview": content[:150], "count": len(lista)})
    return jsonify({"preview": "Error"}), 400

@app.route('/get_img/<id>')
def get_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/api/usuarios')
def api_users():
    users = list(usuarios_col.find()); [u.update({"_id": str(u["_id"])}) for u in users]
    return jsonify(users)

@app.route('/guardar_usuario', methods=['POST'])
def guardar_u():
    u_id, nom, usr, pas, rol = request.form.get('id'), request.form.get('nombre'), request.form.get('user'), request.form.get('pass'), request.form.get('rol')
    d = {"nombre_completo": nom, "usuario": usr, "password": pas, "rol": rol}
    if u_id: usuarios_col.update_one({"_id": ObjectId(u_id)}, {"$set": d})
    else: usuarios_col.insert_one(d)
    return redirect('/')

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Nota'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('Nota')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte.csv"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
