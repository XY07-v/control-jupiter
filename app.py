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
auditoria_col = db['auditoria_bmb']

# --- FUNCIÓN DISTANCIA ---
def calcular_distancia(p1, p2):
    if not p1 or not p2: return 0
    try:
        lat1, lon1 = map(float, p1.split(','))
        lat2, lon2 = map(float, p2.split(','))
        rad = math.pi / 180
        dlat, dlon = (lat2-lat1)*rad, (lon2-lon1)*rad
        a = math.sin(dlat/2)**2 + math.cos(lat1*rad)*math.cos(lat2*rad)*math.sin(dlon/2)**2
        return 2 * 6371000 * math.asin(math.sqrt(a))
    except: return 0

# --- CSS BI COMPLETO ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); z-index: 2000; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; box-shadow: 0 0 50px rgba(0,0,0,0.9); }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; font-size: 14px; margin-top: 10px; text-align: center; display: block; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 13px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">NESTLÉ BI POC</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Gestión de Puntos</div>
            <a href="/validacion" class="nav-link" style="color:#FFD97D;">Validación Visitas POC</a>
            <a href="/descargar" class="nav-link">Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva CSV</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:40px;">Cerrar Sesión</a>
        </div>
        <div style="padding:20px;">
            <button onclick="toggleMenu()" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰ Menú</button>
            <h2 style="margin-top:20px;">Visitas Realizadas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">REGRESAR</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Gestión de Puntos</h3><div id="p_table_cont" style="overflow-x:auto;"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_usuarios" class="modal-box"><h3>👥 Usuarios</h3><div id="u_table_cont"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva</h3><input type="file" id="fcsv"><button onclick="subirCsv()" class="btn btn-primary">Procesar</button><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = 'block'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            function openModal(id) {{ closeAll(); document.getElementById(id).style.display='block'; document.getElementById('overlay').style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            async function cargarPuntos() {{
                const res = await fetch('/api/puntos'); const puntos = await res.json();
                if(puntos.length===0) return;
                const cols = Object.keys(puntos[0]).filter(k=>k!=='_id');
                let h = '<table><tr>' + cols.map(c=>`<th>${{c}}</th>`).join('') + '</tr>';
                puntos.forEach(p => {{ h += '<tr>' + cols.map(c=>`<td>${{p[c]||''}}</td>`).join('') + '</tr>'; }});
                document.getElementById('p_table_cont').innerHTML = h + '</table>';
            }}
            async function cargarUsuarios() {{
                const res = await fetch('/api/usuarios'); const users = await res.json();
                let h = '<table><tr><th>Nombre</th><th>Rol</th></tr>';
                users.forEach(u => {{ h += `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td></tr>`; }});
                document.getElementById('u_table_cont').innerHTML = h + '</table>';
            }}
            async function subirCsv() {{
                const fd = new FormData(); fd.append('file_csv', document.getElementById('fcsv').files[0]);
                const res = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                if(res.ok) {{ alert("Carga exitosa"); location.reload(); }}
            }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>BMB: ${{bmb}}<br>Asesor: ${{doc}}<br>Motivo: ${{mot}}<br>Nota: ${{nota}}</p><button id="lb" class="btn btn-primary" onclick="loadE('${{id}}','${{gps}}')">Ver Evidencia</button><div id="map" style="height:200px; display:none; margin-top:10px;"></div><img id="i1" style="width:100%; display:none; margin-top:10px;"><img id="i2" style="width:100%; display:none; margin-top:10px;">`;
                openModal('modal_detalle');
            }}
            async function loadE(id, gps) {{
                const res = await fetch('/get_img/'+id); const d = await res.json();
                if(d.f1) {{ document.getElementById('i1').src=d.f1; document.getElementById('i1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('i2').src=d.f2; document.getElementById('i2').style.display='block'; }}
                if(gps) {{ document.getElementById('map').style.display='block'; const map = L.map('map').setView(gps.split(','), 16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map); L.marker(gps.split(',')).addTo(map); }}
                document.getElementById('lb').style.display='none';
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg = request.args.get('msg')
    if request.method == 'POST':
        pv, nbmb, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        punto = puntos_col.find_one({"Punto de Venta": pv})
        # Auditoría y actualización
        if punto and punto.get('BMB') != nbmb:
            auditoria_col.insert_one({"pv": pv, "usr": session['user_name'], "ant": punto.get('BMB'), "new": nbmb, "f": datetime.now()})
            puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"BMB": nbmb}})
        
        dist = calcular_distancia(gps, punto.get('Ruta')) if punto else 0
        puntos_col.update_one({"Punto de Venta": pv}, {"$set": {"Ruta": gps}})
        est = "Pendiente" if dist > 100 else "Aprobado"
        
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        visitas_col.insert_one({"pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'), "bmb": nbmb, "motivo": request.form.get('motivo'), "ubicacion": gps, "estado": est, "distancia": round(dist,1), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))})
        return redirect(f'/formulario?msg={"OK" if est=="Aprobado" else "FUERA DE RANGO: Validación"}')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            {f'<p style="text-align:center; color:#B7E4C7;">{msg}</p>' if msg else ''}
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{opts}</datalist>
                <label>BMB (Editable)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Visita a POC</option><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Dificultades Trade</option></select>
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g"><button class="btn btn-primary">REGISTRAR</button>
                <a href="/" class="btn btn-gray">VOLVER</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ 
                const v = document.getElementById('pv_i').value;
                const o = Array.from(document.getElementById('p').options).find(opt => opt.value === v);
                if(o) document.getElementById('bmb_i').value = o.dataset.bmb;
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion')
def validacion():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f"<tr><td>{r['pv']}</td><td>{r['n_documento']}</td><td>{r['distancia']}m</td><td><a href='/api/aprobar/{r['_id']}' style='color:#B7E4C7;'>Aprobar</a></td></tr>" for r in pends])
    return render_template_string(f"<html><head>{CSS_BI}</head><body><div style='padding:20px;'><h2>Validación de Visitas</h2><table><tr><th>Punto</th><th>Asesor</th><th>Distancia</th><th>Acción</th></tr>{rows}</table><br><a href='/' class='btn btn-gray'>Volver al Menú</a></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>ACCESO BI NESTLÉ</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content), delimiter=';' if ';' in content else ',')
        lista = [r for r in reader]
        if lista: puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0, "_id":0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Ubicacion'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('ubicacion')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/api/puntos')
def api_puntos(): p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/usuarios')
def api_u(): u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/aprobar/<id>')
def api_ap(id): visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}}); return redirect('/validacion')
@app.route('/get_img/<id>')
def get_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
