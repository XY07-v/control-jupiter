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

# --- EXPORTE MODIFICADO (ÚNICO CAMBIO REALIZADO) ---
@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0})
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow([
        'PUNTO DE VENTA', 'ASESOR', 'FECHA', 
        'BMB ANTERIOR', 'BMB ACTUALIZADO', 
        'GPS MAESTRA', 'GPS VISITA', 'DESFACE (METROS)', 
        'ESTADO VALIDACION', 'OBSERVACION DE AUDITORIA'
    ])
    for r in cursor:
        b_ant = r.get('bmb', 'N/A')
        b_act = r.get('bmb_propuesto', 'N/A')
        dist = r.get('distancia', 0)
        obs = []
        if b_ant != b_act: obs.append(f"Cambio BMB ({b_ant}->{b_act})")
        if dist > 100: obs.append(f"Desface GPS {dist}m")
        w.writerow([
            r.get('pv'), r.get('n_documento'), r.get('fecha'),
            b_ant, b_act, r.get('gps_anterior', 'S/D'),
            r.get('ubicacion'), f"{dist} m", r.get('estado'),
            " | ".join(obs) if obs else "Sin novedades"
        ])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_Auditoria.csv"})

# --- RESTABLECIMIENTO DE LÓGICA ORIGINAL ---

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
        .menu { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .btn { padding: 10px 15px; border-radius: 8px; border: none; cursor: pointer; background: #007AFF; color: white; text-decoration: none; font-size: 14px; }
        .card { background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:100; }
        .modal-content { background:white; margin:10% auto; padding:20px; width:90%; max-width:600px; border-radius:15px; }
    </style></head>
    <body>
        <h2>Panel Administrador</h2>
        <div class="menu">
            <a href="/formulario" class="btn">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn" style="background:#FF9500;">Validaciones</a>
            <button class="btn" onclick="openM('m_puntos')">Puntos</button>
            <button class="btn" onclick="openM('m_users')">Usuarios</button>
            <button class="btn" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn" style="background:#34C759;">Exportar Reporte</a>
            <a href="/logout" class="btn" style="background:#FF3B30;">Salir</a>
        </div>
        <div id="lista_aprobados"></div>

        <div id="m_puntos" class="modal"><div class="modal-content"><button onclick="closeM()">Cerrar</button><div id="cont_p"></div></div></div>
        <div id="m_users" class="modal"><div class="modal-content"><button onclick="closeM()">Cerrar</button><div id="cont_u"></div></div></div>
        <div id="m_csv" class="modal"><div class="modal-content"><h3>Carga Masiva</h3><input type="file" id="f_csv"><button onclick="subirCSV()">Cargar</button><button onclick="closeM()">Cerrar</button></div></div>

        <script>
            function openM(id){ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }
            function closeM(){ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }
            async function cargaP(){
                const r = await fetch('/api/puntos'); const d = await r.json();
                let h = '<h3>Puntos de Venta</h3><table>';
                d.forEach(p => h += `<tr><td>${p['Punto de Venta']}</td><td><button onclick='editP(${JSON.stringify(p)})'>Editar</button></td></tr>`);
                document.getElementById('cont_p').innerHTML = h + '</table>';
            }
            function editP(p){
                let f = '<h3>Editar</h3>';
                Object.keys(p).forEach(k => { if(k!='_id') f += `<label>${k}</label><input type="text" id="ed_${k}" value="${p[k]}"><br>`; });
                f += `<button onclick="saveP('${p._id}')">Guardar</button>`;
                document.getElementById('cont_p').innerHTML = f;
            }
            async function saveP(id){
                let datos = {}; document.querySelectorAll('[id^="ed_"]').forEach(i => datos[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id, datos:datos})});
                cargaP();
            }
            async function cargaU(){
                const r = await fetch('/api/usuarios'); const d = await r.json();
                let h = '<h3>Usuarios</h3><button onclick="editU()">+ Nuevo</button><table>';
                d.forEach(u => h += `<tr><td>${u.nombre_completo}</td><td><button onclick='editU(${JSON.stringify(u)})'>Editar</button></td></tr>`);
                document.getElementById('cont_u').innerHTML = h + '</table>';
            }
            function editU(u={}){
                let f = `<h3>${u._id?'Editar':'Nuevo'}</h3>
                <input type="text" id="un" placeholder="Nombre" value="${u.nombre_completo||''}">
                <input type="text" id="uu" placeholder="Usuario" value="${u.usuario||''}">
                <input type="text" id="up" placeholder="Password" value="${u.password||''}">
                <select id="ur"><option value="asesor">Asesor</option><option value="admin">Admin</option></select>
                <button onclick="saveU('${u._id||''}')">Guardar</button>`;
                document.getElementById('cont_u').innerHTML = f;
            }
            async function saveU(id){
                const d = {id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value};
                await fetch('/api/actualizar_usuario', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
                cargaU();
            }
            async function subirCSV(){
                const f = document.getElementById('f_csv').files[0]; const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {method:'POST', body:fd});
                const res = await r.json(); alert("Cargados: " + res.count); closeM();
            }
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
    return render_template_string(f"""
    <html><body>
        <div style="max-width:400px; margin:auto; padding:20px; font-family:sans-serif;">
            <h2>Hola, {session['user_name']}</h2>
            <form method="POST" enctype="multipart/form-data">
                <input list="pts" name="pv" placeholder="Punto de Venta" required onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;">
                <datalist id="pts">{opts}</datalist>
                <input type="text" name="bmb" id="bmb_i" placeholder="BMB">
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                <input type="file" name="f1" capture="camera" required>
                <input type="file" name="f2" capture="camera" required>
                <input type="hidden" name="ubicacion" id="gps">
                <button type="submit" style="width:100%; padding:10px; background:#007AFF; color:white; border:none; margin-top:10px;">Enviar</button>
            </form>
            <br><a href="/logout">Cerrar Sesión</a>
        </div>
        <script>navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)</script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = ""
    for r in pends:
        rows += f"<div style='border:1px solid #ccc; padding:10px; margin-bottom:10px;'><h3>{r['pv']}</h3><p>BMB: {r.get('bmb')} -> {r.get('bmb_propuesto')} | Distancia: {r.get('distancia')}m</p><button onclick=\"vF('{r['_id']}','aprobar')\">Aprobar</button><button onclick=\"vF('{r['_id']}','rechazar')\">Rechazar</button></div>"
    return render_template_string(f"<html><body><h2>Validaciones</h2>{rows}<script>async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else: visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/api/puntos')
def api_p(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/usuarios')
def api_u(): u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/actualizar_punto', methods=['POST'])
def api_up_p(): d = request.json; puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']}); return jsonify({"s": "ok"})
@app.route('/api/actualizar_usuario', methods=['POST'])
def api_up_u():
    d = request.json
    if d['id']: usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}})
    else: usuarios_col.insert_one({"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']})
    return jsonify({"s": "ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [r for r in reader]
        if lista: puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string("<html><body><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p'><button>Entrar</button></form></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
