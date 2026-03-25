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

# --- DISEÑO iOS 26 LIQUID GLASS ---
CSS_IOS26 = """
<style>
    :root { 
        --glass: rgba(255, 255, 255, 0.1); 
        --glass-border: rgba(255, 255, 255, 0.2);
        --accent: #4ade80; 
        --bg-liquid: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #081c15 100%);
    }
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif; 
        background: var(--bg-liquid); background-attachment: fixed; margin: 0; color: white; min-height: 100vh;
    }
    .overlay { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.4); backdrop-filter: blur(20px); z-index: 2000; 
    }
    .sidebar { 
        position: fixed; left: -300px; top: 15px; width: 280px; height: calc(100% - 30px); 
        background: var(--glass); backdrop-filter: blur(30px); border-radius: 30px;
        border: 1px solid var(--glass-border); transition: 0.5s cubic-bezier(0.4, 0, 0.2, 1); 
        z-index: 2100; padding: 30px; box-sizing: border-box; left: -300px;
    }
    .sidebar.active { left: 15px; }
    .nav-link { 
        display: block; color: #fff; text-decoration: none; padding: 16px; 
        border-radius: 20px; margin-bottom: 10px; background: rgba(255,255,255,0.05);
        transition: 0.3s; font-weight: 500;
    }
    .nav-link:hover { background: var(--accent); color: #000; transform: scale(1.02); }
    
    .card { 
        background: var(--glass); backdrop-filter: blur(25px); border-radius: 35px; 
        padding: 25px; border: 1px solid var(--glass-border); box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    }
    .btn { 
        width: 100%; padding: 15px; border-radius: 20px; font-weight: 600; cursor: pointer; 
        border: none; transition: 0.3s; font-size: 15px; margin-top: 12px;
    }
    .btn-primary { background: white; color: black; }
    .btn-primary:active { transform: scale(0.96); }
    .btn-gray { background: rgba(255,255,255,0.1); color: white; backdrop-filter: blur(10px); }
    
    input, select, textarea { 
        width: 100%; padding: 14px; margin: 8px 0; border: 1px solid var(--glass-border); 
        border-radius: 18px; background: rgba(255,255,255,0.05); color: white; outline: none;
    }
    .list-item { 
        background: var(--glass); border-radius: 25px; padding: 20px; margin-bottom: 15px;
        border: 1px solid var(--glass-border); transition: 0.3s;
    }
    h2 { font-weight: 700; letter-spacing: -1px; }
    .modal-box { 
        display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 90%; max-width: 600px; z-index: 3000; background: rgba(30,30,30,0.8);
        backdrop-filter: blur(40px); border-radius: 40px; padding: 35px; border: 1px solid var(--glass-border);
        max-height: 85vh; overflow-y: auto;
    }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><b>{r.get("pv")}</b><br><small style="opacity:0.6;">{r.get("fecha")} · {r.get("n_documento")}</small><div style="color:var(--accent); font-weight:bold; margin-top:5px;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_IOS26}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div id="sidebar" class="sidebar">
            <h2 style="text-align:center; margin-bottom:30px;">Nestlé BI</h2>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <a href="/validacion_admin" class="nav-link" style="background:rgba(74,222,128,0.2);">Pendientes 📋</a>
            <div class="nav-link" onclick="openModal('modal_puntos')">Puntos de Venta</div>
            <a href="/descargar" class="nav-link">Exportar Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">Carga Masiva</div>
            <div class="nav-link" onclick="openModal('modal_usuarios')">Usuarios</div>
            <a href="/logout" class="nav-link" style="color:#ff6b6b; margin-top:30px;">Cerrar Sesión</a>
        </div>
        <div style="padding:25px; max-width:800px; margin:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <button onclick="toggleMenu()" style="background:var(--glass); border:none; color:white; padding:12px 20px; border-radius:15px; cursor:pointer;">☰ Menú</button>
                <div style="text-align:right;"><small style="opacity:0.5;">Admin</small><br><b>{session['user_name']}</b></div>
            </div>
            <h2 style="margin-top:40px;">Visitas</h2>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_puntos" class="modal-box"><h3>📍 Puntos</h3><input type="text" id="f_pv" placeholder="Buscar punto..." onkeyup="filtrarPuntos()"><div style="max-height:400px; overflow:auto;"><table id="table_main_puntos" style="width:100%;"><thead></thead><tbody id="puntos_table"></tbody></table></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_usuarios" class="modal-box"><h3>👥 Usuarios</h3><button class="btn btn-primary" onclick="abrirPopUser()">+ Nuevo Usuario</button><div id="user_table"></div><button onclick="closeAll()" class="btn btn-gray">Cerrar</button></div>
        <div id="modal_csv" class="modal-box"><h3>⚙️ Carga Masiva</h3><p style="opacity:0.7;">Seleccione el archivo .csv para actualizar la base de puntos.</p><input type="file" id="fileCsv" accept=".csv"><button onclick="subirCsv()" class="btn btn-primary">Procesar Archivo</button><button onclick="closeAll()" class="btn btn-gray">Cancelar</button></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display='block'; document.getElementById(id).style.display='block'; if(id==='modal_puntos') cargarPuntos(); if(id==='modal_usuarios') cargarUsuarios(); }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display='none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display='none'; }}
            
            // LÓGICA CARGA MASIVA (CORREGIDA)
            async function subirCsv() {{
                const file = document.getElementById('fileCsv').files[0];
                if(!file) return alert('Seleccione un archivo');
                const formData = new FormData(); formData.append('file', file);
                const res = await fetch('/api/subir_csv', {{ method: 'POST', body: formData }});
                const data = await res.json();
                alert(data.msg); closeAll();
            }}

            async function cargarPuntos() {{ const res = await fetch('/api/puntos'); const p = await res.json(); document.getElementById('puntos_table').innerHTML = p.map(x => `<tr><td>${{x['Punto de Venta']}}</td><td>${{x['BMB']}}</td></tr>`).join(''); }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p>${{doc}} - ${{f}}</p><img id="im1" style="width:100%; border-radius:20px;"><div id="map" style="height:200px; border-radius:20px; margin-top:15px;"></div>`;
                openModal('modal_detalle');
                setTimeout(async ()=>{{ 
                    const r = await fetch('/get_img/'+id); const d = await res.json(); document.getElementById('im1').src=d.f1;
                    const c=gps.split(','); const m=L.map('map').setView(c,15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
                }},200);
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
        pend = (bmb_in != bmb_orig) or (dist > 100)
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "bmb_pendiente": bmb_in != bmb_orig,
            "ubicacion": gps, "gps_anterior": pnt.get('Ruta') if pnt else gps,
            "distancia": round(dist, 1), "estado": "Pendiente" if pend else "Aprobado",
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2')), "Nota": request.form.get('nota')
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    # BOTÓN REGRESAR SOLO PARA ADMIN
    btn_back = '<a href="/" class="btn btn-gray">← Panel Administrador</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_IOS26}</head>
    <body onload="getGPS()" style="display:flex; align-items:center; justify-content:center; padding:20px;">
        <div class="card" style="width:100%; max-width:450px;">
            <h2 style="text-align:center;">Nueva Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <input list="p" name="pv" id="pv_i" placeholder="Seleccionar Punto" onchange="upBMB()" required>
                <datalist id="p">{opts}</datalist>
                <input type="text" name="bmb" id="bmb_i" placeholder="BMB">
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <textarea name="nota" placeholder="Observaciones..."></textarea>
                <div style="font-size:12px; opacity:0.6; margin-top:10px;">Foto BMB</div>
                <input type="file" name="f1" accept="image/*" capture="camera" required>
                <div style="font-size:12px; opacity:0.6; margin-top:10px;">Foto Fachada</div>
                <input type="file" name="f2" accept="image/*" capture="camera" required>
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">Enviar Reporte</button>
                {btn_back}
                <a href="/logout" style="display:block; text-align:center; margin-top:20px; color:#ff6b6b; text-decoration:none;">Cerrar Sesión</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{ const v=document.getElementById('pv_i').value; const o=Array.from(document.getElementById('p').options).find(x=>x.value===v); if(o) document.getElementById('bmb_i').value=o.dataset.bmb; }}
        </script>
    </body></html>
    """)

# --- ENDPOINT CARGA MASIVA ---
@app.route('/api/subir_csv', methods=['POST'])
def api_subir_csv():
    if 'file' not in request.files: return jsonify({"msg": "No hay archivo"})
    file = request.files['file']
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.DictReader(stream)
    count = 0
    for row in reader:
        # Se asume que el CSV tiene: Punto de Venta, BMB, Ruta
        puntos_col.update_one(
            {"Punto de Venta": row['Punto de Venta']},
            {"$set": row},
            upsert=True
        )
        count += 1
    return jsonify({"msg": f"Se procesaron {count} puntos correctamente."})

# --- RESTO DE APIS MANTENIDAS ---
@app.route('/api/puntos')
def api_puntos(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)
@app.route('/api/usuarios')
def api_u(): u=list(usuarios_col.find()); [x.update({"_id":str(x["_id"])}) for x in u]; return jsonify(u)
@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Base', 'BMB Propuesto', 'Distancia', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), r.get('distancia'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

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
