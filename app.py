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

# --- DISEÑO iOS 26 LIQUID GLASS (CAPA ESTÉTICA) ---
CSS_IOS26 = """
<style>
    :root { 
        --glass: rgba(255, 255, 255, 0.08); 
        --glass-border: rgba(255, 255, 255, 0.15);
        --accent: #4ade80; 
        --bg-liquid: linear-gradient(135deg, #071a13 0%, #0d2a1f 50%, #05120d 100%);
    }
    body { 
        font-family: -apple-system, "SF Pro Display", sans-serif; 
        background: var(--bg-liquid); background-attachment: fixed; margin: 0; color: white; min-height: 100vh;
    }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(20px); z-index: 2000; }
    .sidebar { 
        position: fixed; left: -300px; top: 15px; width: 280px; height: calc(100% - 30px); 
        background: var(--glass); backdrop-filter: blur(35px); border-radius: 35px;
        border: 1px solid var(--glass-border); transition: 0.5s cubic-bezier(0.16, 1, 0.3, 1); z-index: 2100; padding: 30px; box-sizing: border-box;
    }
    .sidebar.active { left: 15px; }
    .nav-link { 
        display: block; color: #fff; text-decoration: none; padding: 18px; border-radius: 22px; 
        margin-bottom: 12px; background: rgba(255,255,255,0.03); transition: 0.3s;
    }
    .nav-link:hover { background: var(--accent); color: #000; transform: translateY(-2px); }
    .card { 
        background: var(--glass); backdrop-filter: blur(30px); border-radius: 40px; 
        padding: 30px; border: 1px solid var(--glass-border); box-shadow: 0 25px 60px rgba(0,0,0,0.4);
    }
    .btn { width: 100%; padding: 16px; border-radius: 22px; font-weight: 600; cursor: pointer; border: none; transition: 0.3s; font-size: 15px; margin-top: 15px; text-align: center; display: block; text-decoration: none; }
    .btn-primary { background: white; color: black; }
    .btn-gray { background: rgba(255,255,255,0.1); color: white; }
    input, select, textarea { 
        width: 100%; padding: 15px; margin: 10px 0; border: 1px solid var(--glass-border); 
        border-radius: 20px; background: rgba(0,0,0,0.2); color: white; outline: none; box-sizing: border-box;
    }
    .modal-box { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 95%; max-width: 800px; z-index: 3000; background: rgba(20,20,20,0.7);
        backdrop-filter: blur(50px); border-radius: 45px; padding: 40px; border: 1px solid var(--glass-border);
        max-height: 90vh; overflow-y: auto;
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 15px; text-align: left; border-bottom: 1px solid var(--glass-border); }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="card" style="margin-bottom:15px; padding:20px; cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><b>{r.get("pv")}</b><br><small style="opacity:0.6;">{r.get("fecha")} · {r.get("n_documento")}</small></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_IOS26}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h2 style="text-align:center;">Nestlé BI</h2>
            <a href="/formulario" class="nav-link">Nueva Visita</a>
            <a href="/validacion_admin" class="nav-link" style="color:var(--accent);">Revisión Pendientes 📋</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Base de Puntos</div>
            <a href="/descargar" class="nav-link">Descargar Reporte</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#ff6b6b; margin-top:30px;">Cerrar Sesión</a>
        </div>
        <div style="padding:25px; max-width:900px; margin:auto;">
            <button onclick="toggleMenu()" style="background:var(--glass); border:none; color:white; padding:15px 25px; border-radius:20px; cursor:pointer;">☰ Menú</button>
            <h2 style="margin-top:35px;">Historial de Visitas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">Volver</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Gestión de Puntos</h3><input type="text" id="f_pv" placeholder="Filtrar punto..." onkeyup="filtrarPuntos()"><div style="overflow-x:auto;"><table><thead id="h_p"></thead><tbody id="puntos_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_edit_punto" class="modal-box" style="z-index:4000; max-width:450px;"></div>
        <div id="modal_usuarios" class="modal-box"><h3>👥 Usuarios</h3><button class="btn btn-primary" onclick="abrirPopUser()">+ Nuevo Usuario</button><div style="overflow-x:auto;"><table><thead><tr><th>Nombre</th><th>Usuario</th><th>Acción</th></tr></thead><tbody id="user_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_edit_user" class="modal-box" style="z-index:4000; max-width:400px;"></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva CSV</h3><input type="file" id="fileCsv" accept=".csv"><button onclick="subirCsv()" class="btn btn-primary">Cargar Datos</button></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}

            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); window.allP = await res.json(); renderP(window.allP); }}
            function renderP(l) {{
                if(!l.length) return;
                const cols = Object.keys(l[0]).filter(k => k !== '_id');
                document.getElementById('h_p').innerHTML = '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '<th>Acción</th></tr>';
                document.getElementById('puntos_table').innerHTML = l.map(p => `<tr>${{cols.map(c => `<td>${{p[c]||''}}</td>`).join('')}}<td><button onclick='abrirPopPunto(${{JSON.stringify(p)}})' style='color:var(--accent); background:none; border:none; cursor:pointer;'>EDITAR</button></td></tr>`).join('');
            }}
            function filtrarPuntos() {{ const f = document.getElementById('f_pv').value.toLowerCase(); renderP(window.allP.filter(p => Object.values(p).some(v => String(v).toLowerCase().includes(f)))); }}
            
            function abrirPopPunto(p) {{
                let h = `<h3>Editar Punto</h3><input type="hidden" id="ep_id" value="${{p._id}}">`;
                Object.keys(p).filter(k=>k!='_id').forEach(k => {{ h += `<label style="font-size:11px; opacity:0.6;">${{k}}</label><input type="text" class="e-f" data-k="${{k}}" value="${{p[k]||''}}">`; }});
                h += `<button class="btn btn-primary" onclick="saveP()">Guardar Cambios</button><button class="btn btn-gray" onclick="document.getElementById('modal_edit_punto').style.display='none'">Cancelar</button>`;
                document.getElementById('modal_edit_punto').innerHTML = h; document.getElementById('modal_edit_punto').style.display='block';
            }}
            async function saveP() {{
                const d = {{}}; document.querySelectorAll('.e-f').forEach(i => d[i.dataset.k] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:document.getElementById('ep_id').value, datos:d}})}});
                cargarPuntos(); document.getElementById('modal_edit_punto').style.display='none';
            }}

            async function subirCsv() {{
                const f = document.getElementById('fileCsv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file', f);
                const r = await fetch('/api/subir_csv', {{method:'POST', body:fd}}); const res = await r.json();
                alert(res.msg); closeAll();
            }}

            async function cargarUsuarios() {{ const res = await fetch('/api/usuarios'); const u = await res.json(); document.getElementById('user_table').innerHTML = '<table>' + u.map(x => `<tr><td>${{x.nombre_completo}}</td><td><button onclick='abrirPopUser(${{JSON.stringify(x)}})'>EDITAR</button></td></tr>`).join('') + '</table>'; }}
            function abrirPopUser(u={{}}) {{
                document.getElementById('modal_edit_user').innerHTML = `<h3>Usuario</h3><input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}"><input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}"><input type="text" id="up" placeholder="Password" value="${{u.password||''}}"><select id="ur"><option value="asesor" ${{u.rol==='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol==='admin'?'selected':''}}>Admin</option></select><button class="btn btn-primary" onclick="saveU('${{u._id||''}}')">Guardar</button>`;
                document.getElementById('modal_edit_user').style.display='block';
            }}
            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                closeAll(); cargarUsuarios();
            }}
            
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>${{doc}} · ${{f}}</p><div id="map" style="height:250px; border-radius:25px; margin-bottom:20px;"></div><div id="imgs"></div>`;
                openModal('modal_detalle');
                setTimeout(async ()=>{{ 
                    const r = await fetch('/get_img/'+id); const d = await r.json();
                    document.getElementById('imgs').innerHTML = `<img src="${{d.f1}}" style="width:100%; border-radius:20px; margin-bottom:10px;"><img src="${{d.f2}}" style="width:100%; border-radius:20px;">`;
                    const c=gps.split(','); const m=L.map('map').setView(c,16); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
                }},300);
            }}
        </script>
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
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "bmb_pendiente": bmb_in != bmb_orig,
            "ubicacion": gps, "gps_anterior": pnt.get('Ruta') if pnt else gps,
            "distancia": round(dist, 1), "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2')), "Nota": request.form.get('nota'),
            "motivo": request.form.get('motivo')
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    btn_admin = '<a href="/" class="btn btn-gray">← Panel Administrador</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_IOS26}</head>
    <body onload="getGPS()" style="display:flex; align-items:center; justify-content:center; padding:20px;">
        <div class="card" style="width:100%; max-width:480px;">
            <h2 style="text-align:center;">Nueva Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <input list="p" name="pv" id="pv_i" placeholder="Seleccionar Punto de Venta" onchange="upBMB()" required>
                <datalist id="p">{opts}</datalist>
                <input type="text" name="bmb" id="bmb_i" placeholder="BMB">
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                <textarea name="nota" placeholder="Observaciones o novedades..."></textarea>
                <label style="font-size:12px; opacity:0.6;">Foto Máquina / BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label style="font-size:12px; opacity:0.6;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">Guardar Reporte</button>
                {btn_admin}
                <a href="/logout" style="display:block; text-align:center; margin-top:25px; color:#ff6b6b; text-decoration:none;">Cerrar Sesión</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ const v=document.getElementById('pv_i').value; const o=Array.from(document.getElementById('p').options).find(x=>x.value===v); if(o) document.getElementById('bmb_i').value=o.dataset.bmb; }}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = "".join([f"""
        <div class="card" style="margin-bottom:25px; border: 2px solid var(--accent);">
            <h3>{r['pv']}</h3>
            <p style="font-size:13px;">Asesor: {r['n_documento']} | Distancia: {r['distancia']}m</p>
            <p style="font-size:13px; color:var(--accent);">BMB: {r['bmb']} → {r['bmb_propuesto']}</p>
            <div style="display:flex; gap:10px; margin:15px 0;">
                <img src="{r['f_bmb']}" style="width:50%; border-radius:15px;">
                <img src="{r['f_fachada']}" style="width:50%; border-radius:15px;">
            </div>
            <div id="map_{r['_id']}" style="height:300px; border-radius:25px; margin-bottom:15px;"></div>
            <div style="display:flex; gap:10px;">
                <button class="btn btn-primary" onclick="vFinal('{r['_id']}', 'aprobar')">APROBAR</button>
                <button class="btn btn-gray" onclick="vFinal('{r['_id']}', 'rechazar')">RECHAZAR</button>
            </div>
            <script>
                setTimeout(()=>{{
                    const m = L.map('map_{r['_id']}').setView([{r['ubicacion']}], 15);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m);
                    L.marker([{r['gps_anterior']}]).addTo(m).bindPopup('Ubicación Base');
                    L.circle([{r['gps_anterior']}], {{radius: 100, color: 'red', fill: false}}).addTo(m);
                    L.marker([{r['ubicacion']}]).addTo(m).bindPopup('Ubicación Actual').openPopup();
                }}, 500);
            </script>
        </div>
    """ for r in pends])
    return render_template_string(f"<html><head><link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' />{CSS_IOS26}</head><body><div style='padding:25px;'><script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><h2>Visitas por Validar</h2>{rows or '<p>No hay alertas pendientes.</p>'}<br><a href='/' class='btn btn-gray'>Regresar</a></div><script>async function vFinal(id, op){{ await fetch('/api/v_final/'+id+'/'+op); location.reload(); }}</script></body></html>")

# --- APIS RESTAURADAS ---
@app.route('/api/v_final/<id>/<op>')
def api_v_final(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar':
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}})
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/api/puntos')
def api_puntos(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/actualizar_punto', methods=['POST'])
def up_p(): d=request.json; puntos_col.update_one({"_id":ObjectId(d['id'])}, {"$set":d['datos']}); return jsonify({"s":"ok"})
@app.route('/api/usuarios')
def api_u(): u=list(usuarios_col.find()); [x.update({"_id":str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/api/actualizar_usuario', methods=['POST'])
def up_u():
    d=request.json
    if d['id']: usuarios_col.update_one({"_id":ObjectId(d['id'])}, {"$set":{"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']}})
    else: usuarios_col.insert_one({"nombre_completo":d['nom'], "usuario":d['usr'], "password":d['pas'], "rol":d['rol']})
    return jsonify({"s":"ok"})

@app.route('/api/subir_csv', methods=['POST'])
def api_subir_csv():
    f = request.files['file']
    s = io.StringIO(f.stream.read().decode("UTF8"), newline=None)
    r = csv.DictReader(s)
    c = 0
    for row in r:
        puntos_col.update_one({"Punto de Venta": row['Punto de Venta']}, {"$set": row}, upsert=True)
        c += 1
    return jsonify({"msg": f"Se cargaron {c} puntos correctamente."})

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Nuevo', 'Distancia', 'GPS', 'Nota', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('distancia'), r.get('ubicacion'), r.get('Nota'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/get_img/<id>')
def get_img(id): d=visitas_col.find_one({"_id":ObjectId(id)}); return jsonify({"f1":d.get('f_bmb'),"f2":d.get('f_fachada')})
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_IOS26}</head><body style='display:flex; align-items:center; justify-content:center;'><div class='card' style='width:320px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
