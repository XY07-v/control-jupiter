from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_final_2026"

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
    <title>Nestlé BI - Reportes</title>
    <style>
        :root { --blue: #007AFF; --green: #34C759; --bg: #F2F2F7; --gray: #8E8E93; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; color: #1C1C1E; }
        
        /* Navegación Tabs */
        .tabs { display: flex; gap: 8px; margin-bottom: 15px; position: sticky; top: 0; background: var(--bg); padding: 5px 0; z-index: 100; }
        .tab-btn { flex: 1; padding: 12px; border: none; border-radius: 12px; background: #E5E5EA; font-weight: 600; cursor: pointer; color: var(--gray); }
        .tab-btn.active { background: var(--blue); color: white; box-shadow: 0 4px 10px rgba(0,122,255,0.3); }
        
        /* Contenedores */
        .content { display: none; background: white; padding: 20px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .content.active { display: block; }

        /* Formulario */
        input, select, textarea { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
        button.primary { width: 100%; padding: 16px; background: var(--blue); color: white; border: none; border-radius: 12px; font-weight: bold; font-size: 16px; margin-top: 10px; cursor: pointer; transition: 0.3s; }
        button.primary:disabled { background: var(--gray); cursor: not-allowed; }
        
        .res-card { border-bottom: 1px solid #F2F2F7; padding: 12px 5px; cursor: pointer; }
        .res-card b { color: var(--blue); display: block; }
        
        .img-preview { width: 100%; height: 150px; object-fit: cover; border-radius: 12px; margin-top: 5px; display: none; border: 1px solid #DDD; }
        .label-mini { font-size: 12px; color: var(--gray); margin-top: 10px; display: block; font-weight: 600; }
        
        /* Letrero de Carga */
        #overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.8); z-index:1000; justify-content:center; align-items:center; flex-direction:column; }
    </style>
</head>
<body>

    <div id="overlay">
        <div style="border: 4px solid #f3f3f3; border-top: 4px solid var(--blue); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
        <p>Guardando Reporte...</p>
    </div>

    <div class="tabs">
        <button class="tab-btn active" id="btn-t1" onclick="switchTab('tab-buscar')">🔍 Buscar</button>
        <button class="tab-btn" id="btn-t2" onclick="switchTab('tab-registro')">📝 Reporte</button>
    </div>

    <div id="tab-buscar" class="content active">
        <h3 style="margin-top:0;">Consulta de Puntos</h3>
        <input type="text" id="q_puntos" placeholder="Nombre o BMB..." onkeyup="if(event.key==='Enter') buscarPuntos()">
        <button class="primary" onclick="buscarPuntos()">Buscar</button>
        <div id="res_puntos" style="margin-top:15px;"></div>
    </div>

    <div id="tab-registro" class="content">
        <h3 style="margin-top:0;">Nueva Visita</h3>
        <form id="form-visita">
            <input type="text" id="f_pv" placeholder="Punto de Venta" required>
            <input type="text" id="f_bmb" placeholder="Código BMB" required>
            
            <label class="label-mini">Motivo de Visita:</label>
            <select id="f_estado">
                <option value="Visita Exitosa">Visita Exitosa</option>
                <option value="Cerrado">Punto Cerrado</option>
                <option value="Dañado">Equipo Dañado</option>
                <option value="No permitido">Acceso No Permitido</option>
                <option value="Otro">Otro Motivo</option>
            </select>

            <label class="label-mini">Foto Activo (BMB):</label>
            <input type="file" id="img1" accept="image/*" capture="camera" onchange="preview(this, 'p1')">
            <img id="p1" class="img-preview">

            <label class="label-mini">Foto Fachada:</label>
            <input type="file" id="img2" accept="image/*" capture="camera" onchange="preview(this, 'p2')">
            <img id="p2" class="img-preview">

            <textarea id="f_obs" placeholder="Observaciones..." rows="2"></textarea>
            
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" id="btn-enviar" onclick="enviarVisita()">Guardar en Base de Datos</button>
        </form>
    </div>

    <script>
        function switchTab(id) {
            document.querySelectorAll('.content, .tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(id === 'tab-buscar') document.getElementById('btn-t1').classList.add('active');
            else document.getElementById('btn-t2').classList.add('active');
        }

        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        });

        async function buscarPuntos() {
            const q = document.getElementById('q_puntos').value.trim();
            const resDiv = document.getElementById('res_puntos');
            if(q.length < 2) return;
            
            resDiv.innerHTML = "<small>Buscando...</small>";
            const r = await fetch('/api/buscar?q=' + q);
            const data = await r.json();
            
            resDiv.innerHTML = "";
            data.forEach(p => {
                const div = document.createElement('div');
                div.className = 'res-card';
                div.innerHTML = `<b>${p['Punto de Venta']}</b><small>BMB: ${p['BMB'] || '---'}</small>`;
                div.onclick = () => {
                    document.getElementById('f_pv').value = p['Punto de Venta'];
                    document.getElementById('f_bmb').value = p['BMB'];
                    switchTab('tab-registro');
                };
                resDiv.appendChild(div);
            });
        }

        function preview(input, idImg) {
            const file = input.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.getElementById(idImg);
                img.src = e.target.result;
                img.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }

        async function enviarVisita() {
            const f1 = document.getElementById('p1').src;
            const f2 = document.getElementById('p2').src;
            const pv = document.getElementById('f_pv').value;

            if(!pv || !f1 || !f2) return alert("Completa el nombre y las 2 fotos.");

            document.getElementById('overlay').style.display = 'flex';
            document.getElementById('btn-enviar').disabled = true;

            const payload = {
                pv: pv, bmb: document.getElementById('f_bmb').value,
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
                    alert("✅ REGISTRO EXITOSO: Los datos se guardaron correctamente.");
                    // REINICIAR FORMULARIO
                    document.getElementById('form-visita').reset();
                    document.getElementById('p1').style.display = 'none';
                    document.getElementById('p1').src = '';
                    document.getElementById('p2').style.display = 'none';
                    document.getElementById('p2').src = '';
                    switchTab('tab-buscar');
                }
            } catch(e) {
                alert("Error al conectar con el servidor.");
            } finally {
                document.getElementById('overlay').style.display = 'none';
                document.getElementById('btn-enviar').disabled = false;
            }
        }
    </script>
    <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_SISTEMA)

@app.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    filtro = {"BMB": {"$regex": f"^{q}", "$options": "i"}} if q.isdigit() else {"Punto de Venta": {"$regex": q, "$options": "i"}}
    try:
        return jsonify(list(puntos_col.find(filtro, {"_id":0}).limit(10)))
    except: return jsonify([])

@app.route('/api/guardar_visita', methods=['POST'])
def api_visita():
    d = request.json
    visitas_col.insert_one({
        "pv": d['pv'], "bmb": d['bmb'], "motivo": d['estado'],
        "obs": d['obs'], "gps": d['gps'], "f_bmb": d['f1'], "f_fachada": d['f2'],
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    return jsonify({"s": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
