from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_pro_2026_andres"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS FUTURISTA ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
    .container { width: 100%; max-width: 1200px; margin: auto; }
    .card { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05); }
    .btn { padding: 12px 20px; border-radius: 12px; font-weight: 700; cursor: pointer; border: none; transition: 0.3s; text-decoration: none; display: inline-block; text-align: center; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-outline { background: white; color: var(--primary); border: 1.5px solid var(--primary); width: 100%; }
    .btn-admin { background: #10B981; color: white; margin-top: 10px; }
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1.5px solid #E2E8F0; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
    input[readonly] { background: #F8FAFC; color: #94A3B8; border-style: dashed; }
    .list-item { background: white; padding: 20px; border-radius: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 6px solid var(--primary); transition: 0.2s; }
    .list-item:hover { transform: scale(1.01); box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
    #modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,44,95,0.25); backdrop-filter: blur(10px); z-index: 1000; align-items: center; justify-content: center; padding: 20px; }
    .modal-content { background: white; width: 100%; max-width: 850px; border-radius: 24px; padding: 35px; max-height: 90vh; overflow-y: auto; position: relative; }
    #map { height: 300px; width: 100%; border-radius: 18px; margin: 15px 0; display: none; border: 1px solid #ddd; }
    .img-tech { width: 100%; border-radius: 15px; margin-top: 15px; display: none; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
</style>
"""

# --- SEGURIDAD ---
def check_auth(): return 'user_id' in session

# --- RUTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh; background:var(--dark);'><div class='card' style='width:340px; text-align:center;'><h2 style='color:var(--dark)'>Andres BI System</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario' required><input type='password' name='password' placeholder='Contraseña' required><button class='btn btn-primary'>Iniciar Sesión</button></form></div></body></html>")

@app.route('/')
def index():
    if not check_auth(): return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    # Vista Administrador
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}")\'><div><b style="font-size:18px;">{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="font-weight:bold; color:var(--primary);">{r.get("bmb")}</div></div>' for r in cursor])

    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div class="container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px;">
                <h1 style="color:var(--dark); margin:0;">Panel Inteligente</h1>
                <div style="text-align:right;"><small>👤 {session['user_name']}</small><br><a href="/logout" style="color:red; text-decoration:none; font-size:12px;">Cerrar Sesión</a></div>
            </div>
            
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-bottom:30px;">
                <a href="/formulario" class="btn btn-primary">＋ Nuevo Registro</a>
                <a href="/descargar" class="btn btn-outline">📊 Reporte Visitas</a>
                <button onclick="openModal('modal_admin')" class="btn btn-admin">⚙️ Gestión Datos</button>
            </div>
            
            <div id="lista_registros">{rows}</div>
        </div>

        <div id="modal_detalle" id="modal" onclick="closeModal('modal_detalle')">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="det_body"></div>
                <button onclick="closeModal('modal_detalle')" class="btn btn-outline" style="margin-top:20px; color:red; border-color:red;">Cerrar Detalle</button>
            </div>
        </div>

        <div id="modal_admin" id="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); backdrop-filter:blur(5px); z-index:2000; align-items:center; justify-content:center;">
            <div class="card" style="width:90%; max-width:500px; max-height:85vh; overflow-y:auto;">
                <h2 style="margin-top:0;">Gestión de Sistema</h2>
                
                <h4 style="border-bottom: 2px solid var(--primary); padding-bottom:5px;">Carga de Puntos de Venta</h4>
                <a href="/descargar_plantilla" class="btn btn-outline" style="font-size:12px; padding:8px; margin-bottom:10px;">⬇️ Bajar Plantilla CSV</a>
                <form action="/carga_masiva_puntos" method="POST" enctype="multipart/form-data">
                    <input type="file" name="file_csv" accept=".csv" required>
                    <button class="btn btn-primary">Subir y Reemplazar PDVs</button>
                </form>

                <h4 style="border-bottom: 2px solid var(--primary); padding-bottom:5px; margin-top:30px;">Crear Nuevo Usuario</h4>
                <form action="/crear_usuario" method="POST">
                    <input type="text" name="nombre" placeholder="Nombre Completo" required>
                    <input type="text" name="user" placeholder="ID Usuario (Login)" required>
                    <input type="password" name="pass" placeholder="Contraseña" required>
                    <select name="rol"><option value="asesor">Rol: Asesor (Campo)</option><option value="admin">Rol: Administrador</option></select>
                    <button class="btn btn-admin" style="width:100%;">Registrar Usuario</button>
                </form>
                
                <button onclick="closeModal('modal_admin')" class="btn btn-outline" style="margin-top:20px;">Cerrar Gestión</button>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapObj = null;
            function openModal(id) {{ document.getElementById(id).style.display='flex'; }}
            function closeModal(id) {{ document.getElementById(id).style.display='none'; }}

            function verDetalle(id, pv, f, doc, mot, gps, bmb) {{
                document.getElementById('det_body').innerHTML = `
                    <h2 style="color:var(--dark); margin:0;">${{pv}}</h2>
                    <hr style="opacity:0.1; margin:15px 0;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:14px;">
                        <p><b>Asesor:</b><br>${{doc}}</p><p><b>Fecha:</b><br>${{f}}</p>
                        <p><b>Dato BMB:</b><br>${{bmb}}</p><p><b>Motivo:</b><br>${{mot}}</p>
                    </div>
                    <button id="load_btn" class="btn btn-primary" onclick="getMedia('${{id}}','${{gps}}')">Cargar Evidencia Visual</button>
                    <div id="map"></div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <img id="im1" class="img-tech"><img id="im2" class="img-tech">
                    </div>`;
                openModal('modal_detalle');
            }}

            async function getMedia(id, gps) {{
                document.getElementById('load_btn').innerText = "Sincronizando...";
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }}
                if(gps) {{
                    document.getElementById('map').style.display='block';
                    const l = gps.split(',').map(Number);
                    if(mapObj) mapObj.remove();
                    mapObj = L.map('map').setView(l, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapObj);
                    L.marker(l).addTo(mapObj);
                    setTimeout(() => mapObj.invalidateSize(), 400);
                }}
                document.getElementById('load_btn').style.display='none';
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if not check_auth(): return redirect('/login')
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
    alert = '<div style="background:#dcfce7; color:#166534; padding:15px; border-radius:12px; margin-bottom:15px;">✅ Reporte enviado con éxito.</div>' if request.args.get('msg') else ""

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()">
        <div class="container" style="max-width:550px;">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    {f'<a href="/" style="text-decoration:none;">⬅️ Volver</a>' if session['role']=='admin' else '<span></span>'}
                    <h3 style="margin:0;">Nuevo Reporte</h3>
                    <a href="/logout" style="color:red; text-decoration:none; font-size:12px;">Cerrar</a>
                </div>
                <hr style="opacity:0.1; margin:15px 0;">
                {alert}
                <form method="POST" enctype="multipart/form-data">
                    <label style="font-size:12px; font-weight:700;">Seleccionar Punto de Venta</label>
                    <input list="pdvs" name="pv" placeholder="Escriba para buscar..." required>
                    <datalist id="pdvs">{options}</datalist>
                    
                    <label style="font-size:12px; font-weight:700;">Responsable</label>
                    <input type="text" value="{session['user_name']}" readonly>
                    
                    <label style="font-size:12px; font-weight:700;">Fecha</label>
                    <input type="date" name="fecha" value="{today}" required>
                    
                    <label style="font-size:12px; font-weight:700;">Dato BMB</label>
                    <input type="text" name="bmb" placeholder="Ingrese el valor" required>
                    
                    <label style="font-size:12px; font-weight:700;">Motivo</label>
                    <select name="motivo" required><option value="">Elegir...</option><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Fuera de Rango</option></select>
                    
                    <input type="hidden" name="ubicacion" id="gps">
                    <div id="gps_st" style="font-size:11px; color:orange;">📍 Obteniendo GPS...</div>
                    
                    <label style="display:block; margin-top:15px; font-size:12px; font-weight:700;">📸 Foto BMB (Obligatoria)</label>
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    
                    <label style="display:block; margin-top:10px; font-size:12px; font-weight:700;">📸 Foto Fachada (Obligatoria)</label>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    
                    <button type="submit" class="btn btn-primary" style="margin-top:25px;">Finalizar Reporte</button>
                </form>
            </div>
        </div>
        <script>
            function getGPS() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('gps').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps_st').innerText = "✅ GPS Vinculado";
                    document.getElementById('gps_st').style.color = "green";
                }}, () => {{ alert("Por favor activa el GPS."); }}, {{enableHighAccuracy:true}});
            }}
        </script>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga_masiva():
    if not check_auth() or session['role'] != 'admin': return redirect('/')
    file = request.files.get('file_csv')
    if file:
        content = file.stream.read().decode("UTF8")
        # DETECTOR AUTOMÁTICO DE DELIMITADOR (, o ;)
        dialect = csv.Sniffer().sniff(content[:1024])
        stream = io.StringIO(content)
        reader = csv.DictReader(stream, dialect=dialect)
        puntos_col.delete_many({})
        puntos_col.insert_many(list(reader))
    return redirect('/')

@app.route('/crear_usuario', methods=['POST'])
def crear_user():
    if not check_auth() or session['role'] != 'admin': return redirect('/')
    usuarios_col.insert_one({
        "usuario": request.form.get('user'), "password": request.form.get('pass'),
        "nombre_completo": request.form.get('nombre'), "rol": request.form.get('rol')
    })
    return redirect('/')

@app.route('/descargar_plantilla')
def plantilla():
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Id', 'Punto de Venta', 'Departamento', 'Ciudad', 'BMB'])
    w.writerow(['1', 'Tienda Ejemplo', 'Bogotá', 'Bogotá', '0'])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Plantilla_PDV.csv"})

@app.route('/get_img/<id>')
def get_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/descargar')
def descargar():
    if not check_auth() or session['role'] != 'admin': return redirect('/')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto de Venta', 'Asesor', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicación'])
    for r in cursor: w.writerow([r.get('pv',''), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), r.get('bmb',''), r.get('motivo',''), r.get('ubicacion','')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
