from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json, gc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v15_stable"

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
    if session.get('role') == 'asesor': return redirect('/formulario')
    
    # Se excluyen las fotos de la consulta para no saturar la RAM
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(40))
    rows = "".join([f'<div class="card"><b>{v.get("pv")}</b><br><small>{v.get("fecha")} - {v.get("n_documento")}</small><button class="btn btn-light" style="margin-top:10px;" onclick="verVisita(\'{v["_id"]}\')">Consultar Imágenes</button></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:13px; font-weight:bold;">{session.get('user_name')}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content"><h3>Historial Reciente</h3>{rows or '<p>No hay registros.</p>'}</div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        <script>
            async function verVisita(id) {{
                document.getElementById('m_det').style.display='block';
                document.getElementById('det_body').innerHTML = "Cargando imágenes...";
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                document.getElementById('det_body').innerHTML = `
                    <button class="btn btn-light" onclick="document.getElementById('m_det').style.display='none'">Cerrar</button>
                    <p><b>Punto:</b> ${{d.pv}}</p>
                    <img src="${{d.f1}}" style="width:100%; border-radius:15px; margin-bottom:10px;">
                    <img src="${{d.f2}}" style="width:100%; border-radius:15px;">
                `;
            }}
        </script>
    </body></html>
    """)

@app.route('/get_img/<id>')
def api_img(id):
    # Solo aquí se recuperan las imágenes de un único registro
    d = visitas_col.find_one({"_id": ObjectId(id)})
    if not d: return jsonify({})
    return jsonify({"pv": d.get('pv'), "f1": d.get('f_bmb'), "f2": d.get('f_fachada'), "gps": d.get('ubicacion')})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        try:
            def b64(f):
                if not f or not f.filename: return ""
                encoded = base64.b64encode(f.read()).decode()
                f.close() # Cierre inmediato para liberar memoria
                return f"data:image/jpeg;base64,{encoded}"

            pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
            pnt = puntos_col.find_one({"Punto de Venta": pv_in})
            
            bmb_orig = pnt.get('BMB', "") if pnt else "NUEVO"
            ruta_orig = pnt.get('Ruta', "") if pnt else ""
            dist = calcular_distancia(gps, ruta_orig)
            
            estado_v = "Pendiente" if (pnt and bmb_in != bmb_orig) or dist > 100 else "Aprobado"

            visitas_col.insert_one({
                "pv": pv_in, "n_documento": session.get('user_name'), "fecha": request.form.get('fecha'),
                "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
                "distancia": round(dist, 1), "estado": estado_v,
                "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
            })

            if estado_v == "Aprobado":
                puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"BMB": bmb_in, "Ruta": gps}}, upsert=True)
            
            gc.collect() # Limpieza forzada de RAM
            return redirect('/formulario?msg=OK')
        except Exception as e: return str(e), 500
    
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos_col.find({}, {"Punto de Venta":1}).limit(200)])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div style="max-width:400px; margin:auto; padding:20px;">
            <div class="card">
                <h2 style="text-align:center;">Reporte BI</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Punto de Venta" required><datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" placeholder="BMB Máquina" required>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button class="btn btn-blue">Enviar</button>
                    <a href="/" class="btn btn-light">Volver</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    # No cargamos imágenes masivas en la vista de validación
    pends = list(visitas_col.find({"estado": "Pendiente"}, {"f_bmb":0, "f_fachada":0}))
    rows = ""
    for r in pends:
        rows += f'''<div class="card" style="border-left:8px solid #FF9500;">
            <b>{r['pv']}</b><br><small>{r['n_documento']} | Dist: {r.get('distancia')}m</small>
            <div style="margin-top:10px; display:flex; gap:5px;">
                <button class="btn btn-light" onclick="verVisita('{r['_id']}')">Ver Fotos</button>
                <button class="btn btn-blue" onclick="vF('{r['_id']}', 'aprobar')">✓</button>
                <button class="btn btn-red" onclick="vF('{r['_id']}', 'rechazar')">X</button>
            </div>
        </div>'''
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body><div class='main-content'><h2>Pendientes</h2>{rows or '<p>Limpio.</p>'}</div><div id='m_det' class='modal'><div class='modal-content' id='det_body'></div></div><script>async function verVisita(id){{ document.getElementById('m_det').style.display='block'; document.getElementById('det_body').innerHTML='Cargando...'; const r=await fetch('/get_img/'+id); const d=await r.json(); document.getElementById('det_body').innerHTML='<button class="btn btn-light" onclick=\\"document.getElementById(\\'m_det\\').style.display=\\'none\\'\\">Cerrar</button><img src=\\"'+d.f1+'\\" style=\\"width:100%;\\"><img src=\\"'+d.f2+'\\" style=\\"width:100%;\\">'; }} async function vF(id,op){{ await fetch('/api/v_final/'+id+'/'+op); location.reload(); }}</script></body></html>")

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar' and v:
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: 
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
