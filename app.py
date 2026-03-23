from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_sidebar_2026"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS CON SIDEBAR DINÁMICO ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; --sidebar-w: 280px; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; overflow-x: hidden; }
    
    /* Sidebar Estilo */
    .sidebar { 
        position: fixed; left: calc(-1 * var(--sidebar-w)); top: 0; width: var(--sidebar-w); height: 100%; 
        background: var(--dark); color: white; transition: 0.3s ease; z-index: 2000; padding: 25px; box-sizing: border-box;
        box-shadow: 10px 0 30px rgba(0,0,0,0.2);
    }
    .sidebar.active { left: 0; }
    .sidebar h2 { color: #60A5FA; font-size: 22px; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
    .nav-link { 
        display: block; color: #E2E8F0; text-decoration: none; padding: 15px; border-radius: 12px; 
        margin-bottom: 8px; font-weight: 600; transition: 0.2s; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px;
    }
    .nav-link:hover { background: rgba(255,255,255,0.1); color: white; transform: translateX(5px); }
    .nav-link.logout { color: #F87171; margin-top: 40px; }

    /* Contenido Principal */
    .main-content { width: 100%; padding: 20px; transition: 0.3s; margin-left: 0; }
    .header-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; }
    .menu-toggle { background: var(--primary); color: white; border: none; padding: 10px 15px; border-radius: 10px; cursor: pointer; font-size: 20px; }

    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { padding: 12px 20px; border-radius: 12px; font-weight: 700; cursor: pointer; border: none; transition: 0.3s; text-decoration: none; display: inline-block; text-align: center; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    
    .list-item { background: white; padding: 20px; border-radius: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 6px solid var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    
    /* Modales y Overlays */
    .overlay { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.4); backdrop-filter: blur(8px); z-index: 1500; 
    }
    #modal_detalle, #modal_admin { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 90%; max-width: 800px; z-index: 3000; 
    }
    .modal-content { background: white; border-radius: 24px; padding: 30px; max-height: 85vh; overflow-y: auto; }
    
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1.5px solid #E2E8F0; border-radius: 12px; font-size: 16px; }
    #map { height: 300px; width: 100%; border-radius: 18px; margin: 15px 0; display: none; }
    .img-tech { width: 100%; border-radius: 15px; margin-top: 15px; display: none; }
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center; background:var(--dark);'><div class='card' style='width:320px; margin:auto; margin-top:15vh; text-align:center;'><h2>BI Login</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Pass'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:var(--primary); font-weight:bold;">{r.get("bmb")}</div></div>' for r in cursor])

    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div id="sidebar_overlay" class="overlay" onclick="toggleMenu()"></div>
        
        <div id="sidebar" class="sidebar">
            <h2>Menú Control</h2>
            <a href="/formulario" class="nav-link">📝 Nuevo Registro</a>
            <a href="/descargar" class="nav-link">📊 Reporte de Visitas</a>
            <div class="nav-link" onclick="openAdmin()">⚙️ Carga Masiva PDV</div>
            <div class="nav-link" onclick="openAdmin()">👥 Crear Usuario</div>
            <a href="/logout" class="nav-link logout">🚪 Cerrar Sesión</a>
            <div style="position:absolute; bottom:20px; font-size:10px; opacity:0.5;">BI System v2.0 - Andres</div>
        </div>

        <div class="main-content">
            <div class="header-bar">
                <button class="menu-toggle" onclick="toggleMenu()">☰</button>
                <h2 style="margin:0; color:var(--dark);">Registros de Visitas</h2>
            </div>
            
            <div id="lista">{rows}</div>
        </div>

        <div id="modal_detalle" class="modal-content" style="display:none; position:fixed;">
            <div id="det_body"></div>
            <button onclick="closeModal('modal_detalle')" class="btn btn-primary" style="background:gray; margin-top:15px;">Cerrar</button>
        </div>

        <div id="modal_admin" class="modal-content" style="display:none; position:fixed;">
            <h3>Herramientas Administrativas</h3>
            <hr>
            <h4>1. Puntos de Venta</h4>
            <a href="/descargar_plantilla" style="font-size:12px; color:var(--primary);">Descargar Plantilla CSV</a>
            <form action="/carga_masiva_puntos" method="POST" enctype="multipart/form-data">
                <input type="file" name="file_csv" accept=".csv" required>
                <button class="btn btn-primary" style="background:#10B981;">Actualizar Base PDV</button>
            </form>
            <br>
            <h4>2. Registro de Usuarios</h4>
            <form action="/crear_usuario" method="POST">
                <input type="text" name="nombre" placeholder="Nombre Completo" required>
                <input type="text" name="user" placeholder="Usuario Login" required>
                <input type="password" name="pass" placeholder="Password" required>
                <select name="rol"><option value="asesor">Asesor</option><option value="admin">Administrador</option></select>
                <button class="btn btn-primary">Guardar Usuario</button>
            </form>
            <button onclick="closeModal('modal_admin')" class="btn btn-primary" style="background:gray; margin-top:20px;">Cerrar</button>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{
                document.getElementById('sidebar').classList.toggle('active');
                const overlay = document.getElementById('sidebar_overlay');
                overlay.style.display = overlay.style.display === 'block' ? 'none' : 'block';
            }}
            function openAdmin() {{ toggleMenu(); document.getElementById('modal_admin').style.display='block'; }}
            function closeModal(id) {{ document.getElementById(id).style.display='none'; }}

            function verDetalle(id, pv, f, doc, mot, gps, bmb) {{
                document.getElementById('det_body').innerHTML = `
                    <h3>${{pv}}</h3>
                    <p><b>Fecha:</b> ${{f}} | <b>BMB:</b> ${{bmb}}</p>
                    <p><b>Asesor:</b> ${{doc}}<br><b>Motivo:</b> ${{mot}}</p>
                    <button id="btn_m" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Ver Fotos y Mapa</button>
                    <div id="map"></div>
                    <img id="m1" class="img-tech"><img id="m2" class="img-tech">`;
                document.getElementById('modal_detalle').style.display='block';
            }}

            async function loadM(id, gps) {{
                document.getElementById('btn_m').innerText = "Cargando...";
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                if(d.f1) {{ document.getElementById('m1').src=d.f1; document.getElementById('m1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('m2').src=d.f2; document.getElementById('m2').style.display='block'; }}
                if(gps) {{
                    document.getElementById('map').style.display='block';
                    const l = gps.split(',').map(Number);
                    const map = L.map('map').setView(l, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                    L.marker(l).addTo(map);
                }}
                document.getElementById('btn_m').style.display='none';
            }}
        </script>
    </body>
    </html>
    """)

# --- LAS DEMÁS RUTAS (FORMULARIO, CARGA, ETC.) SE MANTIENEN IGUAL QUE ANTES ---
@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(file):
            if file and file.filename != '':
                return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode()}"
            return ""
        f = request.form.get('fecha')
        visitas_col.insert_one({
            "pv": request.form.get('pv'), "n_documento": session['user_name'],
            "fecha": f, "mes": f[:7], "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        if session['role'] == 'asesor': return redirect('/formulario?msg=OK')
        return redirect('/')
    
    puntos = puntos_col.find({}, {"Punto de Venta": 1})
    options = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos])
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_BI}</head><body onload='getGPS()'><div class='container' style='max-width:500px;'><div class='card'><h3>Nuevo Registro</h3><form method='POST' enctype='multipart/form-data'><input list='p' name='pv' placeholder='Punto de Venta' required><datalist id='p'>{options}</datalist><input type='text' value='{session['user_name']}' readonly><input type='date' name='fecha' value='{today}'><input type='text' name='bmb' placeholder='BMB' required><select name='motivo'><option>Máquina Retirada</option><option>Punto Cerrado</option></select><input type='hidden' name='ubicacion' id='g'><div id='gs'>📍 Ubicando...</div><br><label>Foto BMB</label><input type='file' name='f1' accept='image/*' capture='camera' required><label>Foto Fachada</label><input type='file' name='f2' accept='image/*' capture='camera' required><button class='btn btn-primary'>Enviar</button></form></div><a href='/logout' style='color:red;'>Salir</a></div><script>function getGPS(){{navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude; document.getElementById('gs').innerText='✅ GPS OK';}},()=>{{alert('Activa GPS');}},{{enableHighAccuracy:true}});}}</script></body></html>")

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    file = request.files.get('file_csv')
    if file:
        content = file.stream.read().decode("UTF8")
        dialect = csv.Sniffer().sniff(content[:1024])
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        puntos_col.delete_many({})
        puntos_col.insert_many(list(reader))
    return redirect('/')

@app.route('/crear_usuario', methods=['POST'])
def c_user():
    usuarios_col.insert_one({"usuario": request.form.get('user'), "password": request.form.get('pass'), "nombre_completo": request.form.get('nombre'), "rol": request.form.get('rol')})
    return redirect('/')

@app.route('/descargar_plantilla')
def plant():
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Id', 'Punto de Venta', 'Departamento', 'Ciudad', 'BMB'])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Plantilla.csv"})

@app.route('/get_img/<id>')
def get_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto de Venta', 'Asesor', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicación'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('mes'), r.get('bmb'), r.get('motivo'), r.get('ubicacion')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte.csv"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
