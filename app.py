from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, gc, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_v20_final_responsive"

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

CSS_V20 = """
<style>
    :root { --nestle: #004a99; --bg: #F2F2F7; --white: #ffffff; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 0; color: #1c1c1e; overflow-x: hidden; }
    header { background: var(--white); padding: 15px; border-bottom: 1px solid #d1d1d6; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
    .container { padding: 12px; max-width: 1000px; margin: auto; }
    
    /* Barra de Búsqueda */
    .search-box { display: flex; gap: 8px; margin-bottom: 15px; }
    .search-box input { flex: 1; padding: 10px; border-radius: 10px; border: 1px solid #d1d1d6; font-size: 14px; }
    .btn-search { background: var(--nestle); color: white; border: none; border-radius: 10px; width: 45px; cursor: pointer; }

    /* Grid de tarjetas */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
    .card { background: var(--white); border-radius: 12px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 0.5px solid #d1d1d6; font-size: 13px; }
    
    /* Modales Ultra-Ajustables */
    .modal { display: none; position: fixed; top:0; left:0; width:100vw; height:100vh; background: rgba(0,0,0,0.4); backdrop-filter: blur(8px); z-index: 1000; }
    .modal-content { background: white; margin: 5vh auto; width: 92%; max-width: 500px; border-radius: 20px; padding: 20px; max-height: 85vh; overflow-y: auto; box-sizing: border-box; }
    
    .btn { padding: 12px; border-radius: 10px; border: none; font-weight: 600; cursor: pointer; font-size: 14px; text-align: center; text-decoration: none; display: block; width: 100%; margin-bottom: 8px; }
    .btn-blue { background: var(--nestle); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    
    img { width: 100%; border-radius: 12px; margin-top: 10px; }
    label { font-size: 11px; color: #8e8e93; font-weight: bold; }
    @media (max-width: 400px) { .grid { grid-template-columns: 1fr 1fr; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">{CSS_V20}</head>
    <body>
        <header>
            <b style="color:var(--nestle)">Nestlé BI Admin</b>
            <a href="/logout" style="font-size:12px; color:red; text-decoration:none;">Cerrar</a>
        </header>
        
        <div class="container">
            <div style="display:flex; gap:5px; overflow-x:auto; margin-bottom:15px; padding-bottom:5px;">
                <button class="btn btn-blue" style="width:auto; padding:8px 15px;" onclick="setModo('validaciones')">Pendientes</button>
                <button class="btn btn-light" style="width:auto; padding:8px 15px;" onclick="setModo('visitas')">Historial</button>
                <button class="btn btn-light" style="width:auto; padding:8px 15px;" onclick="setModo('puntos')">Puntos</button>
                <button class="btn btn-light" style="width:auto; padding:8px 15px;" onclick="setModo('usuarios')">Usuarios</button>
            </div>

            <div class="search-box">
                <input type="text" id="q_busqueda" placeholder="Buscar por nombre...">
                <button class="btn-search" onclick="ejecutarBusqueda()">🔍</button>
            </div>

            <div id="grid_display" class="grid"></div>
        </div>

        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>

        <script>
            let modoActual = 'validaciones';
            
            function setModo(m) {{ modoActual = m; ejecutarBusqueda(); }}

            async function ejecutarBusqueda() {{
                const q = document.getElementById('q_busqueda').value;
                const grid = document.getElementById('grid_display');
                grid.innerHTML = 'Buscando...';
                
                const r = await fetch(`/api/search?tipo=${{modoActual}}&q=${{q}}`);
                const data = await r.json();
                
                let html = '';
                data.forEach(d => {{
                    let titulo = d.pv || d.nombre_completo || d['Punto de Venta'];
                    let sub = d.fecha || d.rol || d.BMB;
                    html += `<div class="card" onclick="verMas('${{modoActual}}','${{d._id}}')">
                        <b style="color:var(--nestle)">${{titulo}}</b><br>
                        <small>${{sub}}</small>
                    </div>`;
                }});
                grid.innerHTML = html || '<p style="grid-column: 1/-1; text-align:center;">Sin coincidencias.</p>';
            }}

            async function verMas(tipo, id) {{
                const m = document.getElementById('m_global');
                const b = document.getElementById('m_body');
                m.style.display = 'block';
                b.innerHTML = 'Cargando...';
                
                const r = await fetch(`/api/detalle/${{tipo}}/${{id}}`);
                const d = await r.json();
                
                let content = `<h3>Detalles</h3>`;
                for(let k in d) {{
                    if(k.includes('f_')) content += `<img src="${{d[k]}}">`;
                    else if(k !== '_id') content += `<p><b>${{k}}:</b> ${{d[k]}}</p>`;
                }}
                
                if(tipo === 'validaciones') {{
                    content += `<div style="display:flex; gap:10px;">
                        <button class="btn btn-blue" onclick="vFinal('${{id}}','aprobar')">Aprobar</button>
                        <button class="btn btn-light" style="color:red" onclick="vFinal('${{id}}','rechazar')">Rechazar</button>
                    </div>`;
                }}
                content += `<button class="btn btn-light" onclick="document.getElementById('m_global').style.display='none'">Cerrar</button>`;
                b.innerHTML = content;
            }}

            async function vFinal(id, op) {{
                await fetch(\`/api/v_final/${{id}}/${{op}}\`);
                document.getElementById('m_global').style.display='none';
                ejecutarBusqueda();
            }}

            window.onload = ejecutarBusqueda;
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f or not f.filename: return ""
            b = base64.b64encode(f.read()).decode(); f.close()
            return f"data:image/jpeg;base64,{b}"
        
        pv = request.form.get('pv')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_base = pnt.get('BMB', "NUEVO") if pnt else "NUEVO"
        gps = request.form.get('gps')
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        
        visitas_col.insert_one({
            "pv": pv, "bmb_actual": bmb_base, "bmb_propuesto": request.form.get('bmb'),
            "fecha": request.form.get('fecha'), "n_documento": session.get('user_name'),
            "ubicacion": gps, "distancia": round(dist, 1), "estado": "Pendiente",
            "f_bmb": to_b64(request.files.get('f1')), "f_fachada": to_b64(request.files.get('f2'))
        })
        gc.collect()
        return redirect('/formulario?msg=OK')

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">{CSS_V20}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <header><b style="color:var(--nestle)">Nuevo Reporte</b><a href="/logout">Salir</a></header>
        <div class="container">
            <div class="card">
                <label>Buscar Punto de Venta</label>
                <div class="search-box">
                    <input type="text" id="bus_pv" placeholder="Escribe el nombre...">
                    <button class="btn-search" onclick="buscarPunto()">🔍</button>
                </div>
                
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="pv" id="res_pv" readonly placeholder="Punto Seleccionado" required>
                    <label>BMB en Base de Datos</label>
                    <input type="text" id="res_bmb_base" readonly style="background:#f9f9f9">
                    
                    <label>BMB Detectado (Escriba el nuevo)</label>
                    <input type="text" name="bmb" placeholder="Confirmar BMB" required>
                    
                    <label>Fecha</label>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    
                    <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                </form>
            </div>
        </div>
        
        <div id="m_bus" class="modal"><div class="modal-content">
            <h4>Resultados</h4><div id="res_bus"></div>
            <button class="btn btn-light" onclick="document.getElementById('m_bus').style.display='none'">Cerrar</button>
        </div></div>

        <script>
            async function buscarPunto() {{
                const q = document.getElementById('bus_pv').value;
                const r = await fetch('/api/search?tipo=puntos&q=' + q);
                const data = await r.json();
                const m = document.getElementById('m_bus');
                const res = document.getElementById('res_bus');
                m.style.display='block';
                res.innerHTML = '';
                data.forEach(p => {{
                    const div = document.createElement('div');
                    div.className = 'card'; div.style.marginBottom='5px';
                    div.innerHTML = p['Punto de Venta'];
                    div.onclick = () => {{
                        document.getElementById('res_pv').value = p['Punto de Venta'];
                        document.getElementById('res_bmb_base').value = p.BMB;
                        m.style.display='none';
                    }};
                    res.appendChild(div);
                }});
            }}
        </script>
    </body></html>
    """)

# --- API DE BÚSQUEDA DINÁMICA ---
@app.route('/api/search')
def api_search():
    tipo = request.args.get('tipo')
    q = request.args.get('q', '')
    
    col = visitas_col if tipo in ['visitas', 'validaciones'] else puntos_col if tipo == 'puntos' else usuarios_col
    
    query = {}
    if tipo == 'validaciones': query["estado"] = "Pendiente"
    if tipo == 'visitas': query["estado"] = "Aprobado"
    
    if q:
        # Busca en múltiples campos según el tipo
        search_filter = {"$or": [
            {"pv": {"$regex": q, "$options": "i"}},
            {"Punto de Venta": {"$regex": q, "$options": "i"}},
            {"nombre_completo": {"$regex": q, "$options": "i"}},
            {"n_documento": {"$regex": q, "$options": "i"}}
        ]}
        query.update(search_filter)
        
    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/detalle/<tipo>/<id>')
def api_det(tipo, id):
    col = visitas_col if tipo in ['visitas', 'validaciones'] else puntos_col if tipo == 'puntos' else usuarios_col
    d = col.find_one({"_id": ObjectId(id)})
    if d: d['_id'] = str(d['_id'])
    return jsonify(d)

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
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_V20}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:280px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario' style='width:100%; margin-bottom:10px; padding:10px; border-radius:8px; border:1px solid #ccc;'><input type='password' name='p' placeholder='Clave' style='width:100%; margin-bottom:10px; padding:10px; border-radius:8px; border:1px solid #ccc;'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
