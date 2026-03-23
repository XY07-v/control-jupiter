from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
import pandas as pd  # <-- Nueva librería para carga robusta
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_final"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; --sidebar-w: 280px; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; }
    .sidebar { position: fixed; left: -280px; top: 0; width: var(--sidebar-w); height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #E2E8F0; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: rgba(255,255,255,0.1); color: white; }
    .profile-badge { position: absolute; top: 20px; right: 20px; background: white; padding: 8px 15px; border-radius: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: flex; flex-direction: column; align-items: flex-end; z-index: 1000; }
    .profile-badge b { color: var(--dark); font-size: 14px; }
    .profile-badge small { color: var(--primary); font-size: 11px; text-transform: uppercase; font-weight: bold; }
    .main-content { width: 100%; padding: 20px; transition: 0.3s; position: relative; }
    .header-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; margin-top: 10px; }
    .menu-toggle { background: var(--primary); color: white; border: none; padding: 12px 18px; border-radius: 10px; cursor: pointer; font-size: 20px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.3); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 700px; z-index: 2500; background: white; border-radius: 24px; padding: 30px; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 40px rgba(0,0,0,0.2); box-sizing: border-box; }
    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); box-sizing: border-box; width: 100%; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; text-decoration: none; display: inline-block; font-size: 14px; box-sizing: border-box; margin-top: 10px; text-align: center; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-gray { background: #64748B; color: white; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1.5px solid #E2E8F0; border-radius: 10px; box-sizing: border-box; }
    .progress-container { width: 100%; background: #E2E8F0; border-radius: 10px; margin: 15px 0; display: none; }
    .progress-bar { width: 0%; height: 10px; background: #10B981; border-radius: 10px; transition: 0.3s; }
    .list-item { background: white; padding: 18px; border-radius: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 5px solid var(--primary); }
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center; background:var(--dark); display:flex; height:100vh;'><div class='card' style='width:340px; text-align:center;'><h2>VISITAS A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:var(--primary); font-weight:bold;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#FFF; margin-bottom:5px;">Andres BI</h3>
            <p style="font-size:12px; color:#94A3B8; margin-bottom:25px;">👤 {session['user_name']}</p>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <a href="/descargar" class="nav-link">📊 Reporte Excel</a>
            <div class="nav-link" onclick="openModal('modal_csv')">⚙️ Carga Puntos PDV</div>
            <a href="/logout" class="nav-link" style="color:#F87171; margin-top:40px;">🚪 Cerrar Sesión</a>
        </div>
        <div class="main-content">
            <div class="header-bar"><button class="menu-toggle" onclick="toggleMenu()">☰</button><h2 style="margin:0;">Bienvenido, {session['user_name']}</h2></div>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_csv" class="modal-box">
            <h3>Carga Masiva (Excel o CSV)</h3>
            <p style="font-size:12px; color:gray;">Sube tu archivo .xlsx o .csv con las columnas Id, Punto de Venta, Departamento, Ciudad, BMB.</p>
            <form id="uploadForm">
                <input type="file" id="fileCsv" accept=".csv, .xlsx" required>
                <div class="progress-container" id="progCont"><div class="progress-bar" id="progBar"></div></div>
                <div id="statusMsg" style="margin:10px 0; font-size:14px; font-weight:bold;"></div>
                <button type="button" onclick="subirMasivo()" class="btn btn-primary" id="btnSubir">Actualizar Base PDV</button>
            </form>
            <button onclick="closeModal('modal_csv')" class="btn btn-gray">Cerrar</button>
        </div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display = 'block'; document.getElementById(id).style.display = 'block'; }}
            function closeModal(id) {{ document.getElementById(id).style.display = 'none'; document.getElementById('overlay').style.display = 'none'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display = 'none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display = 'none'; }}
            async function subirMasivo() {{
                const fileInput = document.getElementById('fileCsv'); if(!fileInput.files[0]) return alert("Selecciona un archivo");
                const formData = new FormData(); formData.append('file', fileInput.files[0]);
                document.getElementById('progCont').style.display = 'block'; document.getElementById('btnSubir').disabled = true; document.getElementById('statusMsg').innerText = "Procesando...";
                let bar = document.getElementById('progBar'); let width = 0;
                let interval = setInterval(() => {{ if(width >= 90) clearInterval(interval); else {{ width += 10; bar.style.width = width + '%'; }} }}, 150);
                try {{
                    const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }});
                    clearInterval(interval);
                    if(res.ok) {{ bar.style.width = '100%'; document.getElementById('statusMsg').style.color = 'green'; document.getElementById('statusMsg').innerText = "✅ ¡Base de datos actualizada!"; }} 
                    else {{ throw new Error(); }}
                }} catch(e) {{ document.getElementById('statusMsg').style.color = 'red'; document.getElementById('statusMsg').innerText = "❌ Error en el formato del archivo."; }} 
                finally {{ document.getElementById('btnSubir').disabled = false; }}
            }}
        </script>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file')
    if not f: return "No File", 400
    try:
        # PANDAS detecta automáticamente si es Excel o CSV y limpia los nombres de columnas
        if f.filename.endswith('.xlsx'):
            df = pd.read_excel(f)
        else:
            # Si es CSV, intenta detectar el delimitador automáticamente
            df = pd.read_csv(f, sep=None, engine='python', encoding='utf-8-sig')
        
        # Limpieza de nombres de columnas (quitar espacios invisibles)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Convertir a lista de diccionarios y limpiar valores
        data = df.fillna("").to_dict(orient='records')
        
        if data:
            puntos_col.delete_many({})
            puntos_col.insert_many(data)
            return "OK", 200
        return "Empty", 400
    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        f_val = request.form.get('fecha')
        visitas_col.insert_one({"pv": request.form.get('pv'), "n_documento": session['user_name'], "fecha": f_val, "mes": f_val[:7], "bmb": request.form.get('bmb'), "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'), "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))})
        return redirect('/formulario?msg=OK') if session['role'] == 'asesor' else redirect('/')
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="justify-content:center; align-items:center; display:flex; height:100vh;">
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div class="card" style="max-width:480px; width:95%;">
            <h2 style="text-align:center; color:var(--dark); margin-top:0;">Bienvenido, {session['user_name']}</h2>
            <form method="POST" enctype="multipart/form-data">
                <input list="p" name="pv" placeholder="Punto de Venta" required><datalist id="p">{options}</datalist>
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <input type="text" name="bmb" placeholder="Dato BMB" required>
                <select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                <input type="hidden" name="ubicacion" id="g">
                <label style="font-size:12px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label style="font-size:12px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                <button class="btn btn-primary">Enviar Registro</button>
                {f'<a href="/" class="btn btn-gray">Volver</a>' if session['role']=='admin' else ''}
            </form>
        </div>
        <script>function getGPS(){{navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude;}},null,{{enableHighAccuracy:true}});}}</script>
    </body></html>
    """)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
