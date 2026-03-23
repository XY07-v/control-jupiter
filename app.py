from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_ultimate_2026"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS MEJORADO (DISEÑO CENTRADO Y BLUR) ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; --sidebar-w: 280px; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; }
    
    .sidebar { 
        position: fixed; left: -280px; top: 0; width: var(--sidebar-w); height: 100%; 
        background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box;
    }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #E2E8F0; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: rgba(255,255,255,0.1); color: white; }

    .main-content { width: 100%; padding: 20px; transition: 0.3s; }
    .header-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; }
    .menu-toggle { background: var(--primary); color: white; border: none; padding: 12px 18px; border-radius: 10px; cursor: pointer; font-size: 20px; }

    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { padding: 12px 20px; border-radius: 12px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; text-decoration: none; display: inline-block; text-align: center; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-gray { background: #64748B; color: white; width: 100%; margin-top: 10px; }

    /* Overlay para desenfoque de fondo */
    .overlay { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.3); backdrop-filter: blur(10px); z-index: 2000; 
    }

    /* Modales Centrados */
    .modal-box { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 90%; max-width: 600px; z-index: 2500; background: white; border-radius: 24px; padding: 35px; 
        max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    }
    
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1.5px solid #E2E8F0; border-radius: 12px; font-size: 16px; box-sizing: border-box; }
    .list-item { background: white; padding: 20px; border-radius: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 6px solid var(--primary); }
    
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center; background:var(--dark); display:flex; height:100vh;'><div class='card' style='width:340px; text-align:center;'><h2>BI System</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

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
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        
        <div id="sidebar" class="sidebar">
            <h2>Panel Andres</h2>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <a href="/descargar" class="nav-link">📊 Descargar Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">⚙️ Carga Puntos PDV</div>
            <div class="nav-link" onclick="openModal('modal_user')">👤 Crear Usuario</div>
            <a href="/logout" class="nav-link" style="color:#F87171; margin-top:50px;">🚪 Cerrar Sesión</a>
        </div>

        <div class="main-content">
            <div class="header-bar">
                <button class="menu-toggle" onclick="toggleMenu()">☰ Menu</button>
                <h2 style="margin:0;">Registros Recientes</h2>
            </div>
            <div id="lista">{rows}</div>
        </div>

        <div id="modal_detalle" class="modal-box">
            <div id="det_body"></div>
            <button onclick="closeModal('modal_detalle')" class="btn btn-gray">Regresar</button>
        </div>

        <div id="modal_csv" class="modal-box">
            <h3>Carga Masiva de Puntos</h3>
            <a href="/descargar_plantilla" style="color:var(--primary); font-size:13px;">Descargar Formato CSV</a>
            <form action="/carga_masiva_puntos" method="POST" enctype="multipart/form-data">
                <input type="file" name="file_csv" accept=".csv" required>
                <button class="btn btn-primary">Actualizar Base</button>
            </form>
            <button onclick="closeModal('modal_csv')" class="btn btn-gray">Cancelar / Regresar</button>
        </div>

        <div id="modal_user" class="modal-box">
            <h3>Registrar Nuevo Usuario</h3>
            <form action="/crear_usuario" method="POST">
                <input type="text" name="nombre" placeholder="Nombre Completo" required>
                <input type="text" name="user" placeholder="ID de Usuario" required>
                <input type="password" name="pass" placeholder="Password" required>
                <select name="rol"><option value="asesor">Asesor</option><option value="admin">Administrador</option></select>
                <button class="btn btn-primary">Guardar Usuario</button>
            </form>
            <button onclick="closeModal('modal_user')" class="btn btn-gray">Regresar</button>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ 
                document.getElementById('sidebar').classList.toggle('active'); 
                document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none';
            }}
            function openModal(id) {{ 
                closeAll();
                document.getElementById('overlay').style.display = 'block';
                document.getElementById(id).style.display = 'block';
            }}
            function closeModal(id) {{ 
                document.getElementById(id).style.display = 'none';
                if (!document.getElementById('sidebar').classList.contains('active')) document.getElementById('overlay').style.display = 'none';
            }}
            function closeAll() {{
                document.querySelectorAll('.modal-box').forEach(m => m.style.display = 'none');
                document.getElementById('sidebar').classList.remove('active');
                document.getElementById('overlay').style.display = 'none';
            }}

            // ESC para cerrar ventanas
            window.addEventListener('keydown', e => {{ if(e.key === 'Escape') closeAll(); }});

            function verDetalle(id, pv, f, doc, mot, gps, bmb) {{
                document.getElementById('det_body').innerHTML = `
                    <h3>${{pv}}</h3>
                    <p><b>Fecha:</b> ${{f}} | <b>BMB:</b> ${{bmb}}</p>
                    <p><b>Asesor:</b> ${{doc}}<br><b>Motivo:</b> ${{mot}}</p>
                    <button id="ld_b" class="btn btn-primary" onclick="loadM('${{id}}','${{gps}}')">Consultar Evidencia</button>
                    <div id="map"></div>
                    <img id="im1" class="img-tech"><img id="im2" class="img-tech">`;
                openModal('modal_detalle');
            }}

            async function loadM(id, gps) {{
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }}
                if(gps) {{
                    document.getElementById('map').style.display='block';
                    const map = L.map('map').setView(gps.split(','), 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                    L.marker(gps.split(',')).addTo(map);
                }}
                document.getElementById('ld_b').style.display='none';
            }}
        </script>
    </body>
    </html>
    """)

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
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="justify-content:center; align-items:center; display:flex;">
        <div class="container" style="max-width:550px; width:100%;">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    {f'<a href="/" style="text-decoration:none; color:var(--primary); font-weight:700;">← Regresar</a>' if session['role']=='admin' else '<span></span>'}
                    <h3 style="margin:0;">Registro Visita</h3>
                    <a href="/logout" style="color:red; text-decoration:none;">Salir</a>
                </div>
                <hr style="opacity:0.1; margin:15px 0;">
                <form method="POST" enctype="multipart/form-data">
                    <input list="p" name="pv" placeholder="Punto de Venta" required><datalist id="p">{options}</datalist>
                    <input type="text" value="{session['user_name']}" readonly>
                    <input type="date" name="fecha" value="{today}">
                    <input type="text" name="bmb" placeholder="Dato BMB (-1 o vacío)" required>
                    <select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                    <input type="hidden" name="ubicacion" id="g">
                    <div id="gs" style="font-size:11px; color:green;">📍 Localizando...</div>
                    <br><label style="font-size:12px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:12px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <button class="btn btn-primary">Finalizar y Enviar</button>
                    {f'<a href="/" class="btn btn-gray" style="display:block;">Cancelar y Volver</a>' if session['role']=='admin' else ''}
                </form>
            </div>
        </div>
        <script>function getGPS(){{navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude; document.getElementById('gs').innerText='✅ GPS Listo';}},null,{{enableHighAccuracy:true}});}}</script>
    </body></html>
    """)

# (Rutas de carga_masiva, crear_usuario, etc. se mantienen igual)
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
