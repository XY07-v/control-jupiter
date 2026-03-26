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

CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); }
    .card { background: white; border-radius: 15px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .btn { width: 100%; padding: 10px; border-radius: 10px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 8px; font-size: 13px; text-decoration: none; display: inline-block; text-align: center; box-sizing: border-box; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(8px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 500px; border-radius: 20px; padding: 20px; max-height: 85vh; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; }
    @media (max-width: 768px) { .sidebar { display:none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    
    # Solo datos de texto (sin fotos)
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(50))
    rows = ""
    for v in visitas:
        rows += f'''<div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div><b>{v.get('pv')}</b><br><small>{v.get('fecha')} | {v.get('n_documento')}</small></div>
                <button class="btn btn-light" style="width:auto; margin:0;" onclick="verSoportes('{v['_id']}')">Ver Soportes</button>
            </div>
        </div>'''
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="color:var(--ios-blue);">Nestlé BI</h2>
            <p><b>{session.get('user_name')}</b></p><hr>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/logout" class="btn btn-red" style="margin-top:20px;">Cerrar Sesión</a>
        </div>
        <div class="main-content"><h3>Historial (Últimos 50)</h3>{rows or '<p>No hay registros.</p>'}</div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Carga de Puntos</h3><input type="file" id="f_csv" accept=".csv"><br><br>
            <button class="btn btn-blue" onclick="subirCSV()">Procesar</button>
            <button class="btn btn-light" onclick="closeM()">Cancelar</button>
        </div></div>
        <div id="m_img" class="modal"><div class="modal-content" id="cont_img"></div></div>
        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            async function verSoportes(id) {{
                openM('m_img'); document.getElementById('cont_img').innerHTML = "Cargando imágenes...";
                const r = await fetch('/get_img/'+id); const d = await r.json();
                document.getElementById('cont_img').innerHTML = `
                    <button class="btn btn-light" onclick="closeM()">Cerrar</button>
                    <p><b>Punto:</b> ${{d.pv}}</p>
                    <img src="${{d.f1}}" style="width:100%; border-radius:10px; margin-bottom:10px;">
                    <img src="${{d.f2}}" style="width:100%; border-radius:10px;">
                `;
            }}
            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                location.reload();
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion_admin')
def validacion_admin():
    if session.get('role') != 'admin': return redirect('/')
    # Traemos pendientes SIN IMÁGENES inicialmente
    pends = list(visitas_col.find({"estado": "Pendiente"}, {"f_bmb":0, "f_fachada":0}))
    rows = ""
    for r in pends:
        rows += f'''<div class="card" style="border-left:5px solid #FF9500;">
            <b>{r['pv']}</b><br><small>Asesor: {r['n_documento']} | Distancia: {r.get('distancia')}m</small>
            <div style="margin-top:10px; display:flex; gap:5px;">
                <button class="btn btn-light" onclick="verSoportes('{r['_id']}')">Ver Fotos</button>
                <button class="btn btn-blue" onclick="vF('{r['_id']}', 'aprobar')">Aprobar</button>
                <button class="btn btn-red" onclick="vF('{r['_id']}', 'rechazar')">X</button>
            </div>
        </div>'''
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body><div class='main-content'><h2>Pendientes</h2><a href='/' class='btn btn-light' style='width:100px;'>← Volver</a>{rows or '<p>Limpio.</p>'}</div><div id='m_img' class='modal'><div class='modal-content' id='cont_img'></div></div><script>function openM(id){{document.getElementById(id).style.display='block';}} function closeM(){{document.getElementById('m_img').style.display='none';}} async function verSoportes(id){{openM('m_img'); document.getElementById('cont_img').innerHTML='...'; const r=await fetch('/get_img/'+id); const d=await r.json(); document.getElementById('cont_img').innerHTML='<button class="btn btn-light" onclick="closeM()">Cerrar</button><img src="'+d.f1+'" style="width:100%;"><img src="'+d.f2+'" style="width:100%;">';}} async function vF(id,op){{await fetch('/api/v_final/'+id+'/'+op); location.reload();}}</script></body></html>")

@app.route('/get_img/<id>')
def api_img(id):
    # Solo aquí se carga el peso de las imágenes
    d = visitas_col.find_one({"_id": ObjectId(id)})
    if not d: return jsonify({})
    return jsonify({
        "pv": d.get('pv'),
        "f1": d.get('f_bmb'), 
        "f2": d.get('f_fachada')
    })

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): 
            if not f: return ""
            res = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
            f.close()
            return res
        
        pv_in, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        
        # Lógica de aprobación simple para ahorrar CPU
        estado = "Aprobado" if pnt and pnt.get('BMB') == bmb_in else "Pendiente"
        
        visitas_col.insert_one({
            "pv": pv_in, "n_documento": session.get('user_name'), "fecha": request.form.get('fecha'),
            "bmb_propuesto": bmb_in, "ubicacion": gps, "estado": estado,
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        gc.collect()
        return redirect('/formulario?msg=OK')
    
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos_col.find({}, {"Punto de Venta":1}).limit(200)])
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS_FIXED}</head><body onload=\"navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)\"><div style='max-width:400px; margin:auto; padding:20px;'><div class='card'><h2>Nuevo Reporte</h2><form method='POST' enctype='multipart/form-data'><input list='pts' name='pv' placeholder='Punto de Venta'><datalist id='pts'>{opts}</datalist><input type='text' name='bmb' placeholder='BMB Máquina'><input type='date' name='fecha' value='{datetime.now().strftime('%Y-%m-%d')}'><label style='font-size:10px;'>Foto BMB</label><input type='file' name='f1' accept='image/*' capture='camera'><label style='font-size:10px;'>Foto Fachada</label><input type='file' name='f2' accept='image/*' capture='camera'><input type='hidden' name='ubicacion' id='gps'><button class='btn btn-blue'>Enviar</button><a href='/logout' class='btn btn-red'>Salir</a></form></div></div></body></html>")

@app.route('/api/v_final/<id>/<op>')
def api_v_f(id, op):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    if op == 'aprobar' and v:
        puntos_col.update_one({"Punto de Venta": v['pv']}, {"$set": {"BMB": v['bmb_propuesto'], "Ruta": v['ubicacion']}}, upsert=True)
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Aprobado"}})
    else:
        visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"estado": "Rechazado"}})
    return jsonify({"s":"ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def api_csv():
    f = request.files.get('file_csv')
    content = f.read().decode("utf-8-sig")
    d = ';' if content.count(';') > content.count(',') else ','
    reader = csv.DictReader(io.StringIO(content), delimiter=d)
    lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
    if lista:
        puntos_col.delete_many({})
        puntos_col.insert_many(lista)
    return jsonify({"ok": True})

@app.route('/api/puntos')
def api_p(): return jsonify(list(puntos_col.find({}, {"_id":0}).limit(50)))

@app.route('/api/usuarios')
def api_u(): return jsonify(list(usuarios_col.find({}, {"_id":0})))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id':str(u['_id']), 'user_name':u['nombre_completo'], 'role':u.get('rol','asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_FIXED}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input type='text' name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
