from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_executive_v19"

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
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; align-items: center; }
    .search-box { flex-grow: 1; min-width: 200px; margin-top: 15px; }
    .search-box input { width: 100%; padding: 12px 18px; border-radius: 25px; border: 1px solid #ddd; font-size: 14px; outline: none; }
    .btn-g { padding: 10px 18px; border-radius: 8px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: 0.2s; white-space: nowrap; text-decoration: none; justify-content: center; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .btn-danger { background: #FF3B30; color: white; }
    .badge-motivo { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; margin-top: 5px; background: #FFF3E0; color: #E65100; font-weight: bold; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 95%; max-width: 600px; border-radius: 16px; padding: 25px; max-height: 85vh; overflow-y: auto; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; }
    @media (max-width: 600px) { .action-bar { flex-direction: column; align-items: stretch; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    rol = session.get('role')
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body>
        <header>
            <div style="font-weight: 800; font-size: 20px; color: var(--nestle-blue);">Nestlé BI <span style="font-weight: 300;">Dash</span></div>
            <div style="font-size: 13px;">{session.get('user_name')} <a href="/logout" style="margin-left:10px; color:red; text-decoration:none;">Salir</a></div>
        </header>
        
        <div class="container">
            <div class="action-bar" id="nav_btns">
                {'''<button class="btn-g btn-primary" onclick="cargar('validaciones')">⚠️ Validaciones</button>
                    <button class="btn-g btn-outline" onclick="cargar('visitas')">📋 Historial</button>
                    <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Puntos</button>
                    <button class="btn-g btn-outline" onclick="cargar('usuarios')">👥 Usuarios</button>
                    <a href="/exportar_reportes" class="btn-g btn-outline">📤 Exportar</a>''' if rol == 'admin' else 
                   '''<a href="/formulario" class="btn-g btn-primary">📝 Nuevo Reporte</a>
                    <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Consultar Puntos</button>
                    <a href="/exportar_reportes" class="btn-g btn-outline">📤 Exportar</a>'''}
            </div>

            <div class="search-box" id="search_container" style="display:none;">
                <input type="text" id="buscador" placeholder="🔍 Buscar por Nombre o BMB..." onkeyup="filtrar()">
            </div>

            <div id="grid_data" class="grid-cards"></div>
        </div>

        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>

        <script>
            let datosActuales = [];
            let tipoActual = '';
            let timerBusqueda;
            const miRol = "{rol}";

            function openModal(id) {{ document.getElementById(id).style.display='block'; }}
            function closeModal() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargar(tipo) {{
                tipoActual = tipo;
                const grid = document.getElementById('grid_data');
                const sBox = document.getElementById('search_container');
                grid.innerHTML = 'Cargando...';
                
                sBox.style.display = ['visitas', 'puntos', 'usuarios'].includes(tipo) ? 'block' : 'none';
                document.getElementById('buscador').value = '';

                const r = await fetch('/api/get/' + tipo);
                datosActuales = await r.json();
                renderizar(datosActuales);
            }}

            function renderizar(data) {{
                const grid = document.getElementById('grid_data');
                let html = '';
                data.forEach(d => {{
                    if(tipoActual === 'validaciones' || tipoActual === 'visitas') {{
                        let color = d.estado === 'Pendiente' ? '#FF9500' : '#2E7D32';
                        let motivoLabel = d.motivo_alerta ? `<span class="badge-motivo">🚨 ${{d.motivo_alerta}}</span>` : '';
                        html += `<div class="card-mini" style="border-left: 5px solid ${{color}};">
                            <div style="margin: 10px 0;"><b>${{d.pv}}</b><br><small>${{d.fecha}}</small><br>${{motivoLabel}}</div>
                            <button class="btn-g btn-outline" style="width:100%; padding:6px;" onclick="verDetalleValidar('${{d._id}}', ${{d.estado === 'Pendiente'}})">Ver Detalle</button>
                        </div>`;
                    }} else if(tipoActual === 'puntos') {{
                        html += `<div class="card-mini">
                            <div style="margin-bottom:10px;"><b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || 'N/A'}}</small></div>
                            ${{miRol === 'admin' ? `<button class="btn-g btn-outline" style="width:100%; padding:6px;" onclick="formEdit('puntos', '${{d._id}}')">Editar</button>` : ''}}
                        </div>`;
                    }} else if(tipoActual === 'usuarios') {{
                        html += `<div class="card-mini">
                            <div style="margin-bottom:10px;"><b>${{d.nombre_completo}}</b><br><small>Rol: ${{d.rol}}</small></div>
                            <button class="btn-g btn-outline" style="width:100%; padding:6px;" onclick="formEdit('usuarios', '${{d._id}}')">Editar</button>
                        </div>`;
                    }}
                }});
                grid.innerHTML = html || '<p style="grid-column:1/-1; text-align:center; color:gray;">Sin resultados.</p>';
            }}

            function filtrar() {{
                const val = document.getElementById('buscador').value.toLowerCase();
                if(tipoActual === 'puntos') {{
                    clearTimeout(timerBusqueda);
                    timerBusqueda = setTimeout(async () => {{
                        const r = await fetch(`/api/search/puntos?q=${{val}}`);
                        renderizar(await r.json());
                    }}, 400);
                    return;
                }}
                const filtrados = datosActuales.filter(d => {{
                    const n = (d.pv || d['Punto de Venta'] || d.nombre_completo || '').toLowerCase();
                    const b = (d.BMB || d.bmb_actual || '').toLowerCase();
                    return n.includes(val) || b.includes(val);
                }});
                renderizar(filtrados);
            }}

            async function verDetalleValidar(id, conBotones) {{
                openModal('m_global');
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                let html = `<h3>Detalle de Visita</h3><div style="font-size:13px; margin-bottom:15px;"><b>${{d.pv}}</b><br>BMB Propuesto: ${{d.bmb_propuesto}}<br>Alerta: ${{d.motivo_alerta || 'Ninguna'}}</div>
                    <img src="${{d.f_bmb}}" class="img-preview"><img src="${{d.f_fachada}}" class="img-preview">`;
                if(conBotones) {{
                    html += `<div style="display:flex; gap:10px; margin-top:20px;">
                        <button class="btn-g btn-primary" style="flex:1" onclick="finalizarValidacion('${{id}}','aprobar')">Aprobar</button>
                        <button class="btn-g btn-danger" style="flex:1" onclick="finalizarValidacion('${{id}}','rechazar')">Rechazar</button>
                    </div>`;
                }}
                html += `<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>`;
                document.getElementById('m_body').innerHTML = html;
            }}

            async function formEdit(tipo, id) {{
                openModal('m_global');
                const r = await fetch(`/api/detalle/${{tipo}}/${{id}}`);
                const d = await r.json();
                let fields = `<h3>Editar Registro</h3><form id="editForm">`;
                for (let k in d) {{ if(k !== '_id' && (typeof d[k] !== 'string' || d[k].length < 500)) fields += `<label style="font-size:11px;">${{k}}</label><input type="text" name="${{k}}" value="${{d[k]}}">`; }}
                fields += `</form><button class="btn-g btn-primary" style="width:100%" onclick="guardarEdicion('${{tipo}}','${{id}}')">Guardar Cambios</button>
                          <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cancelar</button>`;
                document.getElementById('m_body').innerHTML = fields;
            }}

            async function guardarEdicion(tipo, id) {{
                const fd = new FormData(document.getElementById('editForm'));
                await fetch('/api/update/' + tipo + '/' + id, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(Object.fromEntries(fd.entries()))
                }});
                closeModal(); cargar(tipo);
            }}

            async function finalizarValidacion(id, op) {{
                await fetch(`/api/v_final/${{id}}/${{op}}`);
                closeModal(); cargar('validaciones');
            }}
            
            window.onload = () => cargar(miRol === 'admin' ? 'validaciones' : 'puntos');
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
        
        # LÓGICA DE MOTIVO DE ALERTA
        motivo_alerta = ""
        if not pnt: 
            motivo_alerta = "Nuevo Punto"
            bmb_base = "NUEVO"
        else:
            bmb_base = pnt.get('BMB', "NUEVO")
            dist = calcular_distancia(gps, pnt.get('Ruta'))
            if bmb_in != bmb_base: motivo_alerta = "Cambio de BMB"
            if dist > 100: motivo_alerta = (" / " if motivo_alerta else "") + "Fuera de Rango"

        estado = "Pendiente" if motivo_alerta else "Aprobado"
        
        visitas_col.insert_one({
            "pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in,
            "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'),
            "motivo": request.form.get('motivo'), "ubicacion": gps, "estado": estado,
            "motivo_alerta": motivo_alerta,
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        if estado == "Aprobado": puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        return redirect('/formulario?msg=OK')

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px;">
            <div class="card-mini" style="padding:25px;">
                <h2 style="color:var(--nestle-blue); text-align:center; margin-top:0;">Nuevo Reporte</h2>
                <form method="POST" enctype="multipart/form-data">
                    <label>Punto de Venta</label><input list="pts" name="pv" id="pv_i" oninput="buscarPV(this.value)" required>
                    <datalist id="pts"></datalist>
                    <label>BMB Detectado</label><input type="text" name="bmb" id="bmb_i" required>
                    <label>Motivo</label><select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                    <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <label>Fotos</label>
                    <input type="file" name="f1" accept="image/*" capture="camera"><input type="file" name="f2" accept="image/*" capture="camera">
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn-g btn-primary" style="width:100%; margin-top:15px;">Enviar Reporte</button>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px;">
                        <a href="/" class="btn-g btn-outline">Regresar</a>
                        <a href="/logout" class="btn-g btn-danger">Cerrar Sesión</a>
                    </div>
                </form>
            </div>
        </div>
        <script>
            let tmo;
            async function buscarPV(val) {{
                if(val.length < 3) return;
                clearTimeout(tmo);
                tmo = setTimeout(async () => {{
                    const r = await fetch(`/api/search/puntos?q=${{val}}`);
                    const data = await r.json();
                    document.getElementById('pts').innerHTML = data.map(p => `<option value="${{p['Punto de Venta']}}">`).join('');
                    const found = data.find(x => x['Punto de Venta'] === val);
                    if(found) document.getElementById('bmb_i').value = found.BMB || '';
                }}, 300);
            }}
        </script>
    </body></html>
    """)

@app.route('/exportar_reportes')
def exportar_reportes():
    if 'user_id' not in session: return redirect('/login')
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';')
    # Traemos todos los registros de visitas con su estado y motivo de alerta
    reportes = list(visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0}))
    if reportes:
        cw.writerow(reportes[0].keys())
        for r in reportes: cw.writerow(r.values())
    
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": f"attachment; filename=historial_reportes_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.route('/api/get/<tipo>')
def api_get(tipo):
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    col = db['visitas' if tipo in ['visitas','validaciones'] else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/search/puntos')
def api_search_puntos():
    q = request.args.get('q', '').strip()
    query = {"$or": [{"Punto de Venta": {"$regex": q, "$options": "i"}}, {"BMB": {"$regex": q, "$options": "i"}}]} if q else {}
    res = list(puntos_col.find(query, {"f_bmb":0, "f_fachada":0}).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    d = col.find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/<tipo>/<id>', methods=['POST'])
def api_up(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    col.update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s":"ok"})

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else: visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

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
