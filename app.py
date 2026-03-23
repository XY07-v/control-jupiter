from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_verde_final"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS VERDE OSCURO Y DISEÑO ---
CSS_BI = """
<style>
    :root { --primary: #1B4332; --dark: #081C15; --accent: #40916C; --bg: #081C15; }
    body { 
        font-family: 'Segoe UI', sans-serif; 
        background: radial-gradient(circle, #1b4332 0%, #081c15 100%); 
        margin: 0; display: flex; color: white; min-height: 100vh;
    }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; border-right: 1px solid var(--accent); }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #D8F3DC; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: var(--primary); }
    
    .profile-badge { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 8px 15px; border-radius: 30px; border: 1px solid var(--accent); display: flex; flex-direction: column; align-items: flex-end; z-index: 1000; }
    .profile-badge b { color: #D8F3DC; font-size: 14px; }
    .profile-badge small { color: #95D5B2; font-size: 11px; text-transform: uppercase; }

    .main-content { width: 100%; padding: 20px; position: relative; }
    .card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border-radius: 24px; padding: 30px; border: 1px solid rgba(255,255,255,0.1); box-sizing: border-box; width: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
    
    .btn { width: 100%; padding: 14px; border-radius: 12px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; text-decoration: none; display: inline-block; font-size: 14px; box-sizing: border-box; margin-top: 15px; text-align: center; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-primary:hover { background: #52B788; }
    .btn-logout { background: #BC4749; color: white; }
    
    label { display: block; margin-top: 12px; font-size: 13px; color: #B7E4C7; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid var(--accent); border-radius: 10px; background: rgba(0,0,0,0.2); color: white; box-sizing: border-box; }
    
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 500px; z-index: 3000; background: #1B4332; border-radius: 24px; padding: 30px; border: 2px solid var(--accent); text-align: center; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 2500; }
    
    .list-item { background: rgba(255,255,255,0.05); padding: 18px; border-radius: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 5px solid var(--accent); cursor: pointer; }
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center;'><div class='card' style='max-width:350px; text-align:center;'><h2>SISTEMA POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>ENTRAR</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'alert("BMB: {r.get("bmb")}\\nNota: {r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:#95D5B2;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="side" class="sidebar">
            <h3 style="color:#B7E4C7;">Andres BI</h3>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <a href="/logout" class="nav-link" style="color:#FFB3B3; margin-top:30px;">🚪 Cerrar Sesión</a>
        </div>
        <div class="main-content">
            <button onclick="document.getElementById('side').classList.toggle('active')" style="background:none; border:none; color:white; font-size:24px; cursor:pointer;">☰</button>
            <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
            <h2 style="margin-top:20px;">Panel de Control</h2>
            <div id="lista">{rows}</div>
        </div>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    msg_ok = request.args.get('msg') == 'OK'
    
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        f_val = request.form.get('fecha')
        visitas_col.insert_one({
            "pv": request.form.get('pv'), "n_documento": session['user_name'], "fecha": f_val, "mes": f_val[:7], 
            "bmb": request.form.get('bmb'), "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'), 
            "Nota": request.form.get('nota'), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="justify-content:center; align-items:center; display:flex; padding:20px;">
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        
        <div id="over" class="overlay" style="display:{'block' if msg_ok else 'none'};" onclick="this.style.display='none'"></div>
        <div id="pop" class="modal-box" style="display:{'block' if msg_ok else 'none'};">
            <h1 style="font-size:50px; margin:0;">✅</h1>
            <h2>¡Registro Exitoso!</h2>
            <p>La información se guardó correctamente.</p>
            <button onclick="location.href='/formulario'" class="btn btn-primary">Aceptar</button>
        </div>

        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center; color:#B7E4C7; margin-top:0;">FORMULARIO DE VISITA</h2>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input list="p" name="pv" id="pv_i" placeholder="Seleccione PDV..." onchange="upBMB()" required><datalist id="p">{options}</datalist>
                
                <label>Dato BMB Asociado</label>
                <input type="text" name="bmb" id="bmb_i" readonly style="background:rgba(255,255,255,0.05);">
                
                <label>Fecha de Visita</label>
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                
                <label>Motivo de la Visita</label>
                <select name="motivo">
                    <option>Máquina Retirada</option>
                    <option>Punto Cerrado</option>
                    <option>Dificultades Trade</option>
                    <option>Fuera de rango</option>
                </select>
                
                <label>Observaciones (Nota)</label>
                <textarea name="nota" rows="3" placeholder="Escriba aquí..."></textarea>
                
                <label>Foto Evidencia 1</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label>Foto Evidencia 2</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                
                <input type="hidden" name="ubicacion" id="g">
                <button class="btn btn-primary">ENVIAR REGISTRO</button>
                
                <a href="/logout" class="btn btn-logout">SALIDA / DESLOGUEO</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude);}}
            function upBMB() {{
                const v = document.getElementById('pv_i').value;
                const o = document.getElementById('p').childNodes;
                for (let i=0; i<o.length; i++) if(o[i].value===v) document.getElementById('bmb_i').value=o[i].getAttribute('data-bmb');
            }}
        </script>
    </body></html>
    """)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
