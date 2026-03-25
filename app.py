from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
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

# --- CSS PREMIUM CLEAN (BORDES Y BOTONES CORREGIDOS) ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --glass: rgba(255, 255, 255, 0.9); }
    body { font-family: -apple-system, system-ui, sans-serif; background: var(--bg); margin: 0; color: #1c1c1e; }
    
    /* Header & Containers */
    .header-bar { background: var(--glass); backdrop-filter: blur(20px); padding: 15px 20px; position: sticky; top: 0; z-index: 1000; border-bottom: 0.5px solid rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }
    .container { padding: 15px; max-width: 600px; margin: auto; }
    
    /* Cards Unificadas (Bordes Suaves) */
    .card { background: white; border-radius: 20px !important; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); overflow: hidden; }
    
    /* Botones Estilo iOS */
    .btn { padding: 12px 18px; border-radius: 14px; border: none; font-weight: 600; cursor: pointer; transition: 0.2s; font-size: 14px; text-decoration: none; display: inline-block; text-align: center; }
    .btn-blue { background: var(--ios-blue); color: white; width: 100%; box-sizing: border-box; }
    .btn-blue:active { background: #0056b3; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    
    /* Modales Corregidos */
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 550px; border-radius: 25px !important; padding: 25px; position: relative; max-height: 85vh; overflow-y: auto; }
    
    /* Tablas y Buscador */
    .search-box { width: 100%; padding: 12px; border-radius: 12px; border: 1px solid #D1D1D6; margin-bottom: 15px; font-size: 16px; outline: none; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
    th { text-align: left; padding: 10px; color: #8E8E93; border-bottom: 1px solid #E5E5EA; }
    td { padding: 12px 10px; border-bottom: 1px solid #F2F2F7; }
    
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; font-size: 15px; box-sizing: border-box; }
</style>
"""
FOOTER_HTML = '<div style="text-align:center; padding:20px; font-size:11px; color:#8e8e93;">Desarrollo de Andres Vanegas - Inteligencia de Negocio. Derechos Reservados.</div>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>CMR ASISTENCIA A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-blue'>ENTRAR</button></form></div>{FOOTER_HTML}</body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="card" onclick="verDetalle(\'{r["_id"]}\')"><b>{r.get("pv")}</b><br><small style="color:#8e8e93;">{r.get("fecha")} · {r.get("n_documento")}</small></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="header-bar">
            <h2 style="margin:0; font-size:20px;">Nestlé BI</h2>
            <div>
                <span style="font-size:12px; color:#8e8e93; margin-right:10px;">Hola, {session['user_name']}</span>
                <button class="btn btn-light" onclick="openM('m_menu')">Opciones</button>
            </div>
        </div>
        <div class="container">
            <h3>Visitas Recientes</h3>
            {rows}
        </div>

        <div id="m_menu" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="float:right;">X</button>
            <h3 style="margin-top:0;">Administración</h3>
            <a href="/formulario" class="btn btn-blue" style="margin-bottom:10px;">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="width:100%; margin-bottom:10px; color:#FF9500;">Pendientes de Validación</a>
            <button class="btn btn-light" style="width:100%; margin-bottom:10px;" onclick="openM('m_puntos')">Gestionar Puntos</button>
            <button class="btn btn-light" style="width:100%; margin-bottom:10px;" onclick="openM('m_users')">Gestionar Usuarios</button>
            <button class="btn btn-light" style="width:100%; margin-bottom:10px;" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light" style="width:100%; margin-bottom:10px;">Exportar CSV</a>
            <a href="/logout" class="btn btn-light" style="width:100%; color:red;">Cerrar Sesión</a>
        </div></div>

        <div id="m_puntos" class="modal"><div class="modal-content" style="max-width:800px;">
            <button class="btn btn-light" onclick="closeM()" style="margin-bottom:10px;">← Volver</button>
            <h3>Puntos de Venta</h3>
            <input type="text" id="bus_p" class="search-box" placeholder="Buscar en todas las columnas..." onkeyup="filP()">
            <div id="cont_p" style="overflow-x:auto;"></div>
        </div></div>

        <div id="m_users" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="margin-bottom:10px;">← Volver</button>
            <h3>Usuarios</h3>
            <button class="btn btn-blue" onclick="editU()" style="margin-bottom:15px;">+ Crear Usuario</button>
            <div id="cont_u"></div>
        </div></div>

        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()">← Volver</button>
            <h3>Carga Masiva CSV</h3>
            <input type="file" id="f_csv_file">
            <button class="btn btn-blue" onclick="subirCSV()">Procesar Archivo</button>
        </div></div>

        <div id="m_det" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="margin-bottom:15px;">← Cerrar</button>
            <div id="det_body"></div>
        </div></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let pts_data = [];
            document.addEventListener('keydown', e => {{ if(e.key === 'Escape') closeM(); }});
            function openM(id) {{ 
                document.getElementById(id).style.display='block'; 
                if(id=='m_puntos') cargaP(); 
                if(id=='m_users') cargaU(); 
            }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargaP() {{
                const res = await fetch('/api/puntos'); pts_data = await res.json();
                renderP(pts_data);
            }}

            function renderP(data) {{
                if(data.length === 0) return;
                const cols = Object.keys(data[0]).filter(k => k !== '_id');
                let h = '<table><tr>';
                cols.forEach(c => h += `<th>${{c}}</th>`);
                h += '<th>Acción</th></tr>';
                data.forEach(p => {{
                    h += '<tr>';
                    cols.forEach(c => h += `<td>${{p[c]||''}}</td>`);
                    h += `<td><button class="btn btn-light" onclick='editP(${{JSON.stringify(p)}})'>Edit</button></td></tr>`;
                }});
                document.getElementById('cont_p').innerHTML = h + '</table>';
            }}

            function filP() {{
                const val = document.getElementById('bus_p').value.toLowerCase();
                const filtered = pts_data.filter(p => Object.values(p).some(v => String(v).toLowerCase().includes(val)));
                renderP(filtered);
            }}

            function editP(p) {{
                let form = '<h3>Editar Punto</h3>';
                Object.keys(p).forEach(k => {{ if(k!='_id') form += `<label>${{k}}</label><input type="text" id="ed_${{k}}" value="${{p[k]}}">`; }});
                form += `<button class="btn btn-blue" onclick="saveP('${{p._id}}')">Guardar</button>`;
                document.getElementById('m_puntos').querySelector('.modal-content').innerHTML = '<button class="btn btn-light" onclick="cargaP()">← Volver</button>' + form;
            }}

            async function saveP(id) {{
                let d = {{}}; document.querySelectorAll('[id^="ed_"]').forEach(i => d[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:d}})}});
                cargaP();
            }}

            async function cargaU() {{
                const res = await fetch('/api/usuarios'); const users = await res.json();
                let h = '<table><tr><th>Nombre</th><th>Acción</th></tr>';
                users.forEach(u => {{
                    h += `<tr><td>${{u.nombre_completo}}</td><td><button class="btn btn-light" onclick='editU(${{JSON.stringify(u)}})'>Edit</button></td></tr>`;
                }});
                document.getElementById('cont_u').innerHTML = h + '</table>';
            }}

            function editU(u={{}}) {{
                const form = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor" ${{u.rol=='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol=='admin'?'selected':''}}>Admin</option></select>
                <button class="btn btn-blue" onclick="saveU('${{u._id||''}}')">Guardar Usuario</button>`;
                document.getElementById('m_users').querySelector('.modal-content').innerHTML = '<button class="btn btn-light" onclick="cargaU()">← Volver</button>' + form;
            }}

            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                cargaU();
            }}

            async function subirCSV() {{
                const f = document.getElementById('f_csv_file').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("✅ Cargados: " + res.count + " registros"); closeM();
            }}

            async function verDetalle(id) {{
                openM('m_det'); document.getElementById('det_body').innerHTML = "Cargando...";
                const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `
                    <div id="map" style="height:200px; border-radius:15px; margin-bottom:15px;"></div>
                    <img src="${{d.f1}}" style="width:100%; border-radius:15px; margin-bottom:10px;">
                    <img src="${{d.f2}}" style="width:100%; border-radius:15px;">
                `;
                if(d.gps) {{
                    const c = d.gps.split(',');
                    const m = L.map('map').setView(c, 15);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m);
                    L.marker(c).addTo(m);
                }}
            }}
        </script>
        {FOOTER_HTML}
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        pv = request.form.get('pv')
        bmb_in = request.form.get('bmb')
        gps = request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_orig = pnt.get('BMB') if pnt else ""
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        pend = (bmb_in != bmb_orig) or (dist > 100)
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in,
            "ubicacion": gps, "gps_anterior": pnt.get('Ruta') if pnt else gps, "distancia": round(dist, 1),
            "estado": "Pendiente" if pend else "Aprobado",
            "Nota": request.form.get('nota'), "motivo": request.form.get('motivo'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    msg_exito = ""
    if request.args.get('msg') == 'OK':
        msg_exito = '<div id="exito" style="position:fixed; top:20px; left:50%; transform:translateX(-50%); background:#34C759; color:white; padding:15px 30px; border-radius:15px; font-weight:bold; z-index:5000;">✓ Registro Exitoso</div><script>setTimeout(()=>document.getElementById("exito").remove(), 4000);</script>'

    btn_regresar = '<a href="/" class="btn btn-light" style="margin-bottom:15px;">← Panel Principal</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        {msg_exito}
        <div class="container" style="max-width:480px;">
            {btn_regresar}
            <div class="card">
                <h3 style="text-align:center; color:var(--ios-blue);">NUEVA VISITA</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" id="pv_i" placeholder="Seleccionar Punto" onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <textarea name="nota" placeholder="Observaciones"></textarea>
                    <label style="font-size:11px; opacity:0.6;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:11px; opacity:0.6;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue" style="margin-top:10px;">Enviar Reporte</button>
                    <a href="/logout" style="display:block; text-align:center; margin-top:20px; color:red; text-decoration:none;">Cerrar Sesión</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = ""
    for r in pends:
        rows += f'''<div class="card" style="border-left: 5px solid #FF9500;">
            <b>{r['pv']}</b><br><small>Alerta: {r['distancia']}m de distancia</small>
            <div style="display:flex; gap:10px; margin:15px 0;">
                <img src="{r['f_bmb']}" style="width:48%; border-radius:12px;">
                <img src="{r['f_fachada']}" style="width:48%; border-radius:12px;">
            </div>
            <div style="display:flex; gap:10px;">
                <button class="btn btn-blue" style="background:#34C759; flex:1;" onclick="vF('{r['_id']}', 'aprobar')">Aceptar</button>
                <button class="btn btn-light" style="color:red; flex:1;" onclick="vF('{r['_id']}', 'rechazar')">Rechazar</button>
            </div>
        </div>'''
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body><div class='container'><h2>Validación</h2>{rows or '<p>Todo al día</p>'}<br><a href='/' class='btn btn-gray'>Volver</a></div><script>async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

@app.route('/api/v_final/<id>/<op>')
def api_v_final(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        if lista:
            puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/api/puntos')
def api_puntos(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/actualizar_punto', methods=['POST'])
def up_p(): d = request.json; puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']}); return jsonify({"s": "ok"})
@app.route('/api/usuarios')
def api_users(): u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/actualizar_usuario', methods=['POST'])
def up_u():
    d = request.json
    if d['id']:
        usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}})
    else:
        usuarios_col.insert_one({"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']})
    return jsonify({"s": "ok"})
@app.route('/descargar')
def desc():
    cursor = visitas_col.find({"estado": "Aprobado"}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Propuesto', 'Distancia', 'Nota'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('distancia'), r.get('Nota')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})
@app.route('/get_img/<id>')
def get_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
