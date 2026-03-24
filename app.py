from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
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

# --- CSS ORIGINAL ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle, #1b4332 0%, #081c15 100%); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); z-index: 2000; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 95%; max-width: 850px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 1px solid var(--accent); max-height: 90vh; overflow-y: auto; box-shadow: 0 0 50px rgba(0,0,0,0.9); }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 24px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); width: 100%; box-sizing: border-box; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; font-size: 14px; margin-top: 10px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-gray { background: #495057; color: white; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid var(--accent); border-radius: 8px; background: rgba(0,0,0,0.3); color: white; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 13px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
</style>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>CMR ASISTENCIA A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" style="background: rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border-left:5px solid var(--accent); cursor:pointer;"><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small> - BMB: {r.get("bmb")}</div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#B7E4C7; text-align:center;">MENU</h3>
            <a href="/formulario" class="nav-link">Nuevo Reporte</a>
            <a href="/validacion_bmb" class="nav-link" style="color:#FFD97D;">Validación BMB</a>
            <a href="/logout" class="nav-link" style="color:#FFB3B3;">Cerrar Sesión</a>
        </div>
        <div style="padding:20px;">
            <button onclick="document.getElementById('sidebar').classList.toggle('active')" style="background:none; border:none; color:white; font-size:24px;">☰</button>
            <h2>Visitas</h2>
            <div id="lista">{rows}</div>
        </div>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        pv = request.form.get('pv')
        bmb_input = request.form.get('bmb')
        punto = puntos_col.find_one({"Punto de Venta": pv})
        bmb_actual = punto.get('BMB') if punto else ""
        
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_actual, 
            "bmb_nuevo_solicitado": bmb_input,
            "bmb_pendiente": True if bmb_input != bmb_actual else False,
            "motivo": request.form.get('motivo'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body style="display:flex; justify-content:center; align-items:center; padding:20px;">
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center;">NUEVA VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto</label><input list="p" name="pv" id="pv_i" onchange="upBMB()" required><datalist id="p">{options}</datalist>
                <label>BMB (Editable)</label><input type="text" name="bmb" id="bmb_i">
                <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <label>Motivo</label><select name="motivo"><option>Visita a POC</option><option>Punto Cerrado</option></select>
                <label>Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <button class="btn btn-primary">GUARDAR</button>
            </form>
        </div>
        <script>
            function upBMB() {{ 
                const v = document.getElementById('pv_i').value;
                const o = Array.from(document.getElementById('p').options).find(opt => opt.value === v);
                if(o) document.getElementById('bmb_i').value = o.dataset.bmb;
            }}
        </script>
    </body></html>
    """)

@app.route('/validacion_bmb')
def validacion_bmb():
    if 'user_id' not in session or session['role'] != 'admin': return redirect('/')
    pends = list(visitas_col.find({"bmb_pendiente": True}))
    rows = "".join([f"""
        <div class='card' style='margin-bottom:15px;'>
            <h3>{r['pv']}</h3>
            <p>BMB Actual: {r['bmb']} | <b>Propuesto: {r['bmb_nuevo_solicitado']}</b></p>
            <div style='display:flex; gap:10px;'>
                <img src='{r['f_bmb']}' style='width:50%; border-radius:10px;'>
                <img src='{r['f_fachada']}' style='width:50%; border-radius:10px;'>
            </div>
            <a href='/aprobar_bmb/{r["_id"]}' class='btn btn-primary'>VALIDAR CAMBIO</a>
        </div>
    """ for r in pends])
    return render_template_string(f"<html><head>{CSS_BI}</head><body><div style='padding:20px;'><h2>Validar Cambios</h2>{rows}<br><a href='/'>Volver</a></div></body></html>")

@app.route('/aprobar_bmb/<id>')
def aprobar_bmb(id):
    visita = visitas_col.find_one({"_id": ObjectId(id)})
    puntos_col.update_one({"Punto de Venta": visita['pv']}, {"$set": {"BMB": visita['bmb_nuevo_solicitado']}})
    visitas_col.update_one({"_id": ObjectId(id)}, {"$set": {"bmb": visita['bmb_nuevo_solicitado'], "bmb_pendiente": False}})
    return redirect('/validacion_bmb')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
