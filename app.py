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

# --- INTERFAZ DE LOGIN (OPCIONALMENTE OPTIMIZADA) ---
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
        <h3 style="margin-top:0">Panel Nestlé BI</h3>
        <p style="color:gray; font-size:14px;">Ingrese su credencial para continuar</p>
        <form action="/login" method="POST">
            <input type="password" name="cedula" placeholder="Contraseña" required autocomplete="current-password">
            <button type="submit">Entrar</button>
            {% if error %}<p style="color:#FF3B30; font-size:14px; margin-top:10px;">Credencial no válida</p>{% endif %}
        </form>
    </div>
</body>
</html>
"""

# --- INTERFAZ DEL SISTEMA (OPTIMIZADA AL 100% PARA MÓVIL) ---
HTML_SISTEMA = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>Nestlé BI</title>
    <style>
        :root { --blue: #007AFF; --green: #34C759; --bg: #F2F2F7; --gray: #8E8E93; --radius: 14px; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body { 
            font-family: -apple-system, system-ui, sans-serif; 
            background: var(--bg); 
            margin: 0; 
            padding: 10px; 
            color: #1C1C1E;
        }

        /* Tabs fijas y grandes para dedos */
        .tabs { 
            display: flex; gap: 8px; margin-bottom: 15px; 
            position: sticky; top: 0; background: var(--bg); 
            z-index: 100; padding: 10px 0; 
        }
        .tab-btn { 
            flex: 1; padding: 15px; border: none; border-radius: var(--radius); 
            background: #E5E5EA; font-weight: 700; color: var(--gray); font-size: 15px;
        }
        .tab-btn.active { background: var(--blue); color: white; box-shadow: 0 4px 10px rgba(0,122,255,0.2); }

        /* Contenedores con sombra suave */
        .content { 
            display: none; background: white; padding: 20px; 
            border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
            animation: fadeIn 0.2s ease-out;
        }
        .content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

        /* Formulario optimizado: 16px evita el zoom automático en iPhone */
        input, select, textarea { 
            width: 100%; padding: 16px; margin: 10px 0; 
            border: 1px solid #D1D1D6; border-radius: var(--radius); 
            font-size: 16px; background: #FFF; -webkit-appearance: none;
        }
        
        button.primary { 
            width: 100%; padding: 18px; background: var(--blue); 
            color: white; border: none; border-radius: var(--radius); 
            font-weight: bold; font-size: 17px; cursor: pointer; margin-top: 10px;
        }

        /* Imágenes y Previsualización */
        .img-preview { 
            width: 100%; height: auto; max-height: 200px; 
            object-fit: cover; border-radius: 12px; 
            margin: 10px 0; display: none; border: 2px solid #EEE; 
        }

        /* Pantallas de estado */
        #success-card { 
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: white; z-index: 2000; justify-content: center; 
            align-items: center; text-align: center; flex-direction: column; padding: 20px; 
        }
        #overlay { 
            display:none; position:fixed; top:0; left:0; width:100%; height:100%; 
            background:rgba(255,255,255,0.9); z-index:1500; 
            justify-content:center; align-items:center; flex-direction:column; font-weight:bold; 
        }
        
        .punto-item {
            padding: 15px; border-bottom: 1px solid #F2F2F7; cursor: pointer;
        }
        .punto-item:active { background: #F2F2F7; }
    </style>
</head>
<body>
    <div id="success-card">
        <div style="font-size:80px; color:var(--green); margin-bottom:10px;">✓</div>
        <h2 style="margin:0">¡Reporte Enviado!</h2>
        <p style="color:gray">La visita se registró correctamente.</p>
        <button class="primary" onclick="location.reload()" style="background:var(--green); width:80%;">Nueva Visita</button>
    </div>

    <div id="overlay">
        <div class="spinner"></div>
        <p>Subiendo Reporte...</p>
    </div>

    <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 10px; font-size:13px; color:gray;">
        <span>Usuario: <b>{{ session['user'] }}</b></span>
        <a href="/logout" style="color:#FF3B30; text-decoration:none; font-weight:bold;">Cerrar Sesión</a>
    </div>

    <div class="tabs">
        <button class="tab-btn active" id="btn-t1" onclick="switchTab('tab-buscar')">🔍 Buscar</button>
        <button class="tab-btn" id="btn-t2" onclick="switchTab('tab-registro')">📝 Reporte</button>
    </div>

    <div id="tab-buscar" class="content active">
        <input type="text" id="q_puntos" placeholder="Escriba Nombre o BMB..." inputmode="text">
        <button class="primary" onclick="buscarPuntos()">Consultar Punto</button>
        <div id="res_puntos" style="margin-top:15px;"></div>
    </div>

    <div id="tab-registro" class="content">
        <form id="form-visita">
            <label style="font-size:12px; color:gray; margin-left:5px;">Punto Seleccionado:</label>
            <input type="text" id="f_pv" placeholder="Seleccione un punto primero" readonly style="background:#F2F2F7; border:none; color:#555">
            <input type="text" id="f_bmb" placeholder="BMB" readonly style="background:#F2F2F7; border:none; color:#555">
            
            <label style="font-size:12px; color:gray; margin-left:5px;">Estado de Visita:</label>
            <select id="f_estado">
                <option value="Visita Exitosa">Visita Exitosa</option>
                <option value="Punto Cerrado">Punto Cerrado</option>
                <option value="Fuera de Rango">Fuera de Rango</option>
                <option value="Cambio de BMB">Cambio de BMB</option>
                <option value="Maquina Retirada">Maquina Retirada</option>
                <option value="Error App Trade">Error App Trade</option>
            </select>

            <label style="font-size:12px; color:gray; margin-left:5px;">Foto del Equipo (Obligatoria):</label>
            <input type="file" accept="image/*" capture="camera" onchange="procesarFoto(this, 'p1')">
            <img id="p1" class="img-preview">

            <label style="font-size:12px; color:gray; margin-left:5px;">Foto Fachada / Adicional:</label>
            <input type="file" accept="image/*" capture="camera" onchange="procesarFoto(this, 'p2')">
            <img id="p2" class="img-preview">

            <textarea id="f_obs" placeholder="Observaciones adicionales..." rows="3"></textarea>
            
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" id="btn-enviar" onclick="enviarVisita()">Guardar Reporte</button>
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
                    const scale = Math.min(1000 / img.width, 1000 / img.height); // Calidad alta pero ligera
                    canvas.width = img.width * scale;
                    canvas.height = img.height * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    const base64 = canvas.toDataURL('image/jpeg', 0.6); // Compresión 60%
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
            resDiv.innerHTML = "<p style='text-align:center; color:gray;'>Buscando...</p>";
            const r = await fetch('/api/buscar?q=' + q);
            const data = await r.json();
            resDiv.innerHTML = "";
            if(data.length === 0) resDiv.innerHTML = "<p style='text-align:center;'>No se encontraron resultados</p>";
            data.forEach(p => {
                const div = document.createElement('div');
                div.className = "punto-item";
                div.innerHTML = `<strong>${p['Punto de Venta']}</strong><br><small style="color:var(--blue)">BMB: ${p['BMB']}</small>`;
                div.onclick = () => {
                    document.getElementById('f_pv').value = p['Punto de Venta'];
                    document.getElementById('f_bmb').value = p['BMB'];
                    switchTab('tab-registro');
                    window.scrollTo(0,0);
                };
                resDiv.appendChild(div);
            });
        }

        async function enviarVisita() {
            const f1 = document.getElementById('p1').src;
            const f2 = document.getElementById('p2').src;
            const pv = document.getElementById('f_pv').value;

            if(!pv) return alert("Por favor seleccione un punto de venta primero.");
            if(f1.length < 100) return alert("Debe tomar al menos la foto del equipo.");

            document.getElementById('overlay').style.display = 'flex';
            document.getElementById('btn-enviar').disabled = true;

            const payload = {
                pv: pv,
                bmb: document.getElementById('f_bmb').value,
                estado: document.getElementById('f_estado').value,
                obs: document.getElementById('f_obs').value,
                gps: document.getElementById('f_gps').value,
                f1: f1, f2: f2
            };

            try {
                const r = await fetch('/api/guardar_visita', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if(r.ok) {
                    document.getElementById('overlay').style.display = 'none';
                    document.getElementById('success-card').style.display = 'flex';
                } else {
                    alert("Error al guardar el reporte.");
                    document.getElementById('overlay').style.display = 'none';
                    document.getElementById('btn-enviar').disabled = false;
                }
            } catch (e) {
                alert("Error de conexión.");
                document.getElementById('overlay').style.display = 'none';
                document.getElementById('btn-enviar').disabled = false;
            }
        }

        // GPS Automático
        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        }, (err) => { 
            document.getElementById('f_gps').value = "0,0"; 
        }, { enableHighAccuracy: true });
    </script>
</body>
</html>
"""

# --- RUTAS DE PYTHON ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cedula = request.form.get('cedula').strip()
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
    if q.isdigit():
        filtro = {"BMB": {"$regex": f"^{q}", "$options": "i"}}
    else:
        filtro = {"Punto de Venta": {"$regex": q, "$options": "i"}}
    
    # Proyectamos solo lo necesario para ahorrar datos
    puntos = list(puntos_col.find(filtro, {"_id":0, "Punto de Venta":1, "BMB":1}).limit(15))
    return jsonify(puntos)

@app.route('/api/guardar_visita', methods=['POST'])
def api_visita():
    if 'user' not in session: return jsonify({"error": "No auth"}), 401
    d = request.json
    visitas_col.insert_one({
        "usuario": session['user'],
        "pv": d['pv'], 
        "bmb": d['bmb'], 
        "motivo": d['estado'],
        "obs": d['obs'], 
        "gps": d['gps'], 
        "f_bmb": d['f1'], 
        "f_fachada": d['f2'],
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "timestamp": datetime.now()
    })
    return jsonify({"s": "ok"})

if __name__ == '__main__':
    # Puerto ajustable según entorno (Render utiliza el puerto 10000 por defecto)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
