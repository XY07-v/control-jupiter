from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v18_final"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

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
    .btn-red { background: #FF3B30; color: white; }
    .nav-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 500px; border-radius: 20px; padding: 20px; max-height: 85vh; overflow-y: auto; }
    input, select { width: 100%; padding: 12px; margin: 5px 0 15px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
    img { width: 100%; border-radius: 10px; margin-top: 10px; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body>
        <h3>Panel Administrativo</h3>
        <div class="nav-grid">
            <button class="btn btn-blue" onclick="cargar('visitas')">Visitas</button>
            <button class="btn btn-blue" onclick="cargar('puntos')">Puntos</button>
            <button class="btn btn-light" onclick="cargar('usuarios')">Usuarios</button>
            <button class="btn btn-light" onclick="document.getElementById('m_csv').style.display='block'">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar CSV</a>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
        </div>
        <div id="main_cont"></div>
        
        <div id="m_csv" class="modal"><div class="modal-content" style="padding:20px;">
            <h3>Carga Masiva (.csv)</h3>
            <input type="file" id="f_csv" accept=".csv">
            <button class="btn btn-blue" onclick="subirCSV()">Procesar</button>
            <button class="btn btn-light" onclick="document.getElementById('m_csv').style.display='none'">Cerrar</button>
        </div></div>

        <div id="m_det" class="modal"><div class="modal-content" id="det_body" style="padding:20px;"></div></div>

        <script>
            async function cargar(tipo) {{
                const cont = document.getElementById('main_cont');
                cont.innerHTML = 'Consultando...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                let h = '<h4>Registros: ' + tipo + '</h4>';
                data.forEach(d => {{
                    h += `<div class="card">
                        <b>${{d.pv || d.nombre_completo || d['Punto de Venta']}}</b><br>
                        <small>${{d.fecha || d.rol || d.BMB || ''}}</small>
                        <button class="btn btn-light" style="margin-top:8px;" onclick="verDetalle('${{tipo}}','${{d._id}}')">Ver Todo</button>
                    </div>`;
                }});
                cont.innerHTML = h;
            }}

            async function verDetalle(tipo, id) {{
                const b = document.getElementById('det_body');
                document.getElementById('m_det').style.display='block';
                b.innerHTML = 'Cargando...';
                const r = await fetch(`/api/detalle/${{tipo}}/${{id}}`);
                const d = await r.json();
                let html = '<button class="btn btn-light" onclick="document.getElementById(\\'m_det\\').style.display=\\'none\\'">Cerrar</button>';
                for (let k in d) {{ if(!k.includes('f_')) html += `<p style="font-size:12px;"><b>${{k}}:</b> ${{d[k]}}</p>`; }}
                if(d.f_bmb) html += `<img src="${{d.f_bmb}}"><img src="${{d.f_fachada}}">`;
                b.innerHTML = html;
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); location.reload();
            }}
        </script>
        <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f: return ""
            b = base64.b64encode(f.read()).decode(); f.close()
            return f"data:image/jpeg;base64,{b}"
        
        pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('gps')
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        bmb_base = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        
        # Validación Automática
        estado = "Pendiente" if (bmb_in != bmb_base or dist > 100) else "Aprobado"
        
        visitas_col.insert_one({
            "pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in,
            "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'),
            "motivo": request.form.get('motivo'), "ubicacion": gps,
            "distancia_m": round(dist, 1), "estado": estado,
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        if estado == "Aprobado":
            puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        
        gc.collect()
        return redirect('/formulario?msg=OK')

    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1, "_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in pts])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="card">
            <h2 style="text-align:center; color:var(--blue);">Nestlé BI</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input list="pts" name="pv" id="pv_i" oninput="vincular(this.value)" required>
                <datalist id="pts">{opts}</datalist>
                
                <label>BMB Detectado</label>
                <input type="text" name="bmb" id="bmb_i" required>
                
                <label>Fecha</label>
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                
                <label>Motivo de Visita</label>
                <select name="motivo">
                    <option>Visita Exitosa</option>
                    <option>Punto Cerrado</option>
                    <option>Máquina no encontrada</option>
                </select>

                <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                
                <input type="hidden" name="gps" id="gps">
                <button class="btn btn-blue">Enviar Reporte</button>
                <a href="/" class="btn btn-light">Volver al Panel</a>
            </form>
        </div>
        <script>
            const pts = {json.dumps(pts)};
            function vincular(val) {{
                const p = pts.find(x => x['Punto de Venta'] === val);
                if(p) document.getElementById('bmb_i').value = p.BMB || '';
            }}
        </script>
    </body></html>
    """)

@app.route('/descargar')
def descargar():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'BMB Base', 'BMB Propuesto', 'Fecha', 'Asesor', 'Motivo', 'Distancia'])
    for r in cursor: w.writerow([r.get('pv'), r.get('bmb_actual'), r.get('bmb_propuesto'), r.get('fecha'), r.get('n_documento'), r.get('motivo'), r.get('distancia_m')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga_csv():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        sep = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=sep)
        lista = [r for r in reader]
        if lista:
            puntos_col.delete_many({})
            puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/api/get/<tipo>')
def api_get(tipo):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    res = list(col.find({}, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    d = col.find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
