from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_executive_v21"

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
    :root { --nestle-blue: #004a99; --bg: #F5F7F9; }
    body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg); margin: 0; color: #333; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e0e0e0; position: sticky; top: 0; z-index: 100; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 20px; }
    .card-mini { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #efefef; }
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; align-items: center; }
    .search-box { flex-grow: 1; min-width: 200px; margin-top: 15px; }
    .search-box input { width: 100%; padding: 12px 18px; border-radius: 25px; border: 1px solid #ddd; outline: none; font-size: 14px; }
    .btn-g { padding: 10px 18px; border-radius: 8px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; text-decoration: none; justify-content: center; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .badge-motivo { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; margin-top: 5px; background: #FFF3E0; color: #E65100; font-weight: bold; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 500px; border-radius: 16px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; border: 1px solid #eee; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    rol = session.get('role')
    
    botones = f"""
        <button class="btn-g btn-primary" onclick="cargar('validaciones')">⚠️ Validaciones</button>
        <button class="btn-g btn-outline" onclick="cargar('visitas')">📋 Historial</button>
        <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Puntos</button>
        <button class="btn-g btn-outline" onclick="cargar('usuarios')">👥 Usuarios</button>
        <a href="/exportar_reportes" class="btn-g btn-outline">📤 Exportar</a>
    """ if rol == 'admin' else f"""
        <a href="/formulario" class="btn-g btn-primary">📝 Nuevo Reporte</a>
        <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Consultar Puntos</button>
    """

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body>
        <header>
            <div style="font-weight: 800; font-size: 18px; color: var(--nestle-blue);">Nestlé BI</div>
            <div style="font-size: 12px;">{session.get('user_name')} | <a href="/logout" style="color:red; text-decoration:none;">Salir</a></div>
        </header>
        <div class="container">
            <div class="action-bar">{botones}</div>
            <div class="search-box" id="search_container" style="display:none;">
                <input type="text" id="buscador" placeholder="🔍 Buscar..." onkeyup="filtrar()">
            </div>
            <div id="grid_data" class="grid-cards"></div>
        </div>
        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>

        <script>
            let datosActuales = []; let tipoActual = ''; let timerBusqueda;
            const miRol = "{rol}";

            function openModal() {{ document.getElementById('m_global').style.display='block'; }}
            function closeModal() {{ document.getElementById('m_global').style.display='none'; }}

            async function cargar(tipo) {{
                tipoActual = tipo;
                const grid = document.getElementById('grid_data');
                document.getElementById('search_container').style.display = ['visitas', 'puntos', 'usuarios'].includes(tipo) ? 'block' : 'none';
                grid.innerHTML = '<p>Cargando...</p>';
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
                        let alerta = d.motivo_alerta ? `<span class="badge-motivo">🚨 ${{d.motivo_alerta}}</span>` : '';
                        html += `<div class="card-mini" style="border-left: 5px solid ${{color}};">
                            <div style="padding:10px;"><b>${{d.pv}}</b><br><small>${{d.fecha}}</small><br>${{alerta}}
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="verDetalle('${{d._id}}', ${{d.estado === 'Pendiente'}})">Detalle</button></div>
                        </div>`;
                    }} else if(tipoActual === 'puntos') {{
                        html += `<div class="card-mini" style="padding:15px;">
                            <b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || 'N/A'}}</small>
                        </div>`;
                    }} else if(tipoActual === 'usuarios') {{
                        html += `<div class="card-mini" style="padding:15px;">
                            <b>${{d.nombre_completo}}</b><br><small>Usuario: ${{d.usuario}} | Rol: ${{d.rol}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="editarUsuario('${{d._id}}')">Editar</button>
                        </div>`;
                    }}
                }});
                grid.innerHTML = html || '<p>No hay registros.</p>';
            }}

            function filtrar() {{
                const val = document.getElementById('buscador').value.toLowerCase();
                if(tipoActual === 'puntos') {{
                    clearTimeout(timerBusqueda);
                    timerBusqueda = setTimeout(async () => {{
                        const r = await fetch('/api/search/puntos?q=' + val);
                        renderizar(await r.json());
                    }}, 300);
                }} else {{
                    const filtrados = datosActuales.filter(d => 
                        (d.pv || d.nombre_completo || d.usuario || '').toLowerCase().includes(val)
                    );
                    renderizar(filtrados);
                }}
            }}

            async function editarUsuario(id) {{
                openModal();
                const r = await fetch('/api/detalle/usuarios/' + id);
                const d = await r.json();
                document.getElementById('m_body').innerHTML = `
                    <h3>Editar Usuario</h3>
                    <form id="formUser">
                        <label>Nombre Completo</label><input type="text" name="nombre_completo" value="${{d.nombre_completo}}">
                        <label>Usuario</label><input type="text" name="usuario" value="${{d.usuario}}">
                        <label>Contraseña</label><input type="text" name="password" value="${{d.password}}">
                        <label>Rol</label>
                        <select name="rol">
                            <option value="admin" ${{d.rol=='admin'?'selected':''}}>Admin</option>
                            <option value="asesor" ${{d.rol=='asesor'?'selected':''}}>Asesor</option>
                        </select>
                    </form>
                    <button class="btn-g btn-primary" style="width:100%; margin-top:10px;" onclick="guardarUsuario('${{id}}')">Guardar</button>
                    <button class="btn-g btn-outline" style="width:100%; margin-top:5px;" onclick="closeModal()">Cancelar</button>`;
            }}

            async function guardarUsuario(id) {{
                const fd = new FormData(document.getElementById('formUser'));
                const data = Object.fromEntries(fd.entries());
                await fetch('/api/update/usuarios/' + id, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                closeModal(); cargar('usuarios');
            }}

            async function verDetalle(id, botones) {{
                openModal();
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                let btns = botones ? `<div style="display:flex; gap:10px; margin-top:15px;">
                    <button class="btn-g btn-primary" style="flex:1" onclick="validar('${{id}}','aprobar')">Aprobar</button>
                    <button class="btn-g btn-outline" style="flex:1; color:red; border-color:red;" onclick="validar('${{id}}','rechazar')">Rechazar</button>
                </div>` : '';
                document.getElementById('m_body').innerHTML = `
                    <h3>${{d.pv}}</h3><p>BMB: ${{d.bmb_propuesto}}<br>Alerta: ${{d.motivo_alerta || 'Ninguna'}}</p>
                    <img src="${{d.f_bmb}}" class="img-preview"><img src="${{d.f_fachada}}" class="img-preview">
                    ${{btns}} <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>`;
            }}

            async function validar(id, op) {{
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
        visitas_col.insert_one({"pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in, "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'), "ubicacion": gps, "estado": estado, "motivo_alerta": motivo_alerta, "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))})
        if estado == "Aprobado": puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        return redirect('/')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_GERENCIAL}</head><body onload='navigator.geolocation.getCurrentPosition(p=>document.getElementById(\"gps\").value=p.coords.latitude+\",\"+p.coords.longitude)'><div class='container' style='max-width:400px;'><div class='card-mini' style='padding:20px;'><h2 style='margin-top:0;'>Nuevo Reporte</h2><form method='POST' enctype='multipart/form-data'><label>Punto de Venta</label><input list='pts' name='pv' id='pv_i' oninput='buscarPV(this.value)' required autocomplete='off'><datalist id='pts'></datalist><label>BMB Detectado</label><input type='text' name='bmb' id='bmb_i' required><label>Fecha</label><input type='date' name='fecha' value='{datetime.now().strftime('%Y-%m-%d')}'><label>Fotos</label><input type='file' name='f1' accept='image/*' capture='camera'><input type='file' name='f2' accept='image/*' capture='camera'><input type='hidden' name='gps' id='gps'><button class='btn-g btn-primary' style='width:100%; margin-top:15px;'>Enviar Reporte</button><a href='/' class='btn-g btn-outline' style='margin-top:10px;'>Cancelar</a></form></div></div><script>async function buscarPV(val) {{ if(val.length < 3) return; const r = await fetch('/api/search/puntos?q=' + val); const data = await r.json(); document.getElementById('pts').innerHTML = data.map(p => `<option value=\"${{p['Punto de Venta']}}\">`).join(''); const found = data.find(x => x['Punto de Venta'] === val); if(found) document.getElementById('bmb_i').value = found.BMB || ''; }}</script></body></html>")

@app.route('/api/get/<tipo>')
def api_get(tipo):
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    col = db['visitas' if tipo in ['visitas','validaciones'] else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'usuarios' if tipo=='usuarios' else 'puntos_venta']
    d = col.find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/usuarios/<id>', methods=['POST'])
def api_up_user(id):
    usuarios_col.update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s":"ok"})

@app.route('/api/search/puntos')
def api_search_puntos():
    q = request.args.get('q', '').strip()
    query = {"$or": [{"Punto de Venta": {"$regex": q, "$options": "i"}}, {"BMB": {"$regex": q, "$options": "i"}}]} if q else {}
    res = list(puntos_col.find(query, {"f_bmb":0, "f_fachada":0}).limit(20))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else: visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/exportar_reportes')
def exportar_reportes():
    if 'user_id' not in session or session.get('role') != 'admin': return "Denegado", 403
    si = io.StringIO(); cw = csv.writer(si, delimiter=';')
    reportes = list(visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0}))
    if reportes:
        cw.writerow(reportes[0].keys())
        for r in reportes: cw.writerow(r.values())
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=nestle_historial.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string("<html><head>"+CSS_GERENCIAL+"</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card-mini' style='width:300px; padding:20px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
