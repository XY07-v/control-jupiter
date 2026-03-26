from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_executive_v19_fixed"

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
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }
    .btn-g { padding: 10px 18px; border-radius: 8px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: 0.2s; white-space: nowrap; text-decoration: none; justify-content: center; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .btn-danger { background: #FF3B30; color: white; }
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .badge-warn { background: #FFF9E6; color: #FF9500; }
    .badge-success { background: #E8F5E9; color: #2E7D32; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 95%; max-width: 500px; border-radius: 16px; padding: 25px; max-height: 85vh; overflow-y: auto; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; }
    .img-preview { width: 100%; border-radius: 10px; margin-top: 10px; border: 1px solid #eee; }
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
            <div id="grid_data" class="grid-cards"></div>
        </div>

        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>
        
        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Importar Puntos</h3>
            <input type="file" id="f_csv" accept=".csv">
            <button class="btn-g btn-primary" style="width:100%" onclick="subirCSV()">Procesar</button>
            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>
        </div></div>

        <script>
            function openModal(id) {{ document.getElementById(id).style.display='block'; }}
            function closeModal() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargar(tipo) {{
                const grid = document.getElementById('grid_data');
                grid.innerHTML = 'Cargando...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                let html = '';
                data.forEach(d => {{
                    if(tipo === 'validaciones') {{
                        html += `<div class="card-mini" style="border-left: 5px solid #FF9500;">
                            <span class="badge badge-warn">Pendiente</span>
                            <div style="margin: 10px 0;"><b>\${{d.pv}}</b><br><small>\${{d.n_documento}}</small></div>
                            <button class="btn-g btn-primary" style="width:100%" onclick="verDetalle('\${{d._id}}', true)">Revisar</button>
                        </div>`;
                    }} else if(tipo === 'visitas') {{
                        html += `<div class="card-mini">
                            <span class="badge badge-success">Aprobado</span>
                            <div style="margin: 10px 0;"><b>\${{d.pv}}</b><br><small>\${{d.fecha}}</small></div>
                            <button class="btn-g btn-outline" style="width:100%" onclick="verDetalle('\${{d._id}}', false)">Detalles</button>
                        </div>`;
                    }} else if(tipo === 'puntos') {{
                        html += `<div class="card-mini">
                            <b>\${{d['Punto de Venta']}}</b><br><small>BMB: \${{d.BMB || 'N/A'}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="formEdit('puntos', '\${{d._id}}')">Editar</button>
                        </div>`;
                    }} else if(tipo === 'usuarios') {{
                        html += `<div class="card-mini">
                            <b>\${{d.nombre_completo}}</b><br><small>Rol: \${{d.rol}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="formEdit('usuarios', '\${{d._id}}')">Editar</button>
                        </div>`;
                    }}
                }});
                grid.innerHTML = html || '<p>No hay registros.</p>';
            }}

            async function verDetalle(id, botones) {{
                openModal('m_global');
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                let h = `<h3>Detalle</h3><p><b>\${{d.pv}}</b></p>
                    <div style="font-size:12px;">Base: \${{d.bmb_actual}} | Propuesto: <b style="color:blue">\${{d.bmb_propuesto}}</b></div>
                    <img src="\${{d.f_bmb}}" class="img-preview"><img src="\${{d.f_fachada}}" class="img-preview">`;
                if(botones) {{
                    h += `<div style="display:flex; gap:10px; margin-top:15px;">
                        <button class="btn-g btn-primary" style="flex:1" onclick="vFinal('\${{id}}','aprobar')">APROBAR</button>
                        <button class="btn-g btn-danger" style="flex:1" onclick="vFinal('\${{id}}','rechazar')">RECHAZAR</button>
                    </div>`;
                }}
                document.getElementById('m_body').innerHTML = h + `<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>`;
            }}

            async function formEdit(tipo, id) {{
                openModal('m_global');
                const r = await fetch(\`/api/detalle/\${{tipo}}/\${{id}}\`);
                const d = await r.json();
                let f = \`<h3>Editar \${{tipo}}</h3><form id="ef">\`;
                for(let k in d) if(k!='_id' && !k.startsWith('f_')) f += \`<label style="font-size:11px;">\${{k}}</label><input name="\${{k}}" value="\${{d[k]}}">\`;
                f += \`</form><button class="btn-g btn-primary" style="width:100%" onclick="saveEd('\${{tipo}}','\${{id}}')">Guardar</button>\`;
                document.getElementById('m_body').innerHTML = f + \`<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cancelar</button>\`;
            }}

            async function saveEd(t, id) {{
                const data = Object.fromEntries(new FormData(document.getElementById('ef')));
                await fetch(\`/api/update/\${{t}}/\${{id}}\`, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(data)}});
                closeModal(); cargar(t);
            }}

            async function vFinal(id, op) {{
                await fetch(\`/api/v_final/\${{id}}/\${{op}}\`);
                closeModal(); cargar('validaciones');
            }}

            async function subirCSV() {{
                const fd = new FormData(); fd.append('file_csv', document.getElementById('f_csv').files[0]);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Procesados: " + res.count); closeModal(); cargar('puntos');
            }}

            window.onload = () => cargar('validaciones');
        </script>
    </body></html>
    """)

# --- APIs CORREGIDAS ---

@app.route('/api/get/<tipo>')
def api_get(tipo):
    # Lógica: Validaciones y Visitas consultan la misma colección 'visitas'
    col_name = 'visitas' if tipo in ['visitas', 'validaciones'] else 'puntos_venta' if tipo == 'puntos' else 'usuarios'
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    res = list(db[col_name].find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    # IMPORTANTE: Mapear correctamente el tipo a la colección real de MongoDB
    col_name = 'visitas' if tipo in ['visitas', 'validaciones'] else 'puntos_venta' if tipo == 'puntos' else 'usuarios'
    d = db[col_name].find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/<tipo>/<id>', methods=['POST'])
def api_up(tipo, id):
    col_name = 'puntos_venta' if tipo == 'puntos' else 'usuarios'
    db[col_name].update_one({"_id": ObjectId(id)}, {"$set": request.json})
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

# --- EL RESTO SE MANTIENE IGUAL AL v1.py PERO CON LIMPIEZA ---

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f: return ""
            return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
        pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('gps')
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        bmb_base = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        estado = "Pendiente" if (bmb_in != bmb_base or dist > 100) else "Aprobado"
        visitas_col.insert_one({
            "pv": pv_in, "bmb_actual": bmb_base, "bmb_propuesto": bmb_in,
            "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'),
            "ubicacion": gps, "estado": estado,
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        if estado == "Aprobado":
            puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
        return redirect('/formulario?msg=OK')
    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "_id": 0}))
    return render_template_string(f"<html><head>{CSS_GERENCIAL}</head><body>...Formulario...</body></html>") # (Omitido por brevedad, igual al v1)

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    content = f.stream.read().decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(content), delimiter=';' if ';' in content else ',')
    lista = [r for r in reader]
    if lista: puntos_col.delete_many({}); puntos_col.insert_many(lista)
    return jsonify({"count": len(lista)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_GERENCIAL}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card-mini' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/descargar')
def descargar():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'BMB Base', 'BMB Propuesto', 'Fecha', 'Asesor'])
    for r in cursor: w.writerow([r.get('pv'), r.get('bmb_actual'), r.get('bmb_propuesto'), r.get('fecha'), r.get('n_documento')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
