from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v16_ultra_stable"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']

# Colecciones
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS ESTILO IOS ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; color: #1c1c1e; }
    .container { padding: 20px; max-width: 600px; margin: auto; }
    .card { background: white; border-radius: 15px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .btn { width: 100%; padding: 12px; border-radius: 10px; border: none; font-weight: 600; cursor: pointer; margin-top: 10px; font-size: 14px; text-decoration: none; display: block; text-align: center; box-sizing: border-box; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(5px); z-index: 2000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 400px; border-radius: 20px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    img { width: 100%; border-radius: 10px; margin-top: 10px; }
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: bold; float: right; }
    .badge-pend { background: #FF9500; color: white; }
    .badge-aprob { background: #34C759; color: white; }
</style>
"""

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    
    # CONSULTA SEGURA: Traemos datos de 'visitas' SIN las imágenes (f_bmb y f_fachada)
    # Esto evita que Render se quede sin RAM al iniciar.
    visitas = list(visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1).limit(50))
    
    html_visitas = ""
    for v in visitas:
        estado_clase = "badge-pend" if v.get('estado') == "Pendiente" else "badge-aprob"
        html_visitas += f'''
        <div class="card">
            <span class="badge {estado_clase}">{v.get('estado', 'OK')}</span>
            <b>{v.get('pv')}</b><br>
            <small>{v.get('fecha')} | {v.get('n_documento')}</small><br>
            <button class="btn btn-light" onclick="verSoportes('{v['_id']}')">Consultar Soportes</button>
            {f'<button class="btn btn-blue" onclick="aprobar(\'{v["_id"]}\')">Aprobar</button>' if v.get('estado') == "Pendiente" and session.get('role') == 'admin' else ''}
        </div>'''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body>
        <div class="container">
            <h2 style="color:var(--ios-blue);">Panel Nestlé BI</h2>
            <p>Usuario: <b>{session.get('user_name')}</b></p>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <hr>
            <h3>Historial Reciente</h3>
            {html_visitas or '<p>No hay registros.</p>'}
            <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
        </div>
        
        <div id="modal_img" class="modal">
            <div class="modal-content" id="cont_img"></div>
        </div>

        <script>
            async function verSoportes(id) {{
                const m = document.getElementById('modal_img');
                const cont = document.getElementById('cont_img');
                m.style.display = 'block';
                cont.innerHTML = 'Cargando imágenes de forma segura...';
                
                const r = await fetch('/api/get_img/' + id);
                const d = await r.json();
                
                cont.innerHTML = `
                    <button class="btn btn-light" onclick="document.getElementById('modal_img').style.display='none'">Cerrar</button>
                    <img src="${{d.f1}}" alt="BMB">
                    <img src="${{d.f2}}" alt="Fachada">
                    <p style="font-size:12px; color:gray; text-align:center;">GPS: ${{d.gps}}</p>
                `;
            }}

            async function aprobar(id) {{
                if(confirm('¿Aprobar este registro?')) {{
                    await fetch('/api/aprobar/' + id);
                    location.reload();
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/api/get_img/<id>')
def api_get_img(id):
    # Solo aquí se cargan las imágenes de UN SOLO registro a la vez
    d = visitas_col.find_one({"_id": ObjectId(id)})
    if not d: return jsonify({})
    return jsonify({
        "f1": d.get('f_bmb'),
        "f2": d.get('f_fachada'),
        "gps": d.get('ubicacion', 'Sin GPS')
    })

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        # Procesamiento de imágenes con liberación de RAM inmediata
        def to_b64(f):
            if not f: return ""
            data = base64.b64encode(f.read()).decode()
            f.close()
            return f"data:image/jpeg;base64,{data}"

        nuevo_reporte = {
            "pv": request.form.get('pv'),
            "n_documento": session.get('user_name'),
            "fecha": request.form.get('fecha'),
            "bmb_propuesto": request.form.get('bmb'),
            "ubicacion": request.form.get('gps'),
            "estado": "Pendiente",
            "f_bmb": to_b64(request.files.get('f1')),
            "f_fachada": to_b64(request.files.get('f2'))
        }
        visitas_col.insert_one(nuevo_reporte)
        gc.collect() # FORZAR LIMPIEZA DE MEMORIA
        return redirect('/?msg=Enviado')

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container">
            <div class="card">
                <h3>Nuevo Reporte</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="pv" placeholder="Nombre del Punto" style="width:100%; padding:10px; margin-bottom:10px;" required>
                    <input type="text" name="bmb" placeholder="BMB Máquina" style="width:100%; padding:10px; margin-bottom:10px;" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}" style="width:100%; padding:10px; margin-bottom:10px;">
                    <label>Foto BMB:</label><input type="file" name="f1" accept="image/*" capture="camera">
                    <label>Foto Fachada:</label><input type="file" name="f2" accept="image/*" capture="camera">
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                    <a href="/" class="btn btn-light">Volver</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u:
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body style="display:flex; align-items:center; justify-content:center; height:100vh;">
        <div class="card" style="width:300px;">
            <h2 style="text-align:center;">Nestlé BI</h2>
            <form method="POST">
                <input type="text" name="u" placeholder="Usuario" style="width:100%; padding:10px; margin-bottom:10px;">
                <input type="password" name="p" placeholder="Contraseña" style="width:100%; padding:10px; margin-bottom:10px;">
                <button class="btn btn-blue">Entrar</button>
            </form>
        </div>
    </body></html>
    """)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
