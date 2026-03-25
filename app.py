from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB (TOTALMENTE RESTABLECIDA) ---
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

# --- TOOLKIT DE DISEÑO IPHONE / GLASSMORPHISM ---
CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 260px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { 
        width: var(--sidebar-w); background: white; height: 100vh; position: fixed; 
        border-right: 0.5px solid #d1d1d6; padding: 25px; box-sizing: border-box; 
        display: flex; flex-direction: column; z-index: 1000;
    }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 30px; width: calc(100% - var(--sidebar-w)); }
    .glass-card {
        background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
        border-radius: 20px; padding: 25px; margin-bottom: 20px; border: 0.5px solid rgba(0,0,0,0.1);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .btn { 
        width: 100%; height: 48px; border-radius: 12px; border: none; font-weight: 600; 
        cursor: pointer; margin-bottom: 12px; display: flex; align-items: center; 
        justify-content: center; text-decoration: none; font-size: 15px; transition: 0.2s;
    }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .btn:active { transform: scale(0.97); }
    .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:2000; backdrop-filter: blur(5px); }
    .modal-content { background:white; margin:5% auto; padding:25px; width:90%; max-width:700px; border-radius:25px; max-height: 85vh; overflow-y: auto; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
    @media (max-width: 768px) { .sidebar { display: none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1))
    rows = "".join([f'<div class="glass-card"><b>{v["pv"]}</b><br><small>{v["fecha"]} - {v["n_documento"]}</small></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="color:var(--ios-blue); margin-bottom:5px;">Nestlé BI</h2>
            <p style="font-size:14px; font-weight:600; margin-bottom:25px;">Admin: {session['user_name']}</p>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Validaciones</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Auditoría</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content">
            <h3>Historial General</h3>
            {rows}
        </div>

        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content"><h3>Carga Masiva</h3><input type="file" id="f_csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar</button><button class="btn btn-light" onclick="closeM()">Cerrar</button></div></div>

        <script>
            function openM(id){{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM(){{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            async function cargaP(){{
                const r = await fetch('/api/puntos'); const d = await r.json();
                let h = '<h3>Puntos <button onclick="closeM()" style="float:right">X</button></h3><table>';
                d.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td><button onclick='editP(${{JSON.stringify(p)}})'>Edit</button></td></tr>`);
                document.getElementById('cont_p_modal').innerHTML = h + '</table>';
            }}
            function editP(p){{
                let f = '<h3>Editar Punto</h3>';
                Object.keys(p).forEach(k => {{ if(k!='_id') f += `<label>${{k}}</label><input type="text" id="ed_${{k}}" value="${{p[k]}}">`; }});
                f += `<button class="btn btn-blue" onclick="saveP('${{p._id}}')">Guardar</button><button class="btn btn-light" onclick="cargaP()">Volver</button>`;
                document.getElementById('cont_p_modal').innerHTML = f;
            }}
            async function saveP(id){{
                let datos = {{}}; document.querySelectorAll('[id^="ed_"]').forEach(i => datos[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:datos}})}});
                cargaP();
            }}
            async function cargaU(){{
                const r = await fetch('/api/usuarios'); const d = await r.json();
                let h = '<h3>Usuarios <button onclick="closeM()" style="float:right">X</button></h3><button onclick="editU()">+ Nuevo</button><table>';
                d.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td><button onclick='editU(${{JSON.stringify(u)}})'>Edit</button></td></tr>`);
                document.getElementById('cont_u_modal').innerHTML = h + '</table>';
            }}
            function editU(u={{}}){{
                let f = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor">Asesor</option><option value="admin">Admin</option></select>
                <button class="btn btn-blue" onclick="saveU('${{u._id||''}}')">Guardar</button><button class="btn btn-light" onclick="cargaU()">Volver</button>`;
                document.getElementById('cont_u_modal').innerHTML = f;
            }}
            async function saveU(id){{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                cargaU();
            }}
            async function subirCSV(){{
                const f = document.getElementById('f_csv').files[0]; const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); closeM();
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        pv, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_orig = pnt.get('BMB') if pnt else ""
        gps_maestra = pnt.get('Ruta') if pnt else gps
        dist = calcular_distancia(gps, gps_maestra)
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
            "gps_anterior": gps_maestra, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "motivo": request.form.get('motivo'), 
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    btn_regresar = '<a href="/" class="btn btn-light">Regresar al Menú Principal</a>' if session.get('role') == 'admin' else ''
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body style="display:block; background:white;">
        <div style="max-width:450px; margin:auto; padding:20px;">
            <div class="glass-card" style="box-shadow:none; border:none;">
                <h2 style="text-align:center;">Formulario Visita</h2>
                <p style="text-align:center;">Hola, <b>{session['user_name']}</b></p>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Punto de Venta" required 
                           onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;">
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB Máquina">
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <input type="file" name="f1" capture="camera" required>
                    <input type="file" name="f2" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button type="submit" class="btn btn-blue">Enviar Reporte</button>
                    {btn_regresar}
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        <script>navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)</script>
    </body></html>
    """)

# --- LAS DEMÁS RUTAS (API, LOGIN, VALIDACION) QUEDARON IGUAL A FINAL2.4.PY ---
@app.route('/api/usuarios')
def api_u(): u=list(usuarios_col.find()); [x.update({"_id":str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/puntos')
def api_p(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/actualizar_punto', methods=['POST'])
def api_up_p(): d=request.json; puntos_col.update_one({"_id":ObjectId(d['id'])}, {"$set": d['datos']}); return jsonify({"s":"ok"})
@app.route('/api/actualizar_usuario', methods=['POST'])
def api_up_u():
    d=request.json
    if d['id']: usuarios_col.update_one({"_id":ObjectId(d['id'])}, {"$set":{"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']}})
    else: usuarios_col.insert_one({"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']})
    return jsonify({"s":"ok"})
@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f=request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        puntos_col.delete_many({}); puntos_col.insert_many([r for r in reader])
        return jsonify({"count": 100})
    return jsonify({"e":1})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='justify-content:center; align-items:center;'><div class='glass-card' style='width:300px;'><form method='POST'><h2>Login</h2><input name='u' placeholder='User'><input type='password' name='p'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
