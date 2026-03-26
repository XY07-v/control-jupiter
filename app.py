from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_executive_v19_stable"

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

CSS_GERENCIAL = """
<style>
    :root { --nestle-blue: #004a99; --ios-blue: #007AFF; --bg: #F5F7F9; --accent: #34C759; }
    body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg); margin: 0; color: #333; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e0e0e0; position: sticky; top: 0; z-index: 100; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 20px; }
    .card-mini { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #efefef; transition: 0.3s; position: relative; }
    .card-mini:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }
    .btn-g { padding: 10px 18px; border-radius: 8px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: 0.2s; white-space: nowrap; text-decoration: none; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .btn-danger { background: #FF3B30; color: white; }
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .badge-warn { background: #FFF9E6; color: #FF9500; }
    .badge-success { background: #E8F5E9; color: #2E7D32; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 95%; max-width: 600px; border-radius: 16px; padding: 25px; max-height: 85vh; overflow-y: auto; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
    .search-box { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--nestle-blue); margin-bottom: 15px; font-size: 14px; }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; cursor: zoom-in; }
    @media (max-width: 600px) { .grid-cards { grid-template-columns: 1fr; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body>
        <header>
            <div style="font-weight: 800; font-size: 20px; color: var(--nestle-blue);">Nestlé BI <span style="font-weight: 300;">Dash</span></div>
            <div style="font-size: 13px;">{session.get('user_name')} <a href="/logout" style="margin-left:10px; color:red; text-decoration:none;">Salir</a></div>
        </header>
        <div class="container">
            <div class="action-bar">
                <button class="btn-g btn-primary" onclick="cargar('validaciones')">⚠️ Validaciones</button>
                <button class="btn-g btn-outline" onclick="cargar('visitas')">📋 Historial</button>
                <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Puntos</button>
                <button class="btn-g btn-outline" onclick="cargar('usuarios')">👥 Usuarios</button>
                <button class="btn-g btn-outline" onclick="openModal('m_csv')">📥 Importar</button>
                <a href="/descargar" class="btn-g btn-outline">📤 Exportar</a>
            </div>
            <input type="text" id="main_search" class="search-box" placeholder="Filtrar resultados en pantalla..." onkeyup="filtrarGrilla()">
            <div id="grid_data" class="grid-cards"></div>
        </div>
        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Carga Masiva de Puntos</h3>
            <input type="file" id="f_csv" accept=".csv">
            <button class="btn-g btn-primary" style="width:100%" onclick="subirCSV()">Procesar Archivo</button>
            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>
        </div></div>
        <script>
            function openModal(id) {{ document.getElementById(id).style.display='block'; }}
            function closeModal() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            function filtrarGrilla() {{
                const val = document.getElementById('main_search').value.toLowerCase();
                document.querySelectorAll('.card-mini').forEach(card => {{
                    card.style.display = card.innerText.toLowerCase().includes(val) ? 'block' : 'none';
                }});
            }}

            async function cargar(tipo) {{
                const grid = document.getElementById('grid_data');
                grid.innerHTML = 'Cargando datos maestros...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                let html = '';
                data.forEach(d => {{
                    if(tipo === 'validaciones') {{
                        html += `<div class="card-mini" style="border-left: 5px solid #FF9500;"><span class="badge badge-warn">Pendiente</span><div style="margin: 10px 0;"><b>${{d.pv}}</b><br><small>${{d.n_documento}} | ${{d.fecha}}</small></div><button class="btn-g btn-primary" style="width:100%; padding:6px;" onclick="verDetalleValidar('${{d._id}}')">Revisar</button></div>`;
                    }} else if(tipo === 'visitas') {{
                        html += `<div class="card-mini"><span class="badge badge-success">Aprobado</span><div style="margin: 10px 0;"><b>${{d.pv}}</b><br><small>${{d.fecha}}</small></div><button class="btn-g btn-outline" style="width:100%; padding:6px;" onclick="verDetalleValidar('${{d._id}}', false)">Detalles</button></div>`;
                    }} else if(tipo === 'puntos') {{
                        html += `<div class="card-mini"><b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || 'N/A'}}</small><button class="btn-g btn-outline" style="width:100%; margin-top:10px; padding:6px;" onclick="formEdit('puntos', '${{d._id}}')">Editar</button></div>`;
                    }} else if(tipo === 'usuarios') {{
                        html += `<div class="card-mini"><b>${{d.nombre_completo}}</b><br><small>Rol: ${{d.rol}}</small><button class="btn-g btn-outline" style="width:100%; margin-top:10px; padding:6px;" onclick="formEdit('usuarios', '${{d._id}}')">Editar</button></div>`;
                    }}
                }});
                grid.innerHTML = html || '<p>No hay registros.</p>';
            }}

            async function verDetalleValidar(id, conBotones=true) {{
                openModal('m_global');
                const b = document.getElementById('m_body');
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                let html = `<h3>Detalle</h3><p><b>Punto:</b> ${{d.pv}}</p><p><b>BMB Propuesto:</b> ${{d.bmb_propuesto}}</p><img src="${{d.f_bmb}}" class="img-preview"><img src="${{d.f_fachada}}" class="img-preview">`;
                if(conBotones) {{ html += `<div style="display:flex; gap:10px; margin-top:20px;"><button class="btn-g btn-primary" style="flex:1" onclick="finalizarValidacion('${{id}}','aprobar')">APROBAR</button><button class="btn-g btn-danger" style="flex:1" onclick="finalizarValidacion('${{id}}','rechazar')">RECHAZAR</button></div>`; }}
                html += `<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>`;
                b.innerHTML = html;
            }}

            async function formEdit(tipo, id) {{
                openModal('m_global');
                const b = document.getElementById('m_body');
                const r = await fetch(`/api/detalle/${{tipo}}/${{id}}`);
                const d = await r.json();
                let fields = `<h3>Editar</h3><form id="editForm">`;
                for (let k in d) {{ if(k !== '_id') fields += `<label>${{k}}</label><input type="text" name="${{k}}" value="${{d[k]}}">`; }}
                fields += `</form><button class="btn-g btn-primary" style="width:100%" onclick="guardarEdicion('${{tipo}}','${{id}}')">Guardar</button><button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cancelar</button>`;
                b.innerHTML = fields;
            }}

            async function guardarEdicion(tipo, id) {{
                const fd = new FormData(document.getElementById('editForm'));
                await fetch('/api/update/' + tipo + '/' + id, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(Object.fromEntries(fd.entries())) }});
                closeModal(); cargar(tipo);
            }}

            async function finalizarValidacion(id, op) {{
                await fetch(`/api/v_final/${{id}}/${{op}}`);
                closeModal(); cargar('validaciones');
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                closeModal(); cargar('puntos');
            }}
            window.onload = () => cargar('validaciones');
        </script>
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
        estado = "Pendiente" if (bmb_in != bmb_base or dist > 100) else "Aprobado"
        visitas_col.insert_one({{ "pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in, "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'), "motivo": request.form.get('motivo'), "ubicacion": gps, "distancia_m": round(dist, 1), "estado": estado, "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2')) }})
        if estado == "Aprobado": puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        gc.collect(); return redirect('/formulario?msg=OK')

    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1, "_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in pts])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px;">
            <div class="card-mini" style="padding:25px;">
                <h2 style="color:var(--nestle-blue); text-align:center;">Nuevo Reporte</h2>
                <form method="POST" enctype="multipart/form-data">
                    <label>Punto de Venta</label>
                    <input list="pts" name="pv" id="pv_i" oninput="vincular(this.value)" required placeholder="Escriba para buscar...">
                    <datalist id="pts">{opts}</datalist>
                    <label>BMB Detectado</label><input type="text" name="bmb" id="bmb_i" required>
                    <label>Motivo</label><select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                    <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <label>Fotos</label><input type="file" name="f1" accept="image/*" capture="camera" required><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="gps" id="gps"><button class="btn-g btn-primary" style="width:100%; margin-top:15px;">Enviar</button>
                    <a href="/" class="btn-g btn-outline" style="margin-top:10px;">Volver</a>
                </form>
            </div>
        </div>
        <script>
            const pts = {json.dumps(pts)};
            function vincular(val) {{ const p = pts.find(x => x['Punto de Venta'] === val); if(p) document.getElementById('bmb_i').value = p.BMB || ''; }}
        </script>
    </body></html>
    """)

@app.route('/api/get/<tipo>')
def api_get(tipo):
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    col = db['visitas' if (tipo=='visitas' or tipo=='validaciones') else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    d = col.find_one({"_id": ObjectId(id)}); d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/<tipo>/<id>', methods=['POST'])
def api_up(tipo, id):
    db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios'].update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s":"ok"})

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(content), delimiter=';' if ';' in content else ',')
        lista = [r for r in reader]
        if lista: puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/descargar')
def descargar():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'BMB Base', 'BMB Propuesto', 'Fecha', 'Asesor', 'Motivo', 'Distancia'])
    for r in cursor: w.writerow([r.get('pv'), r.get('bmb_actual'), r.get('bmb_propuesto'), r.get('fecha'), r.get('n_documento'), r.get('motivo'), r.get('distancia_m')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_GERENCIAL}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card-mini' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
