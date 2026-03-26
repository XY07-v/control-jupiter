from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
import os, base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_fast_v1"

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
    <title>Nestlé BI - Operaciones</title>
    <style>
        :root { --blue: #007AFF; --bg: #F2F2F7; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; position: sticky; top: 0; background: var(--bg); padding: 10px 0; z-index: 100; }
        .tab-btn { flex: 1; padding: 12px; border: none; border-radius: 10px; background: white; font-weight: 600; cursor: pointer; color: #8e8e93; }
        .tab-btn.active { background: var(--blue); color: white; }
        .content { display: none; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .content.active { display: block; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }
        button.primary { width: 100%; padding: 15px; background: var(--blue); color: white; border: none; border-radius: 10px; font-weight: bold; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { border-bottom: 1px solid #eee; padding: 10px; text-align: left; }
        .img-preview { width: 100px; height: 100px; object-fit: cover; border-radius: 10px; margin-top: 5px; display: none; }
    </style>
</head>
<body>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('tab-buscar')">🔍 Buscar Punto</button>
        <button class="tab-btn" onclick="switchTab('tab-registro')">📝 Nueva Visita</button>
    </div>

    <div id="tab-buscar" class="content active">
        <h3>Consultar Puntos</h3>
        <input type="text" id="q_puntos" placeholder="Nombre del punto o BMB...">
        <button class="primary" onclick="buscarPuntos()">Consultar BD</button>
        <div id="res_puntos"></div>
    </div>

    <div id="tab-registro" class="content">
        <h3>Reporte de Visita</h3>
        <form id="form-visita">
            <input type="text" id="f_pv" placeholder="Nombre del Punto de Venta" required>
            <input type="text" id="f_bmb" placeholder="Código BMB de la máquina" required>
            
            <label><small>Estado de la máquina:</small></label>
            <select id="f_estado">
                <option value="Operativa">Operativa</option>
                <option value="Dañada">Dañada</option>
                <option value="Retirada">Retirada</option>
            </select>

            <label><small>Foto BMB:</small></label>
            <input type="file" id="img1" accept="image/*" capture="camera" onchange="preview(this, 'p1')">
            <img id="p1" class="img-preview">

            <label><small>Foto Fachada:</small></label>
            <input type="file" id="img2" accept="image/*" capture="camera" onchange="preview(this, 'p2')">
            <img id="p2" class="img-preview">

            <textarea id="f_obs" placeholder="Observaciones adicionales..."></textarea>
            
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" id="btn-enviar" onclick="enviarVisita()">Enviar Reporte</button>
        </form>
    </div>

    <script>
        // Cambiar pestañas
        function switchTab(id) {
            document.querySelectorAll('.content, .tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // Obtener GPS al abrir
        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        });

        // Previsualización y reducción de imágenes
        function preview(input, id) {
            const file = input.files[0];
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.getElementById(id);
                img.src = e.target.result;
                img.style.display = 'block';
            }
            reader.readAsDataURL(file);
        }

        // BUSCADOR EN BD
        async function buscarPuntos() {
            const q = document.getElementById('q_puntos').value;
            if(!q) return alert("Escribe algo");
            document.getElementById('res_puntos').innerHTML = "Buscando...";
            
            const r = await fetch('/api/buscar?q=' + q);
            const data = await r.json();
            
            let html = "<table><tr><th>Punto</th><th>BMB</th></tr>";
            data.forEach(p => {
                html += `<tr><td>${p['Punto de Venta']}</td><td>${p['BMB']}</td></tr>`;
            });
            document.getElementById('res_puntos').innerHTML = html + "</table>";
        }

        // ENVIAR A BD (Colección Visitas)
        async function enviarVisita() {
            const btn = document.getElementById('btn-enviar');
            btn.innerText = "Subiendo...";
            btn.disabled = true;

            const datos = {
                pv: document.getElementById('f_pv').value,
                bmb: document.getElementById('f_bmb').value,
                estado: document.getElementById('f_estado').value,
                obs: document.getElementById('f_obs').value,
                gps: document.getElementById('f_gps').value,
                f1: document.getElementById('p1').src,
                f2: document.getElementById('p2').src
            };

            const r = await fetch('/api/guardar_visita', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(datos)
            });

            if(r.ok) {
                alert("Reporte guardado con éxito");
                location.reload();
            } else {
                alert("Error al guardar");
                btn.disabled = false;
                btn.innerText = "Enviar Reporte";
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
    q = request.args.get('q', '')
    filtro = {"$or": [
        {"Punto de Venta": {"$regex": q, "$options": "i"}},
        {"BMB": {"$regex": q, "$options": "i"}}
    ]}
    res = list(puntos_col.find(filtro, {"_id":0}).limit(20))
    return jsonify(res)

@app.route('/api/guardar_visita', methods=['POST'])
def api_visita():
    d = request.json
    visitas_col.insert_one({
        "pv": d['pv'],
        "bmb_reportado": d['bmb'],
        "estado_maquina": d['estado'],
        "observaciones": d['obs'],
        "ubicacion": d['gps'],
        "f_bmb": d['f1'],
        "f_fachada": d['f2'],
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    return jsonify({"s": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
