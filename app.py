from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

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
    :root { --nestle-blue: #004a99; --bg: #F5F7F9; --accent: #007AFF; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; color: #333; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; position: sticky; top: 0; z-index: 100; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    
    .action-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; }
    .btn-g { 
        height: 40px; padding: 0 20px; border-radius: 10px; border: none; 
        font-size: 13px; font-weight: 600; cursor: pointer; 
        display: flex; align-items: center; justify-content: center; 
        transition: 0.2s; text-decoration: none; white-space: nowrap;
    }
    .btn-primary { background: var(--nestle-blue); color: white; }
    .btn-outline { background: white; color: var(--nestle-blue); border: 1px solid var(--nestle-blue); }
    .btn-danger { background: #FF3B30; color: white; }

    .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
    .card-mini { background: white; border-radius: 15px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #eee; position: relative; }
    
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(5px); z-index: 1000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 550px; border-radius: 20px; padding: 25px; max-height: 85vh; overflow-y: auto; }
    
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
    .img-det { width: 100%; border-radius: 10px; margin-top: 10px; }
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
            <div style="font-weight: 800; color: var(--nestle-blue); font-size: 20px;">Nestlé BI <small style="font-weight:300">Admin</small></div>
            <div style="font-size: 12px;">{session.get('user_name')} | <a href="/logout" style="color:red;">Salir</a></div>
        </header>
        <div class="container">
            <div class="action-bar">
                <button class="btn-g btn-primary" onclick="cargar('validaciones')">⚠️ Pendientes</button>
                <button class="btn-g btn-outline" onclick="cargar('visitas')">📜 Historial</button>
                <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Puntos</button>
                <button class="btn-g btn-outline" onclick="cargar('usuarios')">👥 Usuarios</button>
                <button class="btn-g btn-outline" onclick="openM('m_csv')">📥 Importar</button>
                <a href="/descargar" class="btn-g btn-outline">📤 Exportar</a>
            </div>
            <div id="grid_data" class="grid-cards"></div>
        </div>

        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Importar Puntos (CSV)</h3>
            <input type="file" id="f_csv" accept=".csv">
            <button class="btn-g btn-primary" style="width:100%" onclick="subirCSV()">Subir Archivo</button>
            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeM()">Cerrar</button>
        </div></div>

        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargar(tipo) {{
                const grid = document.getElementById('grid_data');
                grid.innerHTML = 'Cargando...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                let html = '';
                
                data.forEach(d => {{
                    if(tipo === 'validaciones') {{
                        html += `<div class="card-mini" style="border-left: 5px solid #FF9500;">
                            <b>${{d.pv}}</b><br><small>${{d.n_documento}}</small>
                            <button class="btn-g btn-primary" style="width:100%; margin-top:10px;" onclick="verVisita('${{d._id}}', true)">REVISAR</button>
                        </div>`;
                    }} else if(tipo === 'visitas') {{
                        html += `<div class="card-mini">
                            <b>${{d.pv}}</b><br><small>${{d.fecha}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="verVisita('${{d._id}}', false)">VER</button>
                        </div>`;
                    }} else if(tipo === 'puntos') {{
                        html += `<div class="card-mini">
                            <b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || ''}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="editGeneric('puntos', '${{d._id}}')">EDITAR</button>
                        </div>`;
                    }} else if(tipo === 'usuarios') {{
                        html += `<div class="card-mini">
                            <b>${{d.nombre_completo}}</b><br><small>${{d.rol}}</small>
                            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="editGeneric('usuarios', '${{d._id}}')">EDITAR</button>
                        </div>`;
                    }}
                }});
                grid.innerHTML = html || 'No hay datos.';
            }}

            async function verVisita(id, conBotones) {{
                openM('m_global');
                const r = await fetch('/api/detalle/visitas/' + id);
                const d = await r.json();
                let html = `<h3>Detalle de Visita</h3>
                    <p><b>Punto:</b> ${{d.pv}}<br><b>Propuesto:</b> ${{d.bmb_propuesto}}</p>
                    <img src="${{d.f_bmb}}" class="img-det">
                    <img src="${{d.f_fachada}}" class="img-det">`;
                
                if(conBotones) {{
                    html += `<div style="display:flex; gap:10px; margin-top:15px;">
                        <button class="btn-g btn-primary" style="flex:1" onclick="vFinal('${{id}}','aprobar')">ACEPTAR</button>
                        <button class="btn-g btn-danger" style="flex:1" onclick="vFinal('${{id}}','rechazar')">RECHAZAR</button>
                    </div>`;
                }}
                html += `<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeM()">Volver</button>`;
                document.getElementById('m_body').innerHTML = html;
            }}

            async function editGeneric(tipo, id) {{
                openM('m_global');
                const r = await fetch(\`/api/detalle/\${{tipo}}/\${{id}}\`);
                const d = await r.json();
                let form = \`<h3>Editar \${{tipo}}</h3><form id="ef">\`;
                for(let k in d) if(k!='_id' && !k.startsWith('f_')) form += \`<label>\${{k}}</label><input name="\${{k}}" value="\${{d[k]}}">\`;
                form += \`</form><button class="btn-g btn-primary" style="width:100%" onclick="saveGeneric('\${{tipo}}','\${{id}}')">Guardar</button>\`;
                document.getElementById('m_body').innerHTML = form + \`<button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeM()">Cancelar</button>\`;
            }}

            async function saveGeneric(t, id) {{
                const data = Object.fromEntries(new FormData(document.getElementById('ef')));
                await fetch(\`/api/update/\${{t}}/\${{id}}\`, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(data)}});
                closeM(); cargar(t);
            }}

            async function vFinal(id, op) {{
                await fetch(\`/api/v_final/\${{id}}/\${{op}}\`);
                closeM(); cargar('validaciones');
            }}

            async function subirCSV() {{
                const fd = new FormData(); fd.append('file_csv', document.getElementById('f_csv').files[0]);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count);
                closeM(); cargar('puntos');
            }}

            window.onload = () => cargar('validaciones');
        </script>
    </body></html>
    """)

# --- APIS CORREGIDAS (Basadas en REAL INAL.py) ---

@app.route('/api/get/<tipo>')
def api_get(tipo):
    col = db['visitas' if (tipo=='visitas' or tipo=='validaciones') else 'puntos_venta' if tipo=='puntos' else 'usuarios']
    query = {"estado": "Pendiente"} if tipo == 'validaciones' else {"estado": "Aprobado"} if tipo == 'visitas' else {}
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col_name = 'visitas' if tipo == 'visitas' or tipo == 'validaciones' else 'puntos_venta' if tipo == 'puntos' else 'usuarios'
    d = db[col_name].find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

@app.route('/api/update/<tipo>/<id>', methods=['POST'])
def api_upd(tipo, id):
    col_name = 'puntos_venta' if tipo == 'puntos' else 'usuarios'
    db[col_name].update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"s": "ok"})

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
    if not f: return jsonify({"count": 0})
    content = f.stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content), delimiter=';' if ';' in content else ',')
    lista = [r for r in reader]
    if lista: puntos_col.delete_many({}); puntos_col.insert_many(lista)
    return jsonify({"count": len(lista)})

# --- FORMULARIO Y LOGIN ---

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f: return ""
            return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
        visitas_col.insert_one({
            "pv": request.form.get('pv'), "bmb_propuesto": request.form.get('bmb'),
            "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'),
            "ubicacion": request.form.get('gps'), "estado": "Pendiente",
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        return redirect('/formulario?success=true')
    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "_id": 0}))
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:400px;">
            <div class="card-mini">
                <h3 style="text-align:center">Nuevo Reporte</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Punto de Venta" required>
                    <datalist id="pts">{"".join([f'<option value="{p["Punto de Venta"]}">' for p in pts])}</datalist>
                    <input type="text" name="bmb" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn-g btn-primary" style="width:100%">Enviar</button>
                    <a href="/logout" class="btn-g btn-outline" style="margin-top:10px;">Salir</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Propuesto', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb_propuesto'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_GERENCIAL}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card-mini' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn-g btn-primary' style='width:100%'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
