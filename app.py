from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_fixed_root_v21"

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
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; border-bottom: 1px solid #ddd; position: sticky; top: 0; z-index: 100; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 20px; }
    .card-mini { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; position: relative; overflow: hidden; }
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }
    .search-group { display: flex; gap: 5px; margin-top: 15px; background: white; padding: 5px; border-radius: 25px; border: 1px solid #ddd; }
    .search-group input { border: none; padding: 10px 15px; flex-grow: 1; outline: none; border-radius: 20px; }
    .btn-g { padding: 10px 18px; border-radius: 8px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .btn-danger { background: #FF3B30; color: white; }
    .badge-info { font-size: 10px; padding: 3px 7px; border-radius: 5px; background: #E3F2FD; color: #1976D2; font-weight: bold; margin-top: 5px; display: inline-block; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 500px; border-radius: 15px; padding: 20px; max-height: 85vh; overflow-y: auto; }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; }
    input[type="text"], input[type="date"], select { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    rol = session.get('role')
    user_name = session.get('user_name')

    # CONCATENACIÓN PURA PARA EVITAR EL PROBLEMA DE LAS LLAVES { }
    html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">' + CSS_GERENCIAL + '</head><body>'
    html += '<header><div style="font-weight: 800; color: var(--nestle-blue);">Nestlé BI Dashboard</div>'
    html += '<div style="font-size: 12px;">' + str(user_name) + ' | <a href="/logout" style="color:red; text-decoration:none;">Salir</a></div></header>'
    
    html += '<div class="container"><div class="action-bar">'
    if rol == 'admin':
        html += '<button class="btn-g btn-primary" onclick="cargar(\'validaciones\')">⚠️ Validaciones</button>'
        html += '<button class="btn-g btn-outline" onclick="cargar(\'visitas\')">📋 Historial</button>'
        html += '<button class="btn-g btn-outline" onclick="cargar(\'puntos\')">📍 Puntos</button>'
        html += '<button class="btn-g btn-outline" onclick="cargar(\'usuarios\')">👥 Usuarios</button>'
        html += '<a href="/descargar" class="btn-g btn-outline">📤 Exportar</a>'
    else:
        html += '<a href="/formulario" class="btn-g btn-primary">📝 Nuevo Reporte</a>'
        html += '<button class="btn-g btn-outline" onclick="cargar(\'puntos\')">📍 Consultar Puntos</button>'
    
    html += '</div><div class="search-group" id="search_container" style="display:none;">'
    html += '<input type="text" id="buscador" placeholder="Buscar por Nombre o BMB...">'
    html += '<button class="btn-g btn-primary" style="border-radius: 20px;" onclick="ejecutarBusqueda()">🔍 Buscar</button></div>'
    html += '<div id="grid_data" class="grid-cards"></div></div>'
    
    html += '<div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>'
    
    # JAVASCRIPT SIN INTERFERENCIA DE PYTHON
    html += """
    <script>
        let tipoActual = '';
        const miRol = '""" + str(rol) + """';

        function openM() { document.getElementById('m_global').style.display='block'; }
        function closeM() { document.getElementById('m_global').style.display='none'; }

        async function cargar(tipo) {
            tipoActual = tipo;
            document.getElementById('search_container').style.display = (tipo === 'puntos' || tipo === 'visitas' || tipo === 'usuarios') ? 'flex' : 'none';
            document.getElementById('buscador').value = '';
            
            if(tipo === 'puntos') {
                document.getElementById('grid_data').innerHTML = '<p style="grid-column:1/-1; text-align:center; color:gray; margin-top:20px;">Use la barra superior para buscar un punto por nombre.</p>';
            } else {
                ejecutarBusqueda(); 
            }
        }

        async function ejecutarBusqueda() {
            const query = document.getElementById('buscador').value;
            const grid = document.getElementById('grid_data');
            grid.innerHTML = '<p style="grid-column:1/-1; text-align:center;">Buscando...</p>';
            
            const r = await fetch('/api/get/' + tipoActual + '?q=' + encodeURIComponent(query));
            const data = await r.json();
            
            let htmlCards = '';
            data.forEach(d => {
                if(tipoActual === 'validaciones' || tipoActual === 'visitas') {
                    let motivo = d.distancia_m > 100 ? '📍 Fuera de Rango' : (d.bmb_actual === 'NUEVO' ? '🆕 Punto Nuevo' : '🔄 Cambio BMB');
                    let color = d.estado === 'Pendiente' ? '#FF9500' : '#2E7D32';
                    htmlCards += `<div class="card-mini" style="border-left: 5px solid ${color};">
                        <div style="padding:10px;">
                            <b>${d.pv}</b><br><small>${d.fecha}</small><br>
                            <span class="badge-info">${motivo}</span>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px; padding:5px;" onclick="verDetalle('${d._id}', ${d.estado === 'Pendiente'})">Ver Detalle</button>
                        </div>
                    </div>`;
                } else if(tipoActual === 'puntos') {
                    htmlCards += `<div class="card-mini"><div style="padding:10px;">
                        <b>${d['Punto de Venta']}</b><br><small>BMB: ${d.BMB || 'N/A'}</small>
                        ${miRol === 'admin' ? `<button class="btn-g btn-outline" style="width:100%; margin-top:10px; padding:5px;" onclick="formEdit('puntos', '${d._id}')">Editar</button>` : ''}
                    </div></div>`;
                } else if(tipoActual === 'usuarios') {
                    htmlCards += `<div class="card-mini"><div style="padding:10px;">
                        <b>${d.nombre_completo}</b><br><small>Rol: ${d.rol}</small>
                        <button class="btn-g btn-outline" style="width:100%; margin-top:10px; padding:5px;" onclick="formEdit('usuarios', '${d._id}')">Editar</button>
                    </div></div>`;
                }
            });
            grid.innerHTML = htmlCards || '<p style="grid-column:1/-1; text-align:center; color:gray;">No se encontraron registros.</p>';
        }

        async function verDetalle(id, botones) {
            openM();
            const r = await fetch('/api/detalle/visitas/' + id);
            const d = await r.json();
            let h = `<h3>Detalle de Visita</h3>
                <div style="font-size:13px; margin-bottom:10px;">
                    <b>${d.pv}</b><br>
                    BMB Actual: ${d.bmb_actual}<br>
                    BMB Propuesto: ${d.bmb_propuesto}<br>
                    Distancia: ${d.distancia_m} metros
                </div>
                <img src="${d.f_bmb}" class="img-preview">
                <div style="display:flex; gap:10px; margin-top:20px;">
                    ${botones ? `
                        <button class="btn-g btn-primary" style="flex:1" onclick="validar('${id}','aprobar')">Aprobar</button>
                        <button class="btn-g btn-danger" style="flex:1" onclick="validar('${id}','rechazar')">Rechazar</button>
                    ` : ''}
                </div>
                <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeM()">Cerrar</button>`;
            document.getElementById('m_body').innerHTML = h;
        }

        async function validar(id, op) {
            await fetch('/api/v_final/' + id + '/' + op);
            closeM();
            cargar('validaciones');
        }

        async function formEdit(tipo, id) {
            openM();
            const r = await fetch('/api/detalle/' + tipo + '/' + id);
            const d = await r.json();
            let f = '<h3>Editar Registro</h3><form id="eF">';
            for(let k in d) {
                if(k !== '_id' && (typeof d[k] !== 'string' || d[k].length < 200)) {
                    f += `<label style="font-size:11px; font-weight:bold;">${k}</label>
                          <input type="text" name="${k}" value="${d[k]}">`;
                }
            }
            f += '</form><button class="btn-g btn-primary" style="width:100%; margin-top:10px;" onclick="guardarEd(\''+tipo+'\', \''+id+'\')">Guardar Cambios</button>';
            f += '<button class="btn-g btn-outline" style="width:100%; margin-top:8px;" onclick="closeM()">Cancelar</button>';
            document.getElementById('m_body').innerHTML = f;
        }

        async function guardarEd(t, id) {
            const fd = new FormData(document.getElementById('eF'));
            await fetch('/api/update/'+t+'/'+id, {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify(Object.fromEntries(fd))
            });
            closeM(); 
            cargar(t);
        }

        window.onload = () => cargar(miRol === 'admin' ? 'validaciones' : 'puntos');
    </script>
    </body></html>
    """
    return render_template_string(html)

# --- LAS APIS SE MANTIEENEN IGUAL (YA FUNCIONAN) ---
@app.route('/api/get/<tipo>')
def api_get(tipo):
    q = request.args.get('q', '').strip()
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    if q:
        query.update({"$or": [{"pv": {"$regex": q, "$options": "i"}}, {"Punto de Venta": {"$regex": q, "$options": "i"}}, {"BMB": {"$regex": q, "$options": "i"}}]})
    col = db['visitas' if tipo in ['visitas', 'validaciones'] else 'puntos_venta' if tipo == 'puntos' else 'usuarios']
    limit = 100 if tipo in ['visitas', 'validaciones'] else 50
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(limit))
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
    db['visitas' if tipo=='visitas' else 'puntos_venta' if tipo=='puntos' else 'usuarios'].update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s":"ok"})

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else: visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/descargar')
def descargar():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'BMB Ant', 'BMB Nuevo', 'Fecha', 'Asesor', 'Distancia'])
    for r in cursor: w.writerow([r.get('pv'), r.get('bmb_actual'), r.get('bmb_propuesto'), r.get('fecha'), r.get('n_documento'), r.get('distancia_m')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=reporte.csv"})

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
        estado = "Pendiente" if (bmb_in != bmb_base or dist > 100 or bmb_base == "NUEVO") else "Aprobado"
        visitas_col.insert_one({"pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in, "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'), "motivo": request.form.get('motivo'), "ubicacion": gps, "distancia_m": round(dist, 1), "estado": estado, "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))})
        if estado == "Aprobado": puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        return redirect('/formulario?msg=OK')
    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in pts])
    return render_template_string('<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">' + CSS_GERENCIAL + '</head><body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById(\'gps\').value=p.coords.latitude+\',\'+p.coords.longitude)"><div class="container" style="max-width:400px;"><div class="card-mini"><h2>Reporte</h2><form method="POST" enctype="multipart/form-data"><input list="pts" name="pv" placeholder="Punto de Venta" required><datalist id="pts">' + opts + '</datalist><input type="text" name="bmb" placeholder="BMB"><select name="motivo"><option>Visita Exitosa</option></select><input type="date" name="fecha" value="' + datetime.now().strftime('%Y-%m-%d') + '"><input type="file" name="f1" capture="camera"><input type="file" name="f2" capture="camera"><input type="hidden" name="gps" id="gps"><button class="btn-g btn-primary" style="width:100%; margin-top:10px;">Enviar</button><div style="display:flex; gap:10px; margin-top:10px;"><a href="/" class="btn-g btn-outline" style="flex:1">Regresar</a><a href="/logout" class="btn-g btn-danger" style="flex:1">Salir</a></div></form></div></div></body></html>')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'admin')}); return redirect('/')
    return render_template_string('<html><head>' + CSS_GERENCIAL + '</head><body style="display:flex; justify-content:center; align-items:center; height:100vh;"><div class="card-mini" style="width:300px;"><h3>Acceso</h3><form method="POST"><input type="text" name="u" placeholder="Usuario"><input type="password" name="p" placeholder="Clave"><button class="btn-g btn-primary" style="width:100%">Entrar</button></form></div></body></html>')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
