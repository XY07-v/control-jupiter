from flask import Flask, render_template_string, request, redirect, jsonify, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, gc, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_v17_full_data"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']

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

CSS = """
<style>
    :root { --blue: #007AFF; --bg: #F2F2F7; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; color: #1c1c1e; }
    .card { background: white; border-radius: 15px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .btn { width: 100%; padding: 12px; border-radius: 10px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 8px; font-size: 14px; display: block; text-align: center; text-decoration: none; box-sizing: border-box; }
    .btn-blue { background: var(--blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .nav-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); z-index: 1000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 500px; border-radius: 20px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; }
    img { width: 100%; border-radius: 10px; margin-top: 10px; border: 1px solid #ddd; }
    .det-item { margin-bottom: 10px; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body>
        <h3>Nestlé BI - Dashboard</h3>
        <div class="nav-grid">
            <button class="btn btn-blue" onclick="cargar('visitas')">Visitas</button>
            <button class="btn btn-blue" onclick="cargar('puntos')">Puntos</button>
            <button class="btn btn-light" onclick="cargar('usuarios')">Usuarios</button>
            <a href="/formulario" class="btn btn-light">Nuevo Reporte</a>
        </div>
        <div id="main_cont"></div>
        <div id="modal_full" class="modal"><div class="modal-content" id="modal_body"></div></div>
        <script>
            async function cargar(tipo) {{
                const cont = document.getElementById('main_cont');
                cont.innerHTML = 'Cargando...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                let html = '<h4>Lista de ' + tipo + '</h4>';
                data.forEach(d => {{
                    html += `<div class="card">
                        <b>${{d.pv || d.nombre_completo || d['Punto de Venta']}}</b><br>
                        <small>${{d.fecha || d.rol || d.BMB || ''}}</small>
                        <button class="btn btn-light" style="margin-top:8px; font-size:11px;" onclick="verMas('${{tipo}}','${{d._id}}')">Ver Todo / Editar</button>
                    </div>`;
                }});
                cont.innerHTML = html;
            }}
            async function verMas(tipo, id) {{
                const m = document.getElementById('modal_full');
                const b = document.getElementById('modal_body');
                m.style.display = 'block'; b.innerHTML = 'Consultando...';
                const r = await fetch(`/api/detalle/${{tipo}}/${{id}}`);
                const d = await r.json();
                let info = `<button class="btn btn-light" onclick="document.getElementById('modal_full').style.display='none'">Cerrar</button>`;
                for (let k in d) {{
                    if(!k.includes('f_')) info += `<div class="det-item"><b>${{k}}:</b> ${{d[k]}}</div>`;
                }}
                if(d.f_bmb) info += `<img src="${{d.f_bmb}}"><img src="${{d.f_fachada}}">`;
                b.innerHTML = info;
            }}
        </script>
        <a href="/logout" class="btn btn-light" style="color:red;">Cerrar Sesión</a>
    </body></html>
    """)

# --- APIs DE DATOS ---

@app.route('/api/get/<tipo>')
def api_get(tipo):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    # Traemos solo texto para el listado inicial
    res = list(col.find({}, {"f_bmb":0, "f_fachada":0}).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    doc = col.find_one({"_id": ObjectId(id)})
    if doc: doc['_id'] = str(doc['_id'])
    gc.collect()
    return jsonify(doc)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f: return ""
            b = base64.b64encode(f.read()).decode(); f.close()
            return f"data:image/jpeg;base64,{b}"
        
        pv_in = request.form.get('pv')
        gps_in = request.form.get('gps')
        pnt = db['puntos_venta'].find_one({"Punto de Venta": pv_in})
        dist = calcular_distancia(gps_in, pnt.get('Ruta')) if pnt else 0
        
        reporte = {
            "pv": pv_in,
            "bmb_actual": pnt.get('BMB') if pnt else "NUEVO",
            "bmb_propuesto": request.form.get('bmb'),
            "fecha": request.form.get('fecha'),
            "n_documento": session.get('user_name'),
            "ubicacion": gps_in,
            "distancia_m": round(dist, 1),
            "estado": "Pendiente",
            "f_bmb": to_b64(request.files.get('f1')),
            "f_fachada": to_b64(request.files.get('f2'))
        }
        db['visitas'].insert_one(reporte)
        gc.collect()
        return redirect('/?msg=OK')

    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in db['puntos_venta'].find({}, {"Punto de Venta":1}).limit(300)])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="card">
            <h3>Nuevo Reporte</h3>
            <form method="POST" enctype="multipart/form-data">
                <input list="pts" name="pv" placeholder="Seleccionar Punto" class="btn" style="text-align:left; border:1px solid #ccc; color:black;">
                <datalist id="pts">{opts}</datalist>
                <input type="text" name="bmb" placeholder="Nuevo BMB (Propuesto)" class="btn" style="text-align:left; border:1px solid #ccc; color:black;">
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}" class="btn" style="border:1px solid #ccc;">
                <label style="font-size:12px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera">
                <label style="font-size:12px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera">
                <input type="hidden" name="gps" id="gps">
                <button class="btn btn-blue" style="margin-top:15px;">Enviar Datos</button>
                <a href="/" class="btn btn-light">Regresar</a>
            </form>
        </div>
    </body></html>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = db['usuarios'].find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo']}); return redirect('/')
    return render_template_string(f"<html><head>{CSS}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario' class='btn' style='border:1px solid #ccc; color:black;'><input type='password' name='p' placeholder='Clave' class='btn' style='border:1px solid #ccc; color:black;'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
