from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64

app = Flask(__name__)

# Conexión Robusta
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def image_to_base64(file):
    if file and file.filename != '':
        return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"
    return None

@app.route('/')
def index():
    # Ordenar por fecha de la más reciente a la más antigua
    registros = list(coleccion.find().sort("fecha", -1))
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
            
            /* Header con Logos Corregidos */
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 10px; border-radius: 12px; }
            .header img { height: 28px; width: auto; max-width: 100px; object-fit: contain; }
            
            .btn-new { background: var(--ios-blue); color: white; padding: 14px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: 700; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,122,255,0.3); }
            
            /* Lista Compacta */
            .list { background: white; border-radius: 14px; overflow: hidden; }
            .item { display: flex; align-items: center; padding: 12px; border-bottom: 0.5px solid #C6C6C8; cursor: pointer; transition: background 0.2s; }
            .item:active { background: #E5E5EA; }
            .thumb-group { display: flex; gap: 4px; margin-right: 12px; }
            .thumb { width: 45px; height: 45px; border-radius: 8px; object-fit: cover; background: #f0f0f0; }
            .info { flex: 1; }
            .info h4 { margin: 0; font-size: 15px; color: #1C1C1E; }
            .info p { margin: 2px 0 0; font-size: 12px; color: #8E8E93; }

            /* Modal de Detalle Dinámico */
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; }
            .modal-content { background: white; width: 100%; max-width: 400px; border-radius: 20px; padding: 20px; position: relative; max-height: 90vh; overflow-y: auto; }
            .close-modal { position: absolute; top: 15px; right: 15px; font-size: 24px; font-weight: bold; color: #8E8E93; border: none; background: none; }
            .detail-img { width: 100%; border-radius: 12px; margin-top: 10px; }
            .detail-label { font-size: 11px; font-weight: 700; color: var(--ios-blue); text-transform: uppercase; margin-top: 15px; }
            .detail-val { font-size: 16px; color: #1C1C1E; margin-bottom: 8px; border-bottom: 0.5px solid #eee; padding-bottom: 4px; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg">
            <span style="font-weight:700; color:#444">VISITAS</span>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg">
        </div>

        <a href="/formulario" class="btn-new">＋ NUEVA VISITA</a>

        <div class="list">
            {% for r in registros %}
            <div class="item" onclick="verDetalle({{ r|tojson }})">
                <div class="thumb-group">
                    {% if r.f_bmb %}<img src="{{ r.f_bmb }}" class="thumb">{% endif %}
                </div>
                <div class="info">
                    <h4>{{ r.pv }}</h4>
                    <p>{{ r.fecha }} | {{ r.n_documento }}</p>
                </div>
            </div>
            {% endfor %}
        </div>

        <div id="detalleModal" class="modal" onclick="this.style.display='none'">
            <div class="modal-content" onclick="event.stopPropagation()">
                <button class="close-modal" onclick="document.getElementById('detalleModal').style.display='none'">&times;</button>
                <div id="modalBody"></div>
            </div>
        </div>

        <script>
            function verDetalle(data) {
                const body = document.getElementById('modalBody');
                body.innerHTML = `
                    <h2 style="margin-top:0">${data.pv}</h2>
                    <div class="detail-label">Fecha de Visita</div>
                    <div class="detail-val">${data.fecha}</div>
                    <div class="detail-label">Documento</div>
                    <div class="detail-val">${data.n_documento}</div>
                    <div class="detail-label">Estado BMB</div>
                    <div class="detail-val">${data.bmb === '-1' ? 'Positivo' : data.bmb}</div>
                    <div class="detail-label">Motivo</div>
                    <div class="detail-val">${data.motivo}</div>
                    <div class="detail-label">Evidencia Fotográfica</div>
                    <img src="${data.f_bmb}" class="detail-img">
                    <img src="${data.f_fachada}" class="detail-img">
                `;
                document.getElementById('detalleModal').style.display = 'flex';
            }
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Lógica de guardado...
        f_bmb = image_to_base64(request.files.get('f_bmb'))
        f_fachada = image_to_base64(request.files.get('f_fachada'))
        
        # Guardar con formato de mes texto [cite: 2026-02-22]
        nueva_visita = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "motivo": request.form.get('motivo'),
            "bmb": request.form.get('bmb'),
            "f_bmb": f_bmb,
            "f_fachada": f_fachada
        }
        coleccion.insert_one(nueva_visita)
        return redirect('/')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; padding: 20px; }
            .card { background: white; border-radius: 18px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
            .btn-back { display: inline-block; color: #8E8E93; text-decoration: none; margin-bottom: 20px; font-weight: 500; }
            label { display: block; font-size: 12px; font-weight: 700; color: #8E8E93; margin-top: 15px; }
            input, select { width: 100%; padding: 12px; border: 1px solid #D1D1D6; border-radius: 10px; margin-top: 5px; box-sizing: border-box; }
            .btn-save { background: #34C759; color: white; border: none; width: 100%; padding: 16px; border-radius: 14px; font-weight: 700; margin-top: 25px; }
        </style>
    </head>
    <body>
        <a href="/" class="btn-back">✕ Cancelar y Salir</a>
        <div class="card">
            <h3 style="margin:0 0 20px 0">Nuevo Reporte</h3>
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input type="text" name="pv" required>
                <label>N. Documento</label>
                <input type="text" name="n_documento" required>
                <label>Fecha</label>
                <input type="date" name="fecha" required>
                <label>BMB (Escribe -1 si es positivo)</label>
                <input type="text" name="bmb" required>
                <label>Motivo</label>
                <select name="motivo">
                    <option>Maquina Retirada</option>
                    <option>Fuera de Rango</option>
                    <option>No sale en Trade</option>
                </select>
                <label>Foto BMB</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera">
                <label>Foto Fachada</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera">
                <button type="submit" class="btn-save">GUARDAR REGISTRO</button>
            </form>
        </div>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
