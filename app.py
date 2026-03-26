from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_ultra_fast_2026"

# --- CONEXIÓN MONGODB ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['NestleDB']
puntos_col = db['puntos_venta']
visitas_col = db['visitas']

HTML_SISTEMA = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nestlé BI - Gestión</title>
    <style>
        :root { --blue: #007AFF; --bg: #F2F2F7; --gray: #8E8E93; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; color: #1C1C1E; }
        
        /* Navegación Tabs */
        .tabs { display: flex; gap: 8px; margin-bottom: 15px; position: sticky; top: 0; background: var(--bg); padding: 5px 0; z-index: 100; }
        .tab-btn { flex: 1; padding: 12px; border: none; border-radius: 12px; background: #E5E5EA; font-weight: 600; cursor: pointer; color: var(--gray); transition: 0.3s; }
        .tab-btn.active { background: var(--blue); color: white; box-shadow: 0 4px 10px rgba(0,122,255,0.3); }
        
        /* Contenedores */
        .content { display: none; background: white; padding: 20px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); animation: fadeIn 0.3s; }
        .content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Inputs y Botones */
        input, select, textarea { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
        button.primary { width: 100%; padding: 16px; background: var(--blue); color: white; border: none; border-radius: 12px; font-weight: bold; font-size: 16px; margin-top: 10px; cursor: pointer; }
        button.primary:disabled { background: #CCC; }

        /* Tabla de resultados */
        .res-card { border-bottom: 1px solid #F2F2F7; padding: 12px 0; cursor: pointer; }
        .res-card:active { background: #F9F9F9; }
        .res-card b { color: var(--blue); display: block; }
        .res-card small { color: var(--gray); }

        .img-preview { width: 100%; height: 180px; object-fit: cover; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid #DDD; }
        .status-msg { text-align: center; color: var(--gray); font-size: 14px; margin-top: 10px; }
    </style>
</head>
<body>

    <div class="tabs">
        <button class="tab-btn active" id="btn-t1" onclick="switchTab('tab-buscar')">🔍 Buscar</button>
        <button class="tab-btn" id="btn-t2" onclick="switchTab('tab-registro')">📝 Reporte</button>
    </div>

    <div id="tab-buscar" class="content active">
        <h3 style="margin-top:0;">Consulta de Puntos</h3>
        <input type="text" id="q_puntos" placeholder="Escribe nombre o número BMB..." onkeyup="if(event.key==='Enter') buscarPuntos()">
        <button class="primary" onclick="buscarPuntos()">Consultar Base de Datos</button>
        <div id="loader" class="status-msg" style="display:none;">Buscando en MongoDB...</div>
        <div id="res_puntos" style="margin-top:15px;"></div>
    </div>

    <div id="tab-registro" class="content">
        <h3 style="margin-top:0;">Nueva Visita</h3>
        <form id="form-visita">
            <input type="text" id="f_pv" placeholder="Punto de Venta" required>
            <input type="text" id="f_bmb" placeholder="Código BMB" required>
            
            <select id="f_estado">
                <option value="Operativa">Máquina Operativa</option>
                <option value="Dañada">Máquina Dañada</option>
                <option value="Retirada">Punto Cerrado / Retirada</option>
            </select>

            <label style="font-size:12px; color:var(--gray)">Foto del Activo (BMB):</label>
            <input type="file" id="img1" accept="image/*" capture="camera" onchange="comprimirImg(this, 'p1')">
            <img id="p1" class="img-preview">

            <label style="font-size:12px; color:var(--gray); margin-top:10px; display:block;">Foto de Fachada:</label>
            <input type="file" id="img2" accept="image/*" capture="camera" onchange="comprimirImg(this, 'p2')">
            <img id="p2" class="img-preview">

            <textarea id="f_obs" placeholder="Observaciones generales..." rows="2"></textarea>
            
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" id="btn-enviar" onclick="enviarVisita()">Guardar en Nestlé BI</button>
        </form>
    </div>

    <script>
        function switchTab(id) {
            document.querySelectorAll('.content, .tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(id === 'tab-buscar') document.getElementById('btn-t1').classList.add('active');
            else document.getElementById('btn-t2').classList.add('active');
        }

        // Obtener GPS apenas carga
        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        }, (err) => console.log("GPS no disponible"));

        // BUSCADOR CON LÓGICA FILTRADA
        async function buscarPuntos() {
            const q = document.getElementById('q_puntos').value.trim();
            if(q.length < 2) return alert("Escribe al menos 2 caracteres");
            
            const loader = document.getElementById('loader');
            const resDiv = document.getElementById('res_puntos');
            
            loader.style.display = 'block';
            resDiv.innerHTML = "";
            
            try {
                const r = await fetch('/api/buscar?q=' + q);
                const data = await r.json();
                loader.style.display = 'none';
                
                if(data.length === 0) {
                    resDiv.innerHTML = "<p class='status-msg'>No se encontró nada.</p>";
                    return;
                }

                data.forEach(p => {
                    const div = document.createElement('div');
                    div.className = 'res-card';
                    div.innerHTML = `<b>${p['Punto de Venta']}</b><small>BMB: ${p['BMB'] || 'Sin código'}</small>`;
                    div.onclick = () => autoLlenar(p['Punto de Venta'], p['BMB']);
                    resDiv.appendChild(div);
                });
            } catch(e) {
                loader.style.display = 'none';
                alert("Error de conexión");
            }
        }

        function autoLlenar(pv, bmb) {
            document.getElementById('f_pv').value = pv;
            document.getElementById('f_bmb').value = bmb;
            switchTab('tab-registro');
        }

        // COMPRESIÓN DE IMAGEN BÁSICA PARA RENDER
        function comprimirImg(input, idImg) {
            const file = input.files[0];
            const reader = new FileReader();
            reader.onload = function(e) {
                const imgTag = document.getElementById(idImg);
                imgTag.src = e.target.result;
                imgTag.style.display = 'block';
            }
            reader.readAsDataURL(file);
        }

        // ENVÍO DE DATOS
        async function enviarVisita() {
            const btn = document.getElementById('btn-enviar');
            const f1 = document.getElementById('p1').src;
            const f2 = document.getElementById('p2').src;

            if(!document.getElementById('f_pv').value || f1 === "" || f2 === "") {
                return alert("Por favor completa el nombre y las 2 fotos.");
            }

            btn.innerText = "Sincronizando con Mongo...";
            btn.disabled = true;

            const payload = {
                pv: document.getElementById('f_pv').value,
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
                    alert("¡Reporte Guardado!");
                    location.reload();
                }
            } catch(e) {
                alert("Error al enviar. Verifica tu internet.");
                btn.disabled = false;
                btn.innerText = "Guardar en Nestlé BI";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_SISTEMA)

@app.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    # LÓGICA SOLICITADA: Si es número busca en BMB, si es texto en Punto de Venta
    if q.isdigit():
        filtro = {"BMB": {"$regex": f"^{q}", "$options": "i"}}
    else:
        filtro = {"Punto de Venta": {"$regex": q, "$options": "i"}}
    
    try:
        res = list(puntos_col.find(filtro, {"_id":0}).limit(15))
        return jsonify(res)
    except:
        return jsonify([]), 500

@app.route('/api/guardar_visita', methods=['POST'])
def api_visita():
    d = request.json
    visitas_col.insert_one({
        "pv": d['pv'],
        "bmb_reportado": d['bmb'],
        "estado": d['estado'],
        "obs": d['obs'],
        "gps": d['gps'],
        "f_bmb": d['f1'],
        "f_fachada": d['f2'],
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    return jsonify({"s": "ok"})

if __name__ == '__main__':
    # Puerto 10000 para Render
    app.run(host='0.0.0.0', port=10000)
