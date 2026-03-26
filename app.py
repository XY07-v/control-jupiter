from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "nestle_bi_executive_v21"
app.permanent_session_lifetime = timedelta(days=1)

# --- CONEXIÓN OPTIMIZADA ---
# Usamos un pool_size para evitar que la app se bloquee esperando conexiones
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, maxPoolSize=50, waitQueueTimeoutMS=2500)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2 or pos1 == "0,0": return 0
    try:
        lat1, lon1 = map(float, str(pos1).split(','))
        lat2, lon2 = map(float, str(pos2).split(','))
        R = 6371000 
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)
    except: return 0

CSS_GERENCIAL = """
<style>
    :root { --nestle-blue: #004a99; --bg: #F5F7F9; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; border-bottom: 1px solid #ddd; position: sticky; top: 0; z-index: 100; }
    .container { padding: 15px; max-width: 1200px; margin: auto; }
    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
    .card-mini { background: white; border-radius: 12px; padding: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-left: 5px solid #ccc; }
    .action-bar { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; }
    .btn-g { padding: 10px 14px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; text-decoration: none; font-size: 12px; display: flex; align-items: center; justify-content: center; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    input, select { width: 100%; padding: 10px; margin: 5px 0 10px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .badge-alerta { background: #fee2e2; color: #b91c1c; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); z-index: 1000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 450px; border-radius: 15px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    .img-preview { width: 100%; border-radius: 8px; margin-top: 8px; border: 1px solid #eee; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    rol = session.get('role')
    
    btns = f"""
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
            <div style="font-weight: bold; color: var(--nestle-blue);">Nestlé BI</div>
            <div style="font-size: 12px;">{session.get('user_name')} | <a href="/logout" style="color:red; text-decoration:none;">Salir</a></div>
        </header>
        <div class="container">
            <div class="action-bar">{btns}</div>
            <div id="search_container" style="display:none; margin-bottom:15px;">
                <input type="text" id="buscador" placeholder="🔍 Buscar..." onkeyup="filtrar()" style="border-radius:20px; padding:10px 20px;">
            </div>
            <div id="grid_data" class="grid-cards"></div>
        </div>
        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>

        <script>
            let datosActuales = []; let tipoActual = '';
            async function cargar(tipo) {{
                tipoActual = tipo;
                document.getElementById('search_container').style.display = 'block';
                const grid = document.getElementById('grid_data');
                grid.innerHTML = '<p style="text-align:center">Cargando datos...</p>';
                const r = await fetch('/api/get/' + tipo);
                datosActuales = await r.json();
                renderizar(datosActuales);
            }}

            function renderizar(data) {{
                const grid = document.getElementById('grid_data');
                let html = '';
                data.forEach(d => {{
                    if(tipoActual === 'validaciones' || tipoActual === 'visitas') {{
                        let clr = d.estado === 'Pendiente' ? '#f59e0b' : '#10b981';
                        html += `<div class="card-mini" style="border-left-color: ${{clr}}">
                            <b>${{d.pv}}</b><br><small>${{d.fecha}}</small><br>
                            ${{d.motivo_alerta ? `<span class="badge-alerta">${{d.motivo_alerta}}</span>` : ''}}
                            <button class="btn-g btn-outline" style="width:100%; margin-top:8px;" onclick="verDetalle('${{d._id}}', ${{d.estado === 'Pendiente'}})">Ver Detalle</button>
                        </div>`;
                    } else if(tipoActual === 'puntos') {{
                        html += `<div class="card-mini"><b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || 'N/A'}}</small></div>`;
                    } else if(tipoActual === 'usuarios') {{
                        html += `<div class="card-mini"><b>${{d.nombre_completo}}</b><br><small>${{d.rol}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:8px;" onclick="editarUsuario('${{d._id}}')">Editar</button>
                        </div>`;
                    }}
                }});
                grid.innerHTML = html || '<p>Sin resultados.</p>';
            }}

            function filtrar() {{
                const val = document.getElementById('buscador').value.toLowerCase();
                const filtrados = datosActuales.filter(d => (d.pv || d['Punto de Venta'] || d.nombre_completo || '').toLowerCase().includes(val));
                renderizar(filtrados);
            }}

            async function verDetalle(id, permitirAccion) {{
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                document.getElementById('m_body').innerHTML = `
                    <h3 style="margin:0 0 10px 0;">${{d.pv}}</h3>
                    <p style="font-size:13px"><b>Distancia:</b> ${{d.distancia || 0}}m<br><b>BMB Propuesto:</b> ${{d.bmb_propuesto}}</p>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <img src="${{d.f_bmb}}" class="img-preview"><img src="${{d.f_fachada}}" class="img-preview">
                    </div>
                    ${{permitirAccion ? `<div style="display:flex; gap:10px; margin-top:15px;">
                        <button class="btn-g btn-primary" style="flex:1" onclick="validar('${{id}}','aprobar')">Aprobar</button>
                        <button class="btn-g btn-outline" style="flex:1; color:red; border-color:red" onclick="validar('${{id}}','rechazar')">Rechazar</button>
                    </div>` : ''}}
                    <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="document.getElementById('m_global').style.display='none'">Cerrar</button>`;
                document.getElementById('m_global').style.display='block';
            }}

            async function editarUsuario(id) {{
                const r = await fetch('/api/detalle/usuarios/' + id);
                const d = await r.json();
                document.getElementById('m_body').innerHTML = `
                    <h3>Editar Usuario</h3>
                    <label>Nombre</label><input id="unom" value="${{d.nombre_completo}}">
                    <label>Usuario</label><input id="uusr" value="${{d.usuario}}">
                    <label>Rol</label><select id="urol"><option value="admin" ${{d.rol=='admin'?'selected':''}}>Admin</option><option value="asesor" ${{d.rol=='asesor'?'selected':''}}>Asesor</option></select>
                    <button class="btn-g btn-primary" style="width:100%" onclick="guardarU('${{id}}')">Guardar</button>
                    <button class="btn-g btn-outline" style="width:100%; margin-top:5px" onclick="document.getElementById('m_global').style.display='none'">Cancelar</button>`;
                document.getElementById('m_global').style.display='block';
            }}

            async function guardarU(id) {{
                await fetch('/api/update/usuarios/'+id, {{
                    method:'POST', headers:{{'Content-Type':'application/json'}},
                    body: JSON.stringify({{nombre_completo: document.getElementById('unom').value, usuario: document.getElementById('uusr').value, rol: document.getElementById('urol').value}})
                }});
                document.getElementById('m_global').style.display='none'; cargar('usuarios');
            }}

            async function validar(id, op) {{
                await fetch(\`/api/v_final/${{id}}/${{op}}\`);
                document.getElementById('m_global').style.display='none'; cargar('validaciones');
            }}
            window.onload = () => cargar("{'validaciones' if rol=='admin' else 'puntos'}");
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
        
        pv_in = request.form.get('pv')
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        gps = request.form.get('gps')
        ruta_ant = pnt.get('Ruta', "0,0") if pnt else "0,0"
        dist = calcular_distancia(gps, ruta_ant)
        
        bmb_p = request.form.get('bmb')
        bmb_a = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        
        motivo_alerta = ""
        if not pnt: motivo_alerta = "Nuevo Punto"
        elif bmb_p != bmb_a: motivo_alerta = "Cambio de BMB"
        elif dist > 150: motivo_alerta = "Fuera de Rango"

        visitas_col.insert_one({
            "pv": pv_in, "bmb_actual": bmb_a, "bmb_propuesto": bmb_p,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "n_documento": session.get('user_name'), "ubicacion": gps,
            "ruta_anterior": ruta_ant, "distancia": dist,
            "estado": "Pendiente" if motivo_alerta else "Aprobado",
            "motivo_alerta": motivo_alerta, "motivo": request.form.get('motivo_v'),
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        if not motivo_alerta: puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_p, "Ruta": gps}}, upsert=True)
        gc.collect() # Limpieza de memoria tras procesar imágenes
        return redirect('/')
        
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_GERENCIAL}</head><body onload='navigator.geolocation.getCurrentPosition(p=>document.getElementById(\"gps\").value=p.coords.latitude+\",\"+p.coords.longitude)'><div class='container' style='max-width:400px;'><div class='card-mini' style='padding:20px; border:none;'><h2 style='margin-top:0;'>Nueva Visita</h2><form method='POST' enctype='multipart/form-data'><label>Punto de Venta</label><input list='pts' name='pv' oninput='buscarPV(this.value)' required autocomplete='off'><datalist id='pts'></datalist><label>BMB Propuesto</label><input type='text' name='bmb' id='bmb_i' required><label>Motivo Visita</label><input name='motivo_v' list='mv' required><datalist id='mv'><option value='Visita Exitosa'><option value='Local Cerrado'><option value='Rechazo BMB'></datalist><label>Fotos</label><input type='file' name='f1' accept='image/*' capture='camera'><input type='file' name='f2' accept='image/*' capture='camera'><input type='hidden' name='gps' id='gps'><button class='btn-g btn-primary' style='width:100%; margin-top:15px;'>Guardar Reporte</button><a href='/' class='btn-g btn-outline' style='margin-top:10px;'>Volver</a></form></div></div><script>async function buscarPV(val) {{ if(val.length < 3) return; const r = await fetch('/api/search/puntos?q=' + val); const data = await r.json(); document.getElementById('pts').innerHTML = data.map(p => `<option value=\"${{p['Punto de Venta']}}\">`).join(''); const found = data.find(x => x['Punto de Venta'] === val); if(found) document.getElementById('bmb_i').value = found.BMB || ''; }}</script></body></html>")

@app.route('/exportar_reportes')
def exportar_reportes():
    if session.get('role') != 'admin': return "Acceso Denegado", 403
    
    # DEFINICIÓN ESTRICTA DE COLUMNAS PARA EVITAR DESORDEN
    COLS = ["pv", "n_documento", "fecha", "bmb_actual", "bmb_propuesto", "ubicacion", "ruta_anterior", "distancia", "estado", "motivo_alerta", "motivo"]
    
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(COLS)
    
    # IMPORTANTE: Proyectamos solo lo necesario (0 fotos) para que no sea lento
    visitas = visitas_col.find({}, {c: 1 for c in COLS})
    for v in visitas:
        cw.writerow([v.get(c, "") for c in COLS])
    
    gc.collect()
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=reporte_nestle.csv"})

@app.route('/api/get/<tipo>')
def api_get(tipo):
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": {"$ne": "Pendiente"}} if tipo == 'visitas' else {}
    col = db['visitas' if tipo in ['visitas','validaciones'] else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    # Proyectamos para no traer las fotos (f_bmb, f_fachada) que pesan megas
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(100))
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
    query = {"Punto de Venta": {"$regex": q, "$options": "i"}} if q else {}
    res = list(puntos_col.find(query, {"f_bmb":0, "f_fachada":0}).limit(15))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u:
            session.permanent = True
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string("<html><head>"+CSS_GERENCIAL+"</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card-mini' style='width:300px; padding:20px; border:none;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
