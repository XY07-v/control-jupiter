from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_final_v3"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
puntos_col = db['puntos_venta']
usuarios_col = db['usuarios']

# --- CSS ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; }
    .profile-badge { position: absolute; top: 20px; right: 20px; background: white; padding: 8px 15px; border-radius: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: flex; flex-direction: column; align-items: flex-end; z-index: 1000; }
    .profile-badge b { color: var(--dark); font-size: 14px; }
    .profile-badge small { color: var(--primary); font-size: 11px; text-transform: uppercase; font-weight: bold; }
    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); box-sizing: border-box; width: 100%; max-width: 500px; margin: auto; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; margin-top: 10px; text-align: center; display: block; text-decoration: none; font-size: 14px; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-gray { background: #64748B; color: white; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1.5px solid #E2E8F0; border-radius: 10px; box-sizing: border-box; }
    .progress-container { width: 100%; background: #E2E8F0; border-radius: 10px; margin: 15px 0; display: none; }
    .progress-bar { width: 0%; height: 10px; background: #10B981; border-radius: 10px; transition: 0.3s; }
    .sidebar { position: fixed; left: -280px; top: 0; width: 280px; height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; }
    .sidebar.active { left: 0; }
    .menu-toggle { background: var(--primary); color: white; border: none; padding: 12px 18px; border-radius: 10px; cursor: pointer; margin: 20px; }
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
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='display:flex; height:100vh; align-items:center; background:var(--dark);'><div class='card' style='text-align:center;'><h2>VISITAS A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    return render_template_string(f"""
    <html><head>{CSS_BI}</head><body>
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <button class="menu-toggle" onclick="document.getElementById('side').classList.toggle('active')">☰ Menú</button>
        <div id="side" class="sidebar">
            <h3>Andres BI</h3>
            <a href="/formulario" style="color:white; display:block; padding:10px;">📝 Nuevo Reporte</a>
            <div onclick="document.getElementById('m_csv').style.display='block'" style="cursor:pointer; padding:10px;">⚙️ Carga Puntos</div>
            <a href="/logout" style="color:red; display:block; padding:10px; margin-top:20px;">Cerrar Sesión</a>
        </div>
        <div id="m_csv" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:white; padding:30px; border-radius:20px; box-shadow:0 0 100px rgba(0,0,0,0.5); z-index:3000; width:90%; max-width:400px;">
            <h3>Cargar Base de Puntos</h3>
            <p style="font-size:12px; color:gray;">Nota: Si es Excel, guárdalo como <b>CSV (delimitado por comas)</b>.</p>
            <input type="file" id="f_csv" accept=".csv">
            <div class="progress-container" id="p_cont"><div class="progress-bar" id="p_bar"></div></div>
            <div id="status" style="margin:10px 0; font-weight:bold;"></div>
            <button class="btn btn-primary" onclick="subir()">Subir Archivo</button>
            <button class="btn btn-gray" onclick="document.getElementById('m_csv').style.display='none'">Cerrar</button>
        </div>
        <script>
            async function subir() {{
                let f = document.getElementById('f_csv').files[0]; if(!f) return alert("Sube el archivo");
                let fd = new FormData(); fd.append('file_csv', f);
                document.getElementById('p_cont').style.display='block';
                let res = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                if(res.ok) {{ 
                    document.getElementById('p_bar').style.width='100%';
                    document.getElementById('status').innerHTML="✅ ¡Éxito!";
                    setTimeout(()=>location.reload(), 1000);
                }} else {{ 
                    document.getElementById('status').innerHTML="❌ Error: Asegúrate que sea CSV."; 
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        try:
            # Esta lógica limpia el archivo de errores de Excel
            content = f.stream.read().decode("utf-8-sig", errors="ignore")
            # Detectamos si usa ; o ,
            d = ';' if content.count(';') > content.count(',') else ','
            reader = csv.DictReader(io.StringIO(content), delimiter=d)
            lista = []
            for r in reader:
                # Limpiamos espacios en blanco en Id, Punto de Venta, etc.
                clean = {{k.strip(): v.strip() for k, v in r.items() if k}}
                if clean: lista.append(clean)
            if lista:
                puntos_col.delete_many({{}})
                puntos_col.insert_many(lista)
                return "OK", 200
        except: return "Error", 500
    return "No File", 400

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        visitas_col.insert_one({{
            "pv": request.form.get('pv'),
            "n_documento": session['user_name'],
            "fecha": request.form.get('fecha'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'),
            "ubicacion": request.form.get('ubicacion')
        }})
        return redirect('/formulario?ok=1')
    puntos = list(puntos_col.find({{}}, {{"Punto de Venta": 1}}))
    opts = "".join([f'<option value="{{p["Punto de Venta"]}}">' for p in puntos])
    return render_template_string(f"""
    <html><head>{CSS_BI}</head><body style="padding:20px;">
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div class="card">
            <h2>Registro Visita</h2>
            <form method="POST">
                <input list="pts" name="pv" placeholder="Punto de Venta" required><datalist id="pts">{opts}</datalist>
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                <input type="text" name="bmb" placeholder="Dato BMB" required>
                <select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                <input type="hidden" name="ubicacion" id="loc">
                <button class="btn btn-primary">Enviar</button>
                {f'<a href="/" class="btn btn-gray">Volver</a>' if session['role']=='admin' else ''}
            </form>
        </div>
        <script>navigator.geolocation.getCurrentPosition(p=>document.getElementById('loc').value=p.coords.latitude+','+p.coords.longitude);</script>
    </body></html>
    """)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
