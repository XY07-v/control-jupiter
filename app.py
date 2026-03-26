from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_v22_stable"

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
    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
    .card-mini { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 5px solid transparent; }
    .action-bar { display: flex; gap: 10px; margin-bottom: 15px; overflow-x: auto; }
    .btn-g { padding: 10px 15px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; text-decoration: none; display: flex; align-items: center; justify-content: center; font-size: 13px; }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .search-box { width: 100%; margin-bottom: 15px; }
    .search-box input { width: 100%; padding: 12px; border-radius: 20px; border: 1px solid #ccc; outline: none; box-sizing: border-box; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); z-index: 1000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 500px; border-radius: 15px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
    .img-preview { width: 100%; border-radius: 8px; margin-top: 10px; }
    .badge-alerta { background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    rol = session.get('role')
    
    btn_admin = f"""
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
            <div style="font-size: 12px;">{session.get('user_name')} | <a href="/logout" style="color:red;">Salir</a></div>
        </header>
        <div class="container">
            <div class="action-bar">{btn_admin}</div>
            <div class="search-box" id="s_cont" style="display:none;"><input type="text" id="busc" placeholder="Buscar..." onkeyup="filtrar()"></div>
            <div id="grid" class="grid-cards"></div>
        </div>
        <div id="modal" class="modal"><div class="modal-content" id="m_body"></div></div>

        <script>
            let datos = []; let tipoAct = '';
            async function cargar(tipo) {{
                tipoAct = tipo;
                document.getElementById('s_cont').style.display = 'block';
                const grid = document.getElementById('grid');
                grid.innerHTML = 'Cargando...';
                const r = await fetch('/api/get/' + tipo);
                datos = await r.json();
                render(datos);
            }}

            function render(data) {{
                let h = '';
                data.forEach(d => {{
                    if(tipoAct==='validaciones' || tipoAct==='visitas') {{
                        let clr = d.estado === 'Pendiente' ? '#f59e0b' : '#10b981';
                        h += `<div class="card-mini" style="border-left-color: ${{clr}}">
                            <b>${{d.pv}}</b><br><small>${{d.fecha}}</small><br>
                            ${{d.motivo_alerta ? `<span class="badge-alerta">${{d.motivo_alerta}}</span>` : ''}}
                            <button class="btn-g btn-outline" style="width:100%;margin-top:10px" onclick="verDet('${{d._id}}', ${{d.estado=='Pendiente'}})">Detalle</button>
                        </div>`;
                    }} else if(tipoAct==='puntos') {{
                        h += `<div class="card-mini"><b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB}}</small></div>`;
                    }} else if(tipoAct==='usuarios') {{
                        h += `<div class="card-mini"><b>${{d.nombre_completo}}</b><br><small>${{d.rol}}</small>
                        <button class="btn-g btn-outline" style="width:100%;margin-top:10px" onclick="editUser('${{d._id}}')">Editar</button></div>`;
                    }}
                }});
                document.getElementById('grid').innerHTML = h || 'No hay datos';
            }}

            function filtrar() {{
                const q = document.getElementById('busc').value.toLowerCase();
                const f = datos.filter(d => (d.pv || d['Punto de Venta'] || d.nombre_completo || '').toLowerCase().includes(q));
                render(f);
            }}

            async function verDet(id, btns) {{
                const r = await fetch('/api/detalle/visitas/'+id);
                const d = await r.json();
                document.getElementById('m_body').innerHTML = `<h3>${{d.pv}}</h3>
                    <p>BMB Actual: ${{d.bmb_actual}}<br>BMB Propuesto: ${{d.bmb_propuesto}}<br>Motivo: ${{d.motivo}}</p>
                    <img src="${{d.f_bmb}}" class="img-preview"><img src="${{d.f_fachada}}" class="img-preview">
                    ${{btns ? `<div style="display:flex;gap:5px;margin-top:10px"><button class="btn-g btn-primary" style="flex:1" onclick="v('${{id}}','aprobar')">Aprobar</button><button class="btn-g btn-outline" style="flex:1" onclick="v('${{id}}','rechazar')">Rechazar</button></div>`:''}}
                    <button class="btn-g btn-outline" style="width:100%;margin-top:10px" onclick="document.getElementById('modal').style.display='none'">Cerrar</button>`;
                document.getElementById('modal').style.display='block';
            }}

            async function v(id, op) {{ await fetch(\`/api/v_final/${{id}}/${{op}}\`); document.getElementById('modal').style.display='none'; cargar('validaciones'); }}

            async function editUser(id) {{
                const r = await fetch('/api/detalle/usuarios/'+id);
                const d = await r.json();
                document.getElementById('m_body').innerHTML = `<h3>Editar Usuario</h3>
                    <input id="enom" value="${{d.nombre_completo}}"><input id="eusr" value="${{d.usuario}}"><input id="epas" value="${{d.password}}">
                    <select id="erol"><option value="admin" ${{d.rol=='admin'?'selected':''}}>Admin</option><option value="asesor" ${{d.rol=='asesor'?'selected':''}}>Asesor</option></select>
                    <button class="btn-g btn-primary" style="width:100%" onclick="saveUser('${{id}}')">Guardar</button>`;
                document.getElementById('modal').style.display='block';
            }}

            async function saveUser(id) {{
                await fetch('/api/update/usuarios/'+id, {{
                    method: 'POST', headers: {{'Content-Type':'application/json'}},
                    body: JSON.stringify({{nombre_completo: document.getElementById('enom').value, usuario: document.getElementById('eusr').value, password: document.getElementById('epas').value, rol: document.getElementById('erol').value}})
                }});
                document.getElementById('modal').style.display='none'; cargar('usuarios');
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
        
        pv, bmb_p, gps = request.form.get('pv'), request.form.get('bmb_p'), request.form.get('gps')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_a = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        
        motivo_alerta = ""
        if not pnt: motivo_alerta = "Punto Nuevo"
        elif bmb_p != bmb_a: motivo_alerta = "Cambio BMB"
        elif calcular_distancia(gps, pnt.get('Ruta')) > 150: motivo_alerta = "Fuera de Rango"

        visitas_col.insert_one({
            "pv": pv, "n_documento": session.get('user_name'), "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "bmb_actual": bmb_a, "bmb_propuesto": bmb_p, "ubicacion": gps,
            "motivo": request.form.get('motivo'), "estado": "Pendiente" if motivo_alerta else "Aprobado",
            "motivo_alerta": motivo_alerta, "distancia": 0, # Se puede calcular si es necesario
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        if not motivo_alerta: puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"BMB": bmb_p, "Ruta": gps}}, upsert=True)
        return redirect('/')

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:400px">
            <div class="card-mini" style="padding:20px">
                <h2>Reporte de Visita</h2>
                <form method="POST" enctype="multipart/form-data">
                    <label>Punto de Venta</label><input list="pts" name="pv" oninput="buscarPV(this.value)" required autocomplete="off">
                    <datalist id="pts"></datalist>
                    <label>BMB Actual (Sistema)</label><input id="b_act" readonly style="background:#eee">
                    <label>BMB Propuesto / Detectado</label><input name="bmb_p" id="b_prop" required>
                    <label>Motivo de la Visita</label>
                    <input name="motivo" list="mots" placeholder="Escriba o elija motivo" required>
                    <datalist id="mots"><option value="Visita Exitosa"><option value="Punto Cerrado"><option value="Rechazo de BMB"></datalist>
                    <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera">
                    <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera">
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn-g btn-primary" style="width:100%;margin-top:15px">Enviar Reporte</button>
                    <a href="/" class="btn-g btn-outline" style="margin-top:10px">Regresar</a>
                </form>
            </div>
        </div>
        <script>
            async function buscarPV(val) {{
                if(val.length<3) return;
                const r = await fetch('/api/search/puntos?q='+val);
                const data = await r.json();
                document.getElementById('pts').innerHTML = data.map(p=>`<option value="${{p['Punto de Venta']}}">`).join('');
                const found = data.find(x => x['Punto de Venta'] === val);
                if(found) {{
                    document.getElementById('b_act').value = found.BMB;
                    document.getElementById('b_prop').value = found.BMB;
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/exportar_reportes')
def exportar_reportes():
    if session.get('role') != 'admin': return "Acceso Denegado", 403
    
    # ORDEN DE COLUMNAS ESTRICTO PARA QUE NO SE DESORDENE
    COLUMNAS = ["pv", "n_documento", "fecha", "bmb_actual", "bmb_propuesto", "ubicacion", "motivo", "estado", "motivo_alerta"]
    
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(COLUMNAS) # Cabecera
    
    visitas = list(visitas_col.find())
    for v in visitas:
        # Extraemos cada campo en el orden definido, si no existe ponemos vacío
        fila = [v.get(c, "") for c in COLUMNAS]
        cw.writerow(fila)
        
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=base_visitas.csv"})

@app.route('/api/get/<tipo>')
def api_get(tipo):
    col = db['visitas' if tipo in ['visitas','validaciones'] else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    q = {"estado": "Pendiente"} if tipo=='validaciones' else {"estado": {"$ne": "Pendiente"}} if tipo=='visitas' else {}
    res = list(col.find(q, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = db['visitas' if tipo=='visitas' else 'usuarios' if tipo=='usuarios' else 'puntos_venta']
    d = col.find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/usuarios/<id>', methods=['POST'])
def api_up_u(id):
    usuarios_col.update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s":"ok"})

@app.route('/api/search/puntos')
def api_search_puntos():
    q = request.args.get('q', '')
    res = list(puntos_col.find({"Punto de Venta": {"$regex": q, "$options": "i"}}, {"f_bmb":0, "f_fachada":0}).limit(10))
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string("<html><head>"+CSS_GERENCIAL+"</head><body style='display:flex;justify-content:center;align-items:center;height:100vh;'><div class='card-mini' style='width:300px'><h3>Nestlé Login</h3><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
