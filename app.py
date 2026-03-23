from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_futuristic_control_2026"

# --- CONFIGURACIÓN DE MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']
usuarios_col = db['usuarios']

# --- ESTILOS ---
CSS_PRO = """
<style>
    :root {
        --primary: #005596;
        --dark: #002C5F;
        --bg: #F8FAFC;
    }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 20px; }
    .container { width: 100%; max-width: 1200px; margin: auto; }
    .card { background: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; display: inline-block; border: none; cursor: pointer; text-align: center; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-outline { background: white; color: var(--primary); border: 1px solid var(--primary); width: 100%; }
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1px solid #E2E8F0; border-radius: 10px; box-sizing: border-box; }
    input[readonly] { background: #F1F5F9; color: #64748B; cursor: not-allowed; }
    .list-item { background: white; padding: 20px; border-radius: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 5px solid var(--primary); }
    #map { height: 250px; width: 100%; border-radius: 15px; margin: 15px 0; display: none; }
    .img-tech { width: 100%; border-radius: 12px; margin-top: 15px; display: none; }
</style>
"""

def check_auth():
    return 'user_id' in session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('nombre_completo', u)
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_PRO}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh; background:var(--dark);'><div class='card' style='width:300px;'><h2>Acceso</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Contraseña'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/')
def index():
    if not check_auth(): return redirect('/login')
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    
    rows = ""
    for r in cursor:
        rows += f"""
        <div class="list-item" onclick='verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}")'>
            <div><b>{r.get('pv')}</b><br><small>{r.get('fecha')}</small></div>
            <div>{r.get('bmb')}</div>
        </div>"""

    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_PRO}</head>
    <body>
        <div class="container">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h2>Panel Control</h2>
                <div style="font-size:12px;">👤 {session['user_name']} | <a href="/logout">Salir</a></div>
            </div>
            <div style="display:flex; gap:10px; margin-bottom:20px;">
                <a href="/formulario" class="btn btn-primary">Nuevo Registro</a>
                <a href="/descargar" class="btn btn-outline">Excel</a>
            </div>
            {rows}
        </div>
        <div id="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; align-items:center; justify-content:center; padding:20px;">
            <div class="card" style="width:100%; max-width:500px;">
                <div id="det"></div>
                <button onclick="document.getElementById('modal').style.display='none'" class="btn btn-outline" style="margin-top:10px;">Cerrar</button>
            </div>
        </div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapObj = null;
            function verDetalle(id, pv, f, doc, mot, gps) {{
                document.getElementById('det').innerHTML = `<h3>${{pv}}</h3><p>Doc: ${{doc}}<br>Motivo: ${{mot}}</p>
                <button id="btn_img" class="btn btn-primary" onclick="loadImgs('${{id}}','${{gps}}')">Ver Imágenes y Mapa</button>
                <div id="map"></div><img id="i1" class="img-tech"><img id="i2" class="img-tech">`;
                document.getElementById('modal').style.display='flex';
            }}
            async function loadImgs(id, gps) {{
                document.getElementById('btn_img').innerText = "Cargando...";
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                if(d.f1) {{ document.getElementById('i1').src=d.f1; document.getElementById('i1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('i2').src=d.f2; document.getElementById('i2').style.display='block'; }}
                if(gps) {{
                    document.getElementById('map').style.display='block';
                    const l = gps.split(',').map(Number);
                    if(mapObj) mapObj.remove();
                    mapObj = L.map('map').setView(l, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapObj);
                    L.marker(l).addTo(mapObj);
                }}
                document.getElementById('btn_img').style.display='none';
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
        coleccion.insert_one({
            "pv": request.form.get('pv'), "n_documento": session['user_name'],
            "fecha": f, "mes": f[:7], "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/')

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_PRO}</head>
    <body onload="getGPS()">
        <div class="container" style="max-width:500px;">
            <div class="card">
                <h3>Nuevo Registro</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="pv" placeholder="Punto de Venta" required>
                    <input type="text" value="{session['user_name']}" readonly>
                    <input type="date" name="fecha" value="{today}" required>
                    <input type="text" name="bmb" placeholder="BMB">
                    <select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                    <input type="hidden" name="ubicacion" id="gps_val">
                    <div id="gps_status" style="font-size:12px; color:orange;">📍 Obteniendo GPS automáticamente...</div>
                    <input type="file" name="f1" accept="image/*" capture="camera">
                    <input type="file" name="f2" accept="image/*" capture="camera">
                    <button type="submit" class="btn btn-primary" style="margin-top:20px;">Guardar</button>
                </form>
            </div>
        </div>
        <script>
            function getGPS() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('gps_val').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps_status').innerText = "✅ GPS Vinculado automáticamente";
                    document.getElementById('gps_status').style.color = "green";
                }}, () => {{
                    document.getElementById('gps_status').innerText = "❌ Error GPS. Activa permisos.";
                    document.getElementById('gps_status').style.color = "red";
                }});
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/get_img/<id>')
def get_img(id):
    d = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/descargar')
def descargar():
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    def gen():
        si = io.StringIO(); w = csv.writer(si)
        w.writerow(['Punto de Venta', 'Usuario', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicación'])
        yield si.getvalue(); si.seek(0); si.truncate(0)
        for r in cursor:
            w.writerow([r.get('pv',''), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), r.get('bmb',''), r.get('motivo',''), r.get('ubicacion','')])
            yield si.getvalue(); si.seek(0); si.truncate(0)
    return Response(gen(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte.csv"})

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
