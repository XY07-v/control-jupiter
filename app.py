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

# --- DISEÑO iOS 26 LIGHT GLASS ---
CSS_IOS_LIGHT = """
<style>
    :root { 
        --glass: rgba(255, 255, 255, 0.7); 
        --glass-border: rgba(255, 255, 255, 0.4);
        --accent: #007AFF; 
        --bg-liquid: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 50%, #dbeafe 100%);
        --text: #1e293b;
    }
    body { 
        font-family: -apple-system, "SF Pro Display", sans-serif; 
        background: var(--bg-liquid); background-attachment: fixed; margin: 0; color: var(--text); min-height: 100vh;
    }
    .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.1); backdrop-filter: blur(15px); z-index: 2000; display: none; }
    .sidebar { 
        position: fixed; left: -300px; top: 15px; width: 280px; height: calc(100% - 30px); 
        background: var(--glass); backdrop-filter: blur(30px); border-radius: 35px;
        border: 1px solid var(--glass-border); transition: 0.5s cubic-bezier(0.16, 1, 0.3, 1); z-index: 2100; padding: 25px;
    }
    .sidebar.active { left: 15px; }
    .nav-link { 
        display: block; color: var(--text); text-decoration: none; padding: 16px; border-radius: 20px; 
        margin-bottom: 8px; background: rgba(255,255,255,0.4); transition: 0.3s; font-weight: 500;
    }
    .nav-link:hover { background: var(--accent); color: white; transform: scale(1.02); }
    .card { 
        background: var(--glass); backdrop-filter: blur(30px); border-radius: 40px; 
        padding: 25px; border: 1px solid var(--glass-border); box-shadow: 0 20px 40px rgba(0,0,0,0.05);
        width: 90%; max-width: 900px; margin: 20px auto; box-sizing: border-box;
    }
    .btn { width: 100%; padding: 14px; border-radius: 20px; font-weight: 600; cursor: pointer; border: none; transition: 0.3s; font-size: 15px; margin-top: 10px; display: block; text-align: center; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: rgba(0,0,0,0.05); color: var(--text); }
    .btn-top { width: auto; display: inline-block; padding: 8px 20px; margin-bottom: 15px; }
    input, select, textarea { 
        width: 100%; padding: 14px; margin: 8px 0; border: 1px solid var(--glass-border); 
        border-radius: 18px; background: rgba(255,255,255,0.5); color: var(--text); outline: none; box-sizing: border-box;
    }
    .modal-box { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 90%; max-width: 700px; z-index: 3000; background: var(--glass);
        backdrop-filter: blur(40px); border-radius: 40px; padding: 30px; border: 1px solid var(--glass-border);
        max-height: 85vh; overflow-y: auto; box-shadow: 0 30px 60px rgba(0,0,0,0.1);
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(0,0,0,0.05); }
    th { background: rgba(0,0,0,0.02); }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="card" style="padding:15px; margin-bottom:10px; cursor:pointer;" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><b>{r.get("pv")}</b><br><small style="opacity:0.6;">{r.get("fecha")} · {r.get("n_documento")}</small></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_IOS_LIGHT}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h2 style="text-align:center; color:var(--accent);">Nestlé BI</h2>
            <a href="/formulario" class="nav-link">Nueva Visita</a>
            <a href="/validacion_admin" class="nav-link" style="background:rgba(0,122,255,0.1);">Revisión 📋</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Puntos de Venta</div>
            <a href="/descargar" class="nav-link">Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#ff3b30; margin-top:20px;">Cerrar Sesión</a>
        </div>
        <div style="padding:20px;">
            <button onclick="toggleMenu()" style="background:var(--accent); border:none; color:white; padding:12px 24px; border-radius:18px; cursor:pointer; font-weight:bold;">☰ Menú Principal</button>
            <h2 style="margin-top:25px; margin-left:5%;">Visitas Realizadas</h2>
            {rows}
        </div>
        <div id="modal_detalle" class="modal-box">
            <button onclick="closeAll()" class="btn btn-gray btn-top">← Regresar</button>
            <div id="det_body"></div>
        </div>
        <div id="modal_puntos" class="modal-box">
            <button onclick="closeAll()" class="btn btn-gray btn-top">← Regresar</button>
            <h3>📍 Gestión de Puntos</h3>
            <input type="text" id="f_pv" placeholder="Buscar..." onkeyup="filtrarPuntos()">
            <div style="overflow-x:auto;"><table id="table_main_puntos"><thead></thead><tbody id="puntos_table"></tbody></table></div>
        </div>
        <div id="modal_csv" class="modal-box">
            <button onclick="closeAll()" class="btn btn-gray btn-top">← Regresar</button>
            <h3>⚙️ Carga Masiva CSV</h3>
            <input type="file" id="fileCsv" accept=".csv">
            <button onclick="subirCsv()" class="btn btn-primary">Procesar Archivo</button>
        </div>
        <div id="modal_usuarios" class="modal-box">
            <button onclick="closeAll()" class="btn btn-gray btn-top">← Regresar</button>
            <h3>👥 Usuarios</h3>
            <div id="user_table"></div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}

            async function subirCsv() {{
                const fileInput = document.getElementById('fileCsv');
                if(!fileInput.files[0]) return alert("Seleccione un archivo");
                const formData = new FormData();
                formData.append('file_csv', fileInput.files[0]);
                const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }});
                const data = await res.json();
                alert("✅ Cargados: " + data.count + " registros");
                closeAll();
            }}

            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); window.allP = await res.json(); renderP(window.allP); }}
            function renderP(l) {{
                const cols = Object.keys(l[0]).filter(k => k !== '_id');
                document.getElementById('table_main_puntos').querySelector('thead').innerHTML = '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '</tr>';
                document.getElementById('puntos_table').innerHTML = l.map(p => `<tr>${{cols.map(c => `<td>${{p[c]||''}}</td>`).join('')}}</tr>`).join('');
            }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>${{doc}} · ${{f}}</p><div id="map" style="height:200px; border-radius:20px; margin-bottom:15px;"></div><div id="imgs"></div>`;
                openModal('modal_detalle');
                setTimeout(async ()=>{{ 
                    const r = await fetch('/get_img/'+id); const d = await r.json();
                    document.getElementById('imgs').innerHTML = `<img src="${{d.f1}}" style="width:100%; border-radius:15px; margin-bottom:10px;"><img src="${{d.f2}}" style="width:100%; border-radius:15px;">`;
                    if(gps) {{ const c=gps.split(','); const m=L.map('map').setView(c,15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m); }}
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
        
        visitas_col.insert_one({{
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2')), "Nota": request.form.get('nota'),
            "motivo": request.form.get('motivo'), "ubicacion": gps
        }})
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    btn_admin = '<a href="/" class="btn btn-gray btn-top" style="margin-right:10px;">← Panel Principal</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_IOS_LIGHT}</head>
    <body onload="getGPS()" style="display:flex; align-items:center; justify-content:center; padding:20px;">
        <div class="card" style="max-width:500px;">
            {btn_admin}
            <h2 style="text-align:center; color:var(--accent);">Reporte de Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <input list="p" name="pv" id="pv_i" placeholder="Seleccionar Punto" onchange="upBMB()" required>
                <datalist id="p">{opts}</datalist>
                <input type="text" name="bmb" id="bmb_i" placeholder="BMB de la Máquina">
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option><option>Máquina Retirada</option></select>
                <textarea name="nota" placeholder="Observaciones adicionales..."></textarea>
                <div style="font-size:12px; margin-top:10px; opacity:0.6;">Foto Máquina / BMB</div>
                <input type="file" name="f1" accept="image/*" capture="camera" required>
                <div style="font-size:12px; margin-top:10px; opacity:0.6;">Foto Fachada</div>
                <input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">Enviar Información</button>
                <a href="/logout" style="display:block; text-align:center; margin-top:20px; color:#ff3b30; text-decoration:none; font-weight:600;">Cerrar Sesión</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ const v=document.getElementById('pv_i').value; const o=Array.from(document.getElementById('p').options).find(x=>x.value===v); if(o) document.getElementById('bmb_i').value=o.dataset.bmb; }}
        </script>
    </body></html>
    """)

# --- APIS Y LOGICA DE CARGA MASIVA (RESTAURADA) ---
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
@app.route('/get_img/<id>')
def get_img(id): d = visitas_col.find_one({"_id": ObjectId(id)}); return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_IOS_LIGHT}</head><body style='display:flex; align-items:center; justify-content:center;'><div class='card' style='width:340px; text-align:center;'><h2 style='color:var(--accent);'>Nestlé BI</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si); w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Distancia', 'Nota', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb_propuesto'), r.get('motivo'), r.get('distancia'), r.get('Nota'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
