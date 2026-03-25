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

CSS_SISTEMA = """
<style>
    :root { --ios-blue: #007AFF; --sidebar-w: 260px; }
    body { font-family: -apple-system, sans-serif; background: #F2F2F7; margin: 0; display: flex; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; display: flex; flex-direction: column; z-index: 1000; box-sizing: border-box; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 30px; width: calc(100% - var(--sidebar-w)); }
    .btn { width: 100%; height: 48px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; text-decoration: none; font-size: 14px; box-sizing: border-box; transition: 0.2s; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.4); z-index:2000; backdrop-filter: blur(10px); }
    .modal-content { background:white; margin:2% auto; padding:25px; width:90%; max-width:850px; border-radius:25px; max-height: 85vh; overflow-y: auto; }
    .search-box { width: 100%; padding: 14px; margin-bottom: 15px; border: 1px solid #d1d1d6; border-radius: 12px; font-size: 16px; outline: none; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    input[type="text"], input[type="password"], input[type="date"], select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    @media (max-width: 768px) { .sidebar { display: none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_SISTEMA}</head>
    <body>
        <div class="sidebar">
            <h2 style="color:var(--ios-blue)">Nestlé BI</h2>
            <p>Admin: <b>{session['user_name']}</b></p>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500">Validaciones</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Reporte</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Salir</a></div>
        </div>
        <div class="main-content"><h3>Panel Administrativo</h3><p>Bienvenido. Seleccione una opción.</p></div>

        <div id="m_puntos" class="modal"><div class="modal-content">
            <h3>Puntos de Venta <button onclick="closeM()" style="float:right">×</button></h3>
            <input type="text" class="search-box" id="sP" placeholder="Buscar punto..." onkeyup="filterT('sP', 'tP')">
            <div id="cont_p"></div>
        </div></div>

        <div id="m_users" class="modal"><div class="modal-content">
            <h3>Usuarios <button onclick="closeM()" style="float:right">×</button></h3>
            <input type="text" class="search-box" id="sU" placeholder="Buscar usuario..." onkeyup="filterT('sU', 'tU')">
            <button class="btn btn-blue" onclick="editU()">+ Nuevo Usuario</button>
            <div id="cont_u"></div>
        </div></div>

        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Carga Masiva <button onclick="closeM()" style="float:right">×</button></h3>
            <input type="file" id="f_csv"><br><br>
            <button class="btn btn-blue" onclick="subirCSV()">Procesar CSV</button>
        </div></div>

        <script>
            function openM(id){{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM(){{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            function filterT(inp, tab) {{
                let v = document.getElementById(inp).value.toUpperCase();
                let rows = document.getElementById(tab).getElementsByTagName("tr");
                for (let i = 1; i < rows.length; i++) {{ rows[i].style.display = rows[i].innerText.toUpperCase().indexOf(v) > -1 ? "" : "none"; }}
            }}
            async function cargaP(){{
                const r = await fetch('/api/puntos'); const d = await r.json();
                let h = '<table id="tP"><tr><th>Punto</th><th>Acción</th></tr>';
                d.forEach(p => h += `<tr><td>${{p['Punto de Venta']}}</td><td><button onclick='editP(${{JSON.stringify(p)}})'>Editar</button></td></tr>`);
                document.getElementById('cont_p').innerHTML = h + '</table>';
            }}
            async function cargaU(){{
                const r = await fetch('/api/usuarios'); const d = await r.json();
                let h = '<table id="tU"><tr><th>Nombre</th><th>Acción</th></tr>';
                d.forEach(u => h += `<tr><td>${{u.nombre_completo}}</td><td><button onclick='editU(${{JSON.stringify(u)}})'>Editar</button></td></tr>`);
                document.getElementById('cont_u').innerHTML = h + '</table>';
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
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, "gps_anterior": gps_maestra, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    btn_regresar = '<a href="/" class="btn btn-light">Regresar al Menú</a>' if session.get('role') == 'admin' else ''
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_SISTEMA}</head>
    <body style="display:block; background:white; padding:20px;"><div style="max-width:400px; margin:auto;">
        <h2 style="text-align:center;">Formulario BI</h2>
        <form method="POST" enctype="multipart/form-data">
            <input list="pts" name="pv" required onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;">
            <datalist id="pts">{opts}</datalist>
            <input type="text" name="bmb" id="bmb_i" placeholder="BMB Actual">
            <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
            <input type="file" name="f1" capture="camera" required>
            <input type="file" name="f2" capture="camera" required>
            <input type="hidden" name="ubicacion" id="gps">
            <button type="submit" class="btn btn-blue" style="margin-top:15px;">Enviar</button>
            {btn_regresar}
            <a href="/logout" class="btn btn-red">Salir</a>
        </form>
    </div>
    <script>navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)</script>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga_csv():
    f = request.files.get('file_csv')
    if f:
        stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        data = [r for r in reader]
        if data:
            puntos_col.delete_many({})
            puntos_col.insert_many(data)
            return jsonify({"count": len(data)})
    return jsonify({"count": 0}), 400

@app.route('/api/puntos')
def api_p(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/usuarios')
def api_u(): u=list(usuarios_col.find()); [x.update({"_id":str(x["_id"])}) for x in u]; return jsonify(u)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_SISTEMA}</head><body style='justify-content:center; align-items:center;'><div style='width:300px; background:white; padding:25px; border-radius:20px; box-shadow:0 10px 20px rgba(0,0,0,0.1);'><h2 style='text-align:center;'>Nestlé BI</h2><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
