from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_restored"

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

# --- CSS ORIGINAL RESTABLECIDO ---
# Ajustado para que los modales sean responsivos en móviles
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; overflow-x: hidden; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); min-height: 100vh; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); cursor: pointer; transition: 0.2s; }
    .card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; transition: 0.2s; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    
    /* MODALES RESPONSIVOS */
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; overflow: hidden; }
    .modal-content { background: white; margin: 5vh auto; width: 92%; max-width: 600px; border-radius: 25px; padding: 20px; max-height: 85vh; overflow-y: auto; box-sizing: border-box; position: relative; }
    
    /* Buscador */
    .search-container { display: flex; gap: 8px; margin-bottom: 15px; }
    .search-input { flex: 1; padding: 12px; border-radius: 12px; border: 1px solid #ddd; font-size: 14px; }
    .btn-search { background: var(--ios-blue); color: white; border: none; border-radius: 12px; width: 45px; cursor: pointer; }

    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #F2F2F7; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    img { max-width: 100%; border-radius: 12px; margin-top: 10px; }
    
    @media (max-width: 768px) { 
        .sidebar { width: 0; padding: 0; display:none; } 
        .main-content { margin-left: 0; width: 100%; padding: 15px; } 
        .modal-content { margin: 2vh auto; width: 96%; max-height: 96vh; border-radius: 15px; padding: 15px; }
    }
</style>
"""

# --- RUTAS ADMIN (DISEÑO ORIGINAL RESTABLECIDO) ---

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    # Optimización de RAM: No cargamos fotos en el listado principal
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(40))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v.get("pv", "N/A")}</b><br><small>{v.get("fecha", "")} - {v.get("n_documento", "")}</small></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:13px; font-weight:bold;">{session['user_name']}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Datos</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content">
            <h3>Historial de Visitas</h3>
            
            <div class="search-container">
                <input type="text" id="q_historial" class="search-input" placeholder="Buscar por punto o asesor...">
                <button class="btn-search" onclick="buscarDinamico('historial')">🔍</button>
            </div>
            
            <div id="cont_historial">{rows or '<p>No hay visitas.</p>'}</div>
        </div>

        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="f_csv" accept=".csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar</button>
        </div></div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeModal(id) {{ document.getElementById(id).style.display='none'; }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            // BUSCADORES DINÁMICOS CON BOTÓN
            async function buscarDinamico(tipo) {{
                const q = document.getElementById('q_'+tipo).value;
                const cont = document.getElementById('cont_'+tipo);
                cont.innerHTML = 'Buscando...';
                
                const r = await fetch(`/api/search?tipo=${{tipo}}&q=${{q}}`);
                const data = await r.json();
                
                let html = '';
                if(tipo === 'historial') {{
                    data.forEach(v => html += `<div class="card" onclick="verVisita('${{v._id}}')"><b>${{v.pv}}</b><br><small>${{v.fecha}} - ${{v.n_documento}}</small></div>`);
                    cont.innerHTML = html || '<p>Sin resultados.</p>';
                }} else if(tipo === 'puntos') {{
                    renderTablaP(data);
                }} else if(tipo === 'users') {{
                    renderTablaU(data);
                }}
            }}

            // GESTIÓN DE PUNTOS (RESTABLECIDA)
            async function cargaP() {{
                let h = '<button class="btn btn-light" onclick="closeModal(\\'m_puntos\\')" style="width:100px; float:right;">Cerrar</button><h3>Puntos</h3>';
                h += '<div class="search-container"><input type="text" id="q_puntos" class="search-input" placeholder="Buscar punto o BMB..."><button class="btn-search" onclick="buscarDinamico(\\'puntos\\')">🔍</button></div>';
                h += '<div id="tabla_p">Cargando...</div>';
                document.getElementById('cont_p_modal').innerHTML = h;
                const r = await fetch('/api/get/puntos'); const data = await r.json();
                renderTablaP(data);
            }}
            function renderTablaP(data) {{
                let h = '<table><tr><th>Punto</th><th>BMB</th><th>Acción</th></tr>';
                data.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']||''}}</td><td><button class="btn btn-light" style="padding:5px;" onclick=\'editGeneric("puntos", ${{JSON.stringify(p)}})\'>Editar</button></td></tr>`);
                document.getElementById('tabla_p').innerHTML = h + '</table>';
            }}

            // GESTIÓN DE USUARIOS (RESTABLECIDA)
            async function cargaU() {{
                let h = '<button class="btn btn-light" onclick="closeModal(\\'m_users\\')" style="width:100px; float:right;">Cerrar</button><h3>Usuarios</h3>';
                h += '<button class="btn btn-blue" onclick="editGeneric(\\'usuarios\\', {{}})">+ Nuevo</button>';
                h += '<div class="search-container"><input type="text" id="q_users" class="search-input" placeholder="Buscar usuario..."><button class="btn-search" onclick="buscarDinamico(\\'users\\')">🔍</button></div>';
                h += '<div id="tabla_u">Cargando...</div>';
                document.getElementById('cont_u_modal').innerHTML = h;
                const r = await fetch('/api/get/usuarios'); const data = await r.json();
                renderTablaU(data);
            }}
            function renderTablaU(data) {{
                let h = '<table><tr><th>Nombre</th><th>Rol</th><th>Acción</th></tr>';
                data.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td><td><button class="btn btn-light" style="padding:5px;" onclick=\'editGeneric("usuarios", ${{JSON.stringify(u)}})\'>Editar</button></td></tr>`);
                document.getElementById('tabla_u').innerHTML = h + '</table>';
            }}

            // FORMULARIO DE EDICIÓN GENÉRICO (RESTABLECIDO)
            function editGeneric(tipo, doc) {{
                const modalId = tipo === 'puntos' ? 'cont_p_modal' : 'cont_u_modal';
                const volverFn = tipo === 'puntos' ? 'cargaP()' : 'cargaU()';
                let form = `<h3>Editar ${{tipo==='puntos'?'Punto':'Usuario'}}</h3><form id="form_edit">`;
                Object.keys(doc).forEach(k => {{
                    if(k!='_id' && !k.includes('f_')) form += `<label style="font-size:10px;">${{k}}</label><input type="text" name="${{k}}" value="${{doc[k]||''}}">`;
                }});
                form += `</form><button class="btn btn-blue" onclick="saveGeneric('${{tipo}}','${{doc._id||''}}')">Guardar</button><button class="btn btn-light" onclick="${{volverFn}}">Regresar</button>`;
                document.getElementById(modalId).innerHTML = form;
            }}
            async function saveGeneric(tipo, id) {{
                const fd = new FormData(document.getElementById('form_edit'));
                const json = Object.fromEntries(fd.entries());
                await fetch(\`/api/update/${{tipo}}/${{id}}\`, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(json)}});
                tipo === 'puntos' ? cargaP() : cargaU();
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                location.reload();
            }}

            async function verVisita(id) {{
                openM('m_det'); document.getElementById('det_body').innerHTML = "Cargando...";
                const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeModal(\'m_det\')">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}"><img src="${{d.f2}}">`;
                const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
            }}
        </script>
    </body></html>
    """)

# --- RUTAS FORMULARIO (AJUSTADO CON BUSCADOR DINÁMICO) ---

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        try:
            def b64(f): 
                if not f or not f.filename: return ""
                encoded = base64.b64encode(f.read()).decode()
                f.close()
                return f"data:image/jpeg;base64,{encoded}"
            
            pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
            pnt = puntos_col.find_one({"Punto de Venta": pv_in})
            bmb_duplicado = puntos_col.find_one({"BMB": bmb_in, "Punto de Venta": {"$ne": pv_in}})
            
            bmb_orig = pnt.get('BMB', "") if pnt else "NUEVO"
            ruta_orig = pnt.get('Ruta', "") if pnt else ""
            dist = calcular_distancia(gps, ruta_orig)
            
            duplicado_en = bmb_duplicado['Punto de Venta'] if bmb_duplicado else ""
            estado_v = "Pendiente" if (bmb_in != bmb_orig or dist > 100 or duplicado_en) else "Aprobado"

            visitas_col.insert_one({
                "pv": pv_in, "n_documento": session.get('user_name'), "fecha": request.form.get('fecha'),
                "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
                "distancia": round(dist, 1), "estado": estado_v,
                "bmb_duplicado_en": duplicado_en, "is_new": not pnt,
                "motivo": request.form.get('motivo'), 
                "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
            })

            if estado_v == "Aprobado":
                puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}})
            
            gc.collect()
            return redirect('/formulario?msg=OK')
        except Exception as e: return f"Error: {str(e)}", 500
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px; margin:auto; padding:20px;">
            <div class="card">
                <h2 style="text-align:center; color:var(--ios-blue);">Nestlé BI</h2>
                
                <label style="font-size:11px;">1. Buscar Punto de Venta</label>
                <div class="search-container">
                    <input type="text" id="bus_pv" class="search-input" placeholder="Escriba el nombre...">
                    <button class="btn-search" onclick="buscarPuntoFormulario()">🔍</button>
                </div>

                <form method="POST" enctype="multipart/form-data">
                    <label style="font-size:11px;">Punto Seleccionado</label>
                    <input type="text" name="pv" id="res_pv" readonly placeholder="No seleccionado" required style="background:#f9f9f9;">
                    
                    <label style="font-size:11px;">BMB Base de Datos (Lectura)</label>
                    <input type="text" id="res_bmb_base" readonly style="background:#f9f9f9;">
                    
                    <label style="font-size:11px;">2. Confirmar BMB Máquina (Escriba)</label>
                    <input type="text" name="bmb" placeholder="Escriba el BMB actual" required>
                    
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <label style="font-size:11px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:11px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        
        <div id="m_bus_form" class="modal"><div class="modal-content">
            <h4>Resultados</h4>
            <div id="res_bus_form" style="max-height:300px; overflow-y:auto;"></div>
            <button class="btn btn-light" onclick="closeModalForm()">Cerrar</button>
        </div></div>

        <script>
            // Lógica de búsqueda manual con botón para el formulario
            async function buscarPuntoFormulario() {{
                const q = document.getElementById('bus_pv').value;
                if(!q) return;
                const r = await fetch('/api/search?tipo=puntos&q=' + q);
                const data = await r.json();
                const modal = document.getElementById('m_bus_form');
                const cont = document.getElementById('res_bus_form');
                
                modal.style.display = 'block';
                cont.innerHTML = '';
                
                if(data.length === 0) {{
                    cont.innerHTML = '<p style="text-align:center; font-size:12px;">No se encontraron puntos.</p>';
                    return;
                }}
                
                data.forEach(p => {{
                    const div = document.createElement('div');
                    div.className = 'card';
                    div.style.padding = '10px';
                    div.style.marginBottom = '5px';
                    div.style.fontSize = '12px';
                    div.innerHTML = `<b>${{p['Punto de Venta']}}</b><br>BMB: ${{p.BMB || 'N/A'}}`;
                    div.onclick = () => {{
                        document.getElementById('res_pv').value = p['Punto de Venta'];
                        document.getElementById('res_bmb_base').value = p.BMB || 'N/A';
                        modal.style.display = 'none';
                    }};
                    cont.appendChild(div);
                }});
            }}
            function closeModalForm() {{ document.getElementById('m_bus_form').style.display = 'none'; }}
        </script>
    </body></html>
    """)

# --- RUTA VALIDACIONES (DISEÑO ORIGINAL RESTABLECIDO) ---

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}, {"f_bmb":0, "f_fachada":0}))
    rows = ""
    for r in pends:
        duplicado = f'<div style="color:red; font-weight:bold; background:#fff0f0; padding:10px; border-radius:10px; margin-bottom:10px;">⚠️ BMB EN: {r.get("bmb_duplicado_en")}</div>' if r.get('bmb_duplicado_en') else ''
        rows += f'''<div class="card" style="border-left: 8px solid #FF9500;">
            {duplicado}
            <h3>{r['pv']}</h3>
            <p>Dist: {r.get('distancia')}m | {r.get('n_documento')}</p>
            <div style="background:#f2f2f7; padding:10px; border-radius:10px; font-size:12px;">
                BMB Base: {r.get('bmb')} | <b style="color:var(--ios-blue);">Propuesto: {r.get('bmb_propuesto')}</b>
            </div>
            <div style="display:flex; gap:5px; margin-top:10px;">
                <button class="btn btn-light" style="flex:1;" onclick="verVisitaValidar('{r['_id']}')">Ver Fotos</button>
                <button class="btn btn-blue" style="flex:1;" onclick="vF('{r['_id']}', 'aprobar')">Aprobar</button>
                <button class="btn btn-danger" style="flex:1; background:#FF3B30;" onclick="vF('{r['_id']}', 'rechazar')">Rechazar</button>
            </div>
        </div>'''
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>{CSS_FIXED}</head><body><div class='sidebar'><a href='/' class='btn btn-light'>← Volver</a></div><div class='main-content'><h2>Validaciones</h2>{rows or '<p>No hay pendientes.</p>'}</div><div id='m_val' class='modal'><div class='modal-content' id='val_body'></div></div><script>function closeModalV() {{ document.getElementById('m_val').style.display='none'; }} async function verVisitaValidar(id){{ document.getElementById('m_val').style.display='block'; document.getElementById('val_body').innerHTML='Cargando...'; const r=await fetch('/get_img/'+id); const d=await r.json(); document.getElementById('val_body').innerHTML='<button class="btn btn-light" onclick="closeModalV()">Cerrar</button><img src="'+d.f1+'"><img src="'+d.f2+'">';}} async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

# --- APIs DE CONTROL ---

@app.route('/api/search')
def api_search():
    tipo = request.args.get('tipo')
    q = request.args.get('q', '')
    query = {}
    
    if tipo == 'historial':
        col = visitas_col
        query["estado"] = {"$ne": "Pendiente"}
        if q: query["$or"] = [{"pv": {"$regex": q, "$options": "i"}}, {"n_documento": {"$regex": q, "$options": "i"}}]
    elif tipo == 'puntos':
        col = puntos_col
        if q: query["$or"] = [{"Punto de Venta": {"$regex": q, "$options": "i"}}, {"BMB": {"$regex": q, "$options": "i"}}]
    elif tipo == 'users':
        col = usuarios_col
        if q: query["$or"] = [{"nombre_completo": {"$regex": q, "$options": "i"}}, {"usuario": {"$regex": q, "$options": "i"}}]

    res = list(col.find(query, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(50))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/get/<tipo>')
def api_get_all(tipo):
    col = puntos_col if tipo == 'puntos' else usuarios_col
    res = list(col.find({}, {"f_bmb":0, "f_fachada":0}).sort("_id", -1).limit(100))
    for d in res: d['_id'] = str(d['_id'])
    return jsonify(res)

@app.route('/api/update/<tipo>/<id>', methods=['POST'])
def api_update(tipo, id):
    col = puntos_col if tipo == 'puntos' else usuarios_col
    data = request.json
    col.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"s":"ok"})

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar' and v:
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/get_img/<id>')
def api_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1, "ubicacion": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    content = f.stream.read().decode("utf-8-sig", errors="ignore")
    sep = ';' if content.count(';') > content.count(',') else ','
    reader = csv.DictReader(io.StringIO(content), delimiter=sep)
    lista = [r for r in reader]
    if lista:
        puntos_col.delete_many({})
        puntos_col.insert_many(lista)
    return jsonify({"count": len(lista)})

@app.route('/descargar')
def descargar():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Propuesto', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Clave'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
