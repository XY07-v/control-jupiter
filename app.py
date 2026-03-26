from flask import Flask, render_template_string, request, jsonify, session, redirect
from pymongo import MongoClient
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_fixed_2026"

# --- CONEXIÓN MONGODB ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['NestleDB']
puntos_col = db['puntos_venta']
visitas_col = db['visitas']
usuarios_col = db['usuarios']

# --- INTERFAZ DE LOGIN ---
HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Nestlé BI</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #F2F2F7; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 90%; max-width: 350px; text-align: center; }
        input { width: 100%; padding: 15px; margin: 20px 0; border: 1px solid #D1D1D6; border-radius: 12px; font-size: 18px; text-align: center; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #007AFF; color: white; border: none; border-radius: 12px; font-weight: bold; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="login-card">
        <h3>Insertar Credencial</h3>
        <form action="/login" method="POST">
            <input type="password" name="cedula" placeholder="Contraseña" required>
            <button type="submit">Entrar</button>
            {% if error %}<p style="color:red; font-size:14px; margin-top:10px;">Credencial no válida</p>{% endif %}
        </form>
    </div>
</body>
</html>
"""

# --- INTERFAZ DEL SISTEMA ---
HTML_SISTEMA = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nestlé BI</title>
    <style>
        :root { --blue: #007AFF; --green: #34C759; --bg: #F2F2F7; --gray: #8E8E93; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; }
        .tabs { display: flex; gap: 8px; margin-bottom: 15px; position: sticky; top: 0; background: var(--bg); z-index: 100; padding: 5px 0; }
        .tab-btn { flex: 1; padding: 12px; border: none; border-radius: 12px; background: #E5E5EA; font-weight: 600; color: var(--gray); }
        .tab-btn.active { background: var(--blue); color: white; }
        .content { display: none; background: white; padding: 20px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .content.active { display: block; }
        input, select, textarea { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
        button.primary { width: 100%; padding: 16px; background: var(--blue); color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; }
        #success-card { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: white; z-index: 2000; justify-content: center; align-items: center; text-align: center; flex-direction: column; padding: 20px; }
        #overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.9); z-index:1500; justify-content:center; align-items:center; flex-direction:column; font-weight:bold; }
        .img-preview { width: 100%; height: 150px; object-fit: cover; border-radius: 12px; margin-top: 5px; display: none; border: 1px solid #DDD; }
    </style>
</head>
<body>
    <div id="success-card">
        <h1 style="font-size:60px; color:var(--green);">✓</h1>
        <h2>¡Reporte Guardado!</h2>
        <button class="primary" onclick="location.reload()" style="background:var(--green);">Nueva Visita</button>
    </div>

    <div id="overlay">
        <p>Subiendo Reporte...</p>
    </div>

    <div style="display:flex; justify-content:space-between; padding:5px; font-size:12px; color:gray;">
        <span>ID: {{ session['user'] }}</span>
        <a href="/logout" style="color:red; text-decoration:none;">Salir</a>
    </div>

    <div class="tabs">
        <button class="tab-btn active" id="btn-t1" onclick="switchTab('tab-buscar')">🔍 Buscar</button>
        <button class="tab-btn" id="btn-t2" onclick="switchTab('tab-registro')">📝 Reporte</button>
    </div>

    <div id="tab-buscar" class="content active">
        <input type="text" id="q_puntos" placeholder="Nombre o BMB...">
        <button class="primary" onclick="buscarPuntos()">Consultar</button>
        <div id="res_puntos" style="margin-top:15px;"></div>
    </div>

    <div id="tab-registro" class="content">
        <form id="form-visita">
            <input type="text" id="f_pv" placeholder="Punto de Venta" readonly style="background:#f9f9f9">
            <input type="text" id="f_bmb" placeholder="BMB" readonly style="background:#f9f9f9">
            <select id="f_estado">
                <option value="Visita Exitosa">Visita Exitosa</option>
                <option value="Cerrado">Punto Cerrado</option>
                <option value="Dañado">Equipo Dañado</option>
            </select>
            <input type="file" accept="image/*" capture="camera" onchange="procesarFoto(this, 'p1')">
            <img id="p1" class="img-preview">
            <input type="file" accept="image/*" capture="camera" onchange="procesarFoto(this, 'p2')">
            <img id="p2" class="img-preview">
            <textarea id="f_obs" placeholder="Notas..."></textarea>
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" onclick="enviarVisita()">Guardar Reporte</button>
        </form>
    </div>

    <script>
        function switchTab(id) {
            document.querySelectorAll('.content, .tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(id === 'tab-buscar') document.getElementById('btn-t1').classList.add('active');
            else document.getElementById('btn-t2').classList.add('active');
        }

        function procesarFoto(input, idDestino) {
            const file = input.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function (e) {
                const img = new Image();
                img.src = e.target.result;
                img.onload = function () {
                    const canvas = document.createElement('canvas');
                    const scale = Math.min(800 / img.width, 800 / img.height);
                    canvas.width = img.width * scale;
                    canvas.height = img.height * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    const base64 = canvas.toDataURL('image/jpeg', 0.7);
                    const preview = document.getElementById(idDestino);
                    preview.src = base64;
                    preview.style.display = 'block';
                }
            }
        }

        async function buscarPuntos() {
            const q = document.getElementById('q_puntos').value.trim();
            const resDiv = document.getElementById('res_puntos');
            if(q.length < 2) return;
            resDiv.innerHTML = "Buscando...";
            const r = await fetch('/api/buscar?q=' + q);
            const data = await r.json();
            resDiv.innerHTML = "";
            data.forEach(p => {
                const div = document.createElement('div');
                div.style = "border-bottom:1px solid #eee; padding:10px; cursor:pointer;";
                div.innerHTML = `<b>${p['Punto de Venta']}</b><br><small>${p['BMB']}</small>`;
                div.onclick = () => {
                    document.getElementById('f_pv').value = p['Punto de Venta'];
                    document.getElementById('f_bmb').value = p['BMB'];
                    switchTab('tab-registro');
                };
                resDiv.appendChild(div);
            });
        }

        async function enviarVisita() {
            const f1 = document.getElementById('p1').src;
            const f2 = document.getElementById('p2').src;
            if(!document.getElementById('f_pv').value || f1.length < 100) return alert("Faltan datos");

            document.getElementById('overlay').style.display = 'flex';
            const payload = {
                pv: document.getElementById('f_pv').value,
                bmb: document.getElementById('f_bmb').value,
                estado: document.getElementById('f_estado').value,
                obs: document.getElementById('f_obs').value,
                gps: document.getElementById('f_gps').value,
                f1: f1, f2: f2
            };

            const r = await fetch('/api/guardar_visita', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if(r.ok) {
                document.getElementById('overlay').style.display = 'none';
                document.getElementById('success-card').style.display = 'flex';
            }
        }

        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        }, (err) => { document.getElementById('f_gps').value = "0,0"; });
    </script>
</body>
</html>
"""

# --- RUTAS DE PYTHON ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cedula = request.form.get('cedula').strip()
        # Buscamos solo en la columna 'password'
        user = usuarios_col.find_one({"password": cedula})
        if not user and cedula.isdigit():
            user = usuarios_col.find_one({"password": int(cedula)})
            
        if user:
            session['user'] = cedula
            return redirect('/')
        else:
            return render_template_string(HTML_LOGIN, error=True)
    return render_template_string(HTML_LOGIN)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    return render_template_string(HTML_SISTEMA)

@app.route('/api/buscar')
def api_buscar():
    if 'user' not in session: return jsonify([])
    q = request.args.get('q', '').strip()
    filtro = {"BMB": {"$regex": f"^{q}", "$options": "i"}} if q.isdigit() else {"Punto de Venta": {"$regex": q, "$options": "i"}}
    return jsonify(list(puntos_col.find(filtro, {"_id":0}).limit(10)))

@app.route('/api/guardar_visita', methods=['POST'])
def api_visita():
    if 'user' not in session: return jsonify([]), 401
    d = request.json
    visitas_col.insert_one({
        "usuario": session['user'],
        "pv": d['pv'], "bmb": d['bmb'], "motivo": d['estado'],
        "obs": d['obs'], "gps": d['gps'], "f_bmb": d['f1'], "f_fachada": d['f2'],
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    return jsonify({"s": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
