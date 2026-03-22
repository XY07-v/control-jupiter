from flask import Flask, render_template_string, request, redirect, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, io, csv, base64

app = Flask(__name__)

# Conexión optimizada
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client['NestleDB']
coleccion = db['visitas']

def image_to_base64(file):
    if file and file.filename != '':
        return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"
    return None

@app.route('/')
def index():
    try:
        registros = list(coleccion.find().sort("_id", -1).limit(50)) # Limitamos para rapidez
    except:
        registros = []
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Nestlé Manpower</title>
        <style>
            :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; }
            .header { display: flex; justify-content: space-between; padding: 10px; align-items: center; }
            .header img { height: 25px; }
            .btn-new { background: var(--ios-blue); color: white; padding: 12px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: 600; margin: 10px 0; }
            
            /* Lista Compacta Ejecutiva */
            .card-list { background: white; border-radius: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .item { display: flex; align-items: center; padding: 10px; border-bottom: 0.5px solid #C6C6C8; }
            .img-prev { display: flex; gap: 4px; margin-right: 12px; }
            .img-prev img { width: 45px; height: 45px; border-radius: 8px; object-fit: cover; background: #eee; }
            .content { flex: 1; min-width: 0; }
            .title { font-size: 14px; font-weight: 700; color: #1C1C1E; margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .subtitle { font-size: 12px; color: #8E8E93; }
            .status-badge { font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 5px; background: #F2F2F7; margin-left: 5px; }
            .btn-edit { color: var(--ios-blue); font-size: 13px; font-weight: 600; text-decoration: none; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg">
            <span style="font-size:14px; font-weight:700;">Control Visitas</span>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg">
        </div>

        <a href="/formulario" class="btn-new">＋ NUEVO REGISTRO</a>

        <div class="card-list">
            {% for r in registros %}
            <div class="item">
                <div class="img-prev">
                    {% if r.f_bmb %}<img src="{{ r.f_bmb }}">{% endif %}
                    {% if r.f_fachada %}<img src="{{ r.f_fachada }}">{% endif %}
                </div>
                <div class="content">
                    <div class="title">
                        {{ r.pv }} 
                        <span class="status-badge">{{ '✅' if r.bmb == '-1' else '❌' }}</span>
                    </div>
                    <div class="subtitle">{{ r.fecha }} | {{ r.bmb if r.bmb != '-1' else 'Positivo' }}</div>
                </div>
                <a href="/editar/{{ r._id }}" class="btn-edit">Editar</a>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        f_bmb = image_to_base64(request.files.get('f_bmb'))
        f_fachada = image_to_base64(request.files.get('f_fachada'))
        
        # MES en formato texto y días de L-S [cite: 2026-02-22, 2026-03-11]
        nueva_visita = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "motivo": request.form.get('motivo'),
            "bmb": request.form.get('bmb'),
            "ubicacion": request.form.get('ubicacion'),
            "f_bmb": f_bmb,
            "f_fachada": f_fachada,
            "mes": request.form.get('fecha')[:7] 
        }
        coleccion.insert_one(nueva_visita)
        return redirect('/')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <style>
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; padding: 15px; margin: 0; }
            .card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
            label { display: block; font-size: 11px; font-weight: 700; color: #8E8E93; margin: 10px 0 5px 0; text-transform: uppercase; }
            input, select { width: 100%; padding: 12px; border: 1px solid #D1D1D6; border-radius: 10px; font-size: 15px; box-sizing: border-box; }
            .btn-gps { background: #5856D6; color: white; border: none; padding: 10px; border-radius: 8px; width: 100%; font-weight: 600; margin-top: 5px; }
            .grid-motivo { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
            .opt-motivo { border: 1px solid #D1D1D6; padding: 10px; border-radius: 8px; text-align: center; font-size: 12px; }
            input[type="radio"]:checked + label { background: #007AFF; color: white; border-color: #007AFF; }
            .btn-save { background: #34C759; color: white; border: none; width: 100%; padding: 15px; border-radius: 12px; font-weight: 700; font-size: 16px; margin-top: 20px; }
        </style>
        <script>
            function getLoc() {
                navigator.geolocation.getCurrentPosition(p => {
                    document.getElementById('ub').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps-btn').innerText = "📍 UBICACIÓN LISTA";
                });
            }
        </script>
    </head>
    <body>
        <div class="card">
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input type="text" name="pv" required>
                <label>N. Documento</label>
                <input type="text" name="n_documento" required>
                <label>Fecha</label>
                <input type="date" name="fecha" required>
                <label>BMB (Formato Libre)</label>
                <input type="text" name="bmb" required>
                
                <label>Ubicación</label>
                <button type="button" id="gps-btn" class="btn-gps" onclick="getLoc()">CAPTURAR GPS</button>
                <input type="hidden" name="ubicacion" id="ub" required>

                <label>Motivo</label>
                <select name="motivo" required>
                    <option value="Maquina Retirada">Máquina Retirada</option>
                    <option value="Fuera de Rango">Fuera de Rango</option>
                    <option value="No sale en Trade">No sale en Trade</option>
                    <option value="Punto Cerrado">Punto Cerrado</option>
                </select>

                <label>Foto BMB</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera" required>
                <label>Foto Fachada</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera" required>

                <button type="submit" class="btn-save">ENVIAR REPORTE</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    obj_id = ObjectId(id)
    r = coleccion.find_one({"_id": obj_id})
    if request.method == 'POST':
        updates = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo')
        }
        # Actualización lógica
        coleccion.update_one({"_id": obj_id}, {"$set": updates})
        return redirect('/')
    
    return f"<h3>Editando: {r['pv']}</h3><form method='POST'>PV: <input name='pv' value='{r['pv']}'><button>Guardar</button></form>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
