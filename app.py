from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:<db_password>@cluster0.ytmei.mongodb.net/NestleDB?retryWrites=true&w=majority&appName=Cluster0"
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

CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); min-height: 100vh; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); }
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; transition: 0.2s; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 600px; border-radius: 25px; padding: 25px; max-height: 85vh; overflow-y: auto; position: relative; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #F2F2F7; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    @media (max-width: 768px) { .sidebar { width: 0; padding: 0; display:none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v["pv"]}</b><br><small>{v["fecha"]} - {v["n_documento"]}</small></div>' for v in visitas])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
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
        <div class="main-content"><h3>Historial de Visitas</h3>{rows}</div>
        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva de Puntos</h3>
            <input type="file" id="f_csv" accept=".csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar CSV</button>
        </div></div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let pts_data = [];
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargaP() {{
                const r = await fetch('/api/puntos'); pts_data = await r.json();
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Puntos</h3>';
                h += '<input type="text" id="bus_p" placeholder="Buscar..." onkeyup="filP()"><div id="tabla_p"></div>';
                document.getElementById('cont_p_modal').innerHTML = h; renderTablaP(pts_data);
            }}
            function renderTablaP(data) {{
                let h = '<table><tr><th>Punto</th><th>BMB</th><th>Acción</th></tr>';
                data.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']||''}}</td><td><button class="btn btn-light" style="padding:5px;" onclick=\'editP(${{JSON.stringify(p)}})\'>Editar</button></td></tr>`);
                document.getElementById('tabla_p').innerHTML = h + '</table>';
            }}
            function filP() {{
                const v = document.getElementById('bus_p').value.toLowerCase();
                renderTablaP(pts_data.filter(p => p['Punto de Venta'].toLowerCase().includes(v) || (p['BMB']||'').toLowerCase().includes(v)));
            }}
            function editP(p) {{
                let form = '<h3>Editar Punto</h3>';
                Object.keys(p).forEach(k => {{ if(k!='_id') form += `<label style="font-size:10px;">${{k}}</label><input type="text" id="ed_${{k}}" value="${{p[k]}}">`; }});
                form += `<button class="btn btn-blue" onclick="saveP('${{p._id}}')">Guardar</button><button class="btn btn-light" onclick="cargaP()">Regresar</button>`;
                document.getElementById('cont_p_modal').innerHTML = form;
            }}
            async function saveP(id) {{
                let d = {{}}; document.querySelectorAll('[id^="ed_"]').forEach(i => d[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:d}})}});
                cargaP();
            }}

            async function cargaU() {{
                const r = await fetch('/api/usuarios'); const us = await r.json();
                let h = '<button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button><h3>Usuarios</h3>';
                h += '<button class="btn btn-blue" onclick="editU()">+ Nuevo Usuario</button><table>';
                us.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td><button class="btn btn-light" onclick=\'editU(${{JSON.stringify(u)}})\'>Editar</button></td></tr>`);
                document.getElementById('cont_u_modal').innerHTML = h + '</table>';
            }}
            function editU(u={{}}) {{
                const form = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor" ${{u.rol=='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol=='admin'?'selected':''}}>Admin</option></select>
                <button class="btn btn-blue" onclick="saveU('${{u._id||''}}')">Guardar</button><button class="btn btn-light" onclick="cargaU()">Regresar</button>`;
                document.getElementById('cont_u_modal').innerHTML = form;
            }}
            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                cargaU();
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); closeM();
            }}

            async function verVisita(id) {{
                openM('m_det'); const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeM()">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}" style="width:100%;"><img src="${{d.f2}}" style="width:100%;">`;
                const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f and f.filename else ""
        pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        bmb_duplicado = puntos_col.find_one({"BMB": bmb_in, "Punto de Venta": {"$ne": pv_in}})
        duplicado_info = bmb_duplicado['Punto de Venta'] if bmb_duplicado else ""

        if not pnt:
            bmb_orig, ruta_orig, dist, estado_v, is_new = "NUEVO", "", 0, "Pendiente", True
        else:
            bmb_orig, ruta_orig = pnt.get('BMB', ""), pnt.get('Ruta', "")
            dist = calcular_distancia(gps, ruta_orig)
            estado_v = "Pendiente" if (bmb_in != bmb_orig or dist > 100 or duplicado_info) else "Aprobado"
            is_new = False

        visitas_col.insert_one({
            "pv": pv_in, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
            "ruta_anterior": ruta_orig, "distancia": round(dist, 1), "estado": estado_v,
            "bmb_duplicado_en": duplicado_info, "is_new": is_new,
            "motivo": request.form.get('motivo'), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        if estado_v == "Aprobado":
            puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}})
        return redirect('/formulario?msg=OK')
    
    puntos_raw = list(puntos_col.find({}, {"_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}"> ' for p in puntos_raw])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px; margin:auto; padding:20px;">
            <div class="card">
                <h2 style="text-align:center; color:var(--ios-blue);">Nestlé BI</h2>
                <button class="btn btn-light" onclick="openGuia()">🔍 Guía Puntos / BMB</button>
                <form method="POST" enctype="multipart/form-data">
                    <label style="font-size:11px;">Nombre Punto (Escriba o Seleccione)</label>
                    <input list="pts" name="pv" id="pv_i" oninput="vincularBMB(this.value)" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <label style="font-size:11px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:11px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue">Enviar Reporte</button>
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        <div id="m_guia" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="this.parentElement.parentElement.style.display='none'">Cerrar</button>
            <h3>Referencia de Datos</h3>
            <input type="text" id="bus_g" placeholder="Filtrar..." onkeyup="filG()">
            <div id="tabla_g"></div>
        </div></div>
        <script>
            const data_pts = {json.dumps(puntos_raw)};
            function vincularBMB(val) {{
                const p = data_pts.find(x => x['Punto de Venta'] === val);
                if(p) document.getElementById('bmb_i').value = p.BMB || '';
            }}
            function openGuia() {{ document.getElementById('m_guia').style.display='block'; filG(); }}
            function filG() {{
                const v = document.getElementById('bus_g').value.toLowerCase();
                let h = '<table><tr><th>Punto</th><th>BMB</th></tr>';
                data_pts.filter(p => p['Punto de Venta'].toLowerCase().includes(v) || (p['BMB']||'').toLowerCase().includes(v))
                       .forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']||''}}</td></tr>`);
                document.getElementById('tabla_g').innerHTML = h + '</table>';
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = ""
    for r in pends:
        duplicado = f'<div style="color:red; font-weight:bold; background:#fff0f0; padding:10px; border-radius:10px; margin-bottom:10px;">⚠️ BMB ACTUALMENTE EN: {r.get("bmb_duplicado_en")}</div>' if r.get('bmb_duplicado_en') else ''
        tipo = '<b style="color:green;">[ASIGNACIÓN NUEVA]</b>' if r.get('is_new') else ''
        rows += f'''<div class="card" style="border-left: 8px solid #FF9500;">
            {duplicado}
            <h3>{r['pv']} {tipo}</h3>
            <p>Distancia: {r.get('distancia')}m | {r.get('n_documento')}</p>
            <div style="background:#f2f2f7; padding:10px; border-radius:10px; font-size:12px;">
                BMB Base: {r.get('bmb')} | <b style="color:var(--ios-blue);">Propuesto: {r.get('bmb_propuesto')}</b>
            </div>
            <div style="display:flex; gap:5px; margin-top:10px;"><img src="{r['f_bmb']}" style="width:50%;"><img src="{r['f_fachada']}" style="width:50%;"></div>
            <button class="btn btn-blue" onclick="vF('{r['_id']}', 'aprobar')">Aprobar (Actualizar Punto/BMB)</button>
            <button class="btn btn-light" style="color:red;" onclick="vF('{r['_id']}', 'rechazar')">Rechazar</button>
        </div>'''
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body><div class='sidebar'><a href='/' class='btn btn-light'>← Volver</a></div><div class='main-content'><h2>Validaciones</h2>{rows or '<p>No hay pendientes.</p>'}</div><script>async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if not v: return jsonify({"s":"error"})
    
    if op == 'aprobar':
        bmb_objetivo = v['bmb_propuesto']
        # Lógica de Ajuste: Buscar si el BMB ya existe en algún punto
        punto_existente = puntos_col.find_one({"BMB": bmb_objetivo})
        
        if punto_existente:
            # SI EL BMB YA EXISTE: Actualizamos ese registro con el nuevo nombre de punto y ubicación
            puntos_col.update_one(
                {"BMB": bmb_objetivo}, 
                {"$set": {"Punto de Venta": v['pv'], "Ruta": v['ubicacion']}}
            )
        else:
            # SI EL BMB NO EXISTE: Creamos/Actualizamos el registro por nombre de Punto de Venta
            puntos_col.update_one(
                {"Punto de Venta": v['pv']}, 
                {"$set": {"BMB": bmb_objetivo, "Ruta": v['ubicacion']}}, 
                upsert=True
            )
        
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        if lista: 
            puntos_col.delete_many({})
            puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/api/puntos')
def api_p(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)

@app.route('/api/actualizar_punto', methods=['POST'])
def api_up_p(): 
    d = request.json
    puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']})
    return jsonify({"s": "ok"})

@app.route('/api/usuarios')
def api_u(): 
    u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]
    return jsonify(u)

@app.route('/api/actualizar_usuario', methods=['POST'])
def api_up_u():
    d = request.json
    if d.get('id'): 
        usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}})
    else: 
        usuarios_col.insert_one({"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']})
    return jsonify({"s": "ok"})

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Propuesto', 'Ruta Anterior', 'Ruta Nueva', 'Diferencia Metros', 'Estado'])
    for r in cursor: 
        w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('ruta_anterior', ''), r.get('ubicacion', ''), r.get('distancia', 0), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/get_img/<id>')
def api_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
