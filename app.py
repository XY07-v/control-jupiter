from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB (ESTRICTA) ---
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

# --- CSS IOS 26 PULIDO Y COMPACTO ---
CSS_PULIDO = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --card: rgba(255,255,255,0.85); }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; color: #1c1c1e; }
    .nav-header { 
        background: rgba(255,255,255,0.7); backdrop-filter: blur(20px); 
        padding: 10px 20px; position: sticky; top: 0; z-index: 1000;
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 0.5px solid rgba(0,0,0,0.1);
    }
    .container { padding: 15px; max-width: 600px; margin: auto; }
    .card { 
        background: var(--card); border-radius: 18px; padding: 15px; margin-bottom: 12px;
        border: 0.5px solid rgba(0,0,0,0.05); box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        cursor: pointer; transition: 0.2s;
    }
    .btn { 
        padding: 10px 16px; border-radius: 12px; border: none; font-weight: 600; 
        font-size: 14px; cursor: pointer; text-decoration: none; display: inline-block;
    }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: rgba(0,0,0,0.05); color: var(--ios-blue); }
    input, select, textarea { 
        width: 100%; padding: 12px; margin: 8px 0; border: 0.5px solid #d1d1d6; 
        border-radius: 10px; background: white; font-size: 15px; box-sizing: border-box;
    }
    .modal { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.3); backdrop-filter: blur(15px); z-index: 2000;
    }
    .modal-content { 
        background: white; margin: 10% auto; width: 90%; max-width: 500px; 
        border-radius: 25px; padding: 20px; max-height: 80vh; overflow-y: auto;
    }
    .badge-pend { color: #FF9500; font-weight: bold; font-size: 11px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { text-align: left; padding: 10px; border-bottom: 0.5px solid #d1d1d6; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1))
    rows = "".join([f'''<div class="card" onclick="verDetalle('{v["_id"]}', '{v.get("pv")}', '{v.get("n_documento")}', '{v.get("fecha")}')">
        <b>{v.get("pv")}</b><br>
        <span style="font-size:12px; opacity:0.6;">{v.get("n_documento")} · {v.get("fecha")}</span>
    </div>''' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_PULIDO}</head>
    <body>
        <div class="nav-header">
            <h3 style="margin:0;">Nestlé BI</h3>
            <div>
                <button class="btn btn-light" onclick="openM('m_menu')">Opciones</button>
            </div>
        </div>
        <div class="container">{rows}</div>

        <div id="m_menu" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="float:right;">X</button>
            <h3>Menú Admin</h3>
            <a href="/formulario" class="btn btn-blue" style="width:100%; margin-bottom:8px;">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="width:100%; margin-bottom:8px; color:#FF9500;">Pendientes de Validación</a>
            <button class="btn btn-light" style="width:100%; margin-bottom:8px;" onclick="openM('m_puntos')">Base de Puntos</button>
            <button class="btn btn-light" style="width:100%; margin-bottom:8px;" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light" style="width:100%; margin-bottom:8px;">Exportar CSV</a>
            <a href="/logout" class="btn btn-light" style="width:100%; color:red;">Cerrar Sesión</a>
        </div></div>

        <div id="m_detalle" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="margin-bottom:10px;">← Regresar</button>
            <div id="det_cont"></div>
        </div></div>

        <div id="m_puntos" class="modal"><div class="modal-content" style="max-width:700px;">
            <button class="btn btn-light" onclick="closeM()">← Volver</button>
            <h3>Puntos de Venta</h3>
            <div id="puntos_list" style="overflow-x:auto;"></div>
        </div></div>

        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()">← Volver</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="f_csv">
            <button class="btn btn-blue" onclick="subir()">Cargar</button>
        </div></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function openM(id){{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargarP(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            
            async function verDetalle(id, pv, as, fe) {{
                document.getElementById('det_cont').innerHTML = `<h4>${{pv}}</h4><p style="font-size:12px;">${{as}} | ${{fe}}</p><div id="map" style="height:180px; border-radius:15px; margin-bottom:10px;"></div><div id="fotos">Cargando imágenes...</div>`;
                openM('m_detalle');
                const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('fotos').innerHTML = `<img src="${{d.f1}}" style="width:100%; border-radius:12px; margin-bottom:8px;"><img src="${{d.f2}}" style="width:100%; border-radius:12px;">`;
                if(d.gps) {{
                    const c = d.gps.split(','); 
                    const map = L.map('map').setView(c, 15);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                    L.marker(c).addTo(map);
                }}
            }}

            async function cargarP() {{
                const res = await fetch('/api/puntos'); const pts = await res.json();
                let h = '<table><tr><th>Nombre</th><th>BMB</th></tr>';
                pts.forEach(p => {{ h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td></tr>`; }});
                document.getElementById('puntos_list').innerHTML = h + '</table>';
            }}

            async function subir() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); location.reload();
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
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
            "gps_anterior": pnt.get('Ruta') if pnt else gps, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2')),
            "Nota": request.form.get('nota'), "motivo": request.form.get('motivo')
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    btn_back = '<a href="/" class="btn btn-light" style="margin-bottom:15px;">← Volver</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_PULIDO}</head>
    <body onload="getG()">
        <div class="container" style="max-width:450px;">
            {btn_back}
            <div class="card" style="cursor:default;">
                <h3 style="text-align:center; color:var(--ios-blue);">Reporte de Visita</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" id="pv_i" placeholder="Punto de Venta" onchange="setB()" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                    <textarea name="nota" placeholder="Observaciones"></textarea>
                    <label style="font-size:11px; opacity:0.6;">Foto Máquina</label>
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    <label style="font-size:11px; opacity:0.6;">Foto Fachada</label>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue" style="width:100%; margin-top:15px;">Enviar Reporte</button>
                </form>
            </div>
            <a href="/logout" style="display:block; text-align:center; color:red; text-decoration:none; margin-top:15px; font-size:14px;">Cerrar Sesión</a>
        </div>
        <script>
            function getG(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude);}}
            function setB(){{const i=document.getElementById('pv_i').value; const o=document.querySelector('#pts option[value="'+i+'"]'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;}}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    pends = list(visitas_col.find({"estado": "Pendiente"}))
    rows = ""
    for r in pends:
        rows += f'''<div class="card" style="border-left: 5px solid #FF9500;">
            <b>{r['pv']}</b><br><small>Diferencia: {r['distancia']}m</small>
            <div style="display:flex; gap:5px; margin:10px 0;">
                <img src="{r['f_bmb']}" style="width:50%; border-radius:10px;">
                <img src="{r['f_fachada']}" style="width:50%; border-radius:10px;">
            </div>
            <div style="display:flex; gap:10px;">
                <button class="btn btn-blue" style="background:#34C759; flex:1;" onclick="vFinal('{r['_id']}', 'aprobar')">Aprobar</button>
                <button class="btn btn-light" style="color:red; flex:1;" onclick="vFinal('{r['_id']}', 'rechazar')">Rechazar</button>
            </div>
        </div>'''
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_PULIDO}</head>
    <body>
        <div class="nav-header"><button class="btn btn-light" onclick="history.back()">← Volver</button><h3>Validación</h3><div></div></div>
        <div class="container">{rows or '<p>No hay pendientes</p>'}</div>
        <script>async function vFinal(id, op){{ await fetch('/api/v_final/'+id+'/'+op); location.reload(); }}</script>
    </body></html>
    """)

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

@app.route('/get_img/<id>')
def get_img(id):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    return jsonify({"f1": v.get('f_bmb'), "f2": v.get('f_fachada'), "gps": v.get('ubicacion')})

@app.route('/api/puntos')
def api_pts(): p=list(puntos_col.find()); [x.update({"_id":str(x["_id"])}) for x in p]; return jsonify(p)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig")
        d = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=d)
        lista = [r for r in reader]
        if lista:
            puntos_col.delete_many({}); puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB Propuesto', 'Estado'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb_propuesto'), r.get('estado')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user['nombre_completo'], 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_PULIDO}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue' style='width:100%;'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
