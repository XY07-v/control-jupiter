from flask import Flask, render_template_string, request, redirect, Response
from pymongo import MongoClient
import os, io, csv, base64

app = Flask(__name__)

# Configuración MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['NestleDB']
coleccion = db['visitas']

def image_to_base64(file):
    if file and file.filename != '':
        return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"
    return ""

@app.route('/')
def index():
    try:
        registros = list(coleccion.find().sort("_id", -1))
    except:
        registros = []
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Control Nestlé | Manpower</title>
        <style>
            :root { --ios-blue: #007AFF; --ios-bg: #F2F2F7; }
            body { font-family: -apple-system, system-ui, sans-serif; background: var(--ios-bg); margin: 0; }
            .navbar { 
                background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); 
                padding: 15px; position: sticky; top: 0; border-bottom: 1px solid #d1d1d6; 
                display: flex; justify-content: space-between; align-items: center; z-index: 100;
            }
            .navbar img { height: 35px; border-radius: 4px; }
            .container { padding: 15px; }
            .btn-action { background: var(--ios-blue); color: white; padding: 14px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: 600; margin-bottom: 10px; }
            .card { background: white; border-radius: 14px; padding: 0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-top:15px; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; }
            th { background: #F9F9F9; padding: 10px; color: #8E8E93; text-transform: uppercase; text-align: left; font-size: 10px; }
            td { padding: 12px; border-top: 1px solid #F2F2F7; vertical-align: middle; }
            .thumb { width: 50px; height: 50px; border-radius: 8px; object-fit: cover; border: 1px solid #eee; margin-right: 2px; }
            .edit-link { color: var(--ios-blue); font-weight: 600; text-decoration: none; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="navbar">
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAvYAAAFz..." alt="Nestle"> <span style="font-weight:700; font-size:15px; color:#333;">Control Visitas</span>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAb4AAABx..." alt="Manpower">
        </div>
        
        <div class="container">
            <a href="/formulario" class="btn-action">＋ Registrar Nueva Visita</a>
            <a href="/descargar" style="color:var(--ios-blue); font-size:13px; text-decoration:none;">📥 Descargar Reporte Completo</a>
            
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Punto de Venta</th>
                            <th>Fotos</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in registros %}
                        <tr>
                            <td>
                                <b>{{ r.pv }}</b><br>
                                <small style="color:#8E8E93;">{{ r.fecha }} | {{ r.bmb }}</small>
                            </td>
                            <td>
                                {% if r.f_bmb %}<img src="{{ r.f_bmb }}" class="thumb">{% endif %}
                                {% if r.f_fachada %}<img src="{{ r.f_fachada }}" class="thumb">{% endif %}
                            </td>
                            <td><a href="#" class="edit-link">Editar</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        f_bmb_data = image_to_base64(request.files.get('f_bmb'))
        f_fachada_data = image_to_base64(request.files.get('f_fachada'))
        
        nueva_visita = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "motivo": request.form.get('motivo'),
            "bmb": request.form.get('bmb'),
            "ubicacion": request.form.get('ubicacion'),
            "f_bmb": f_bmb_data,
            "f_fachada": f_fachada_data,
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
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; margin: 0; padding: 20px; }
            .form-card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
            label { display: block; font-weight: 600; font-size: 12px; color: #8E8E93; margin-bottom: 6px; text-transform: uppercase; }
            input, select, textarea { width: 100%; padding: 14px; margin-bottom: 18px; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
            
            /* Estilo Botones Motivo */
            .motivo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
            .motivo-item { position: relative; }
            .motivo-item input { position: absolute; opacity: 0; width: 0; height: 0; }
            .motivo-item label { 
                background: white; border: 1px solid #D1D1D6; color: #333; padding: 12px 5px; 
                border-radius: 10px; text-align: center; font-size: 12px; cursor: pointer; display: block; text-transform: none;
            }
            .motivo-item input:checked + label { background: #007AFF; color: white; border-color: #007AFF; }

            .btn-gps { background: #5856D6; color: white; border: none; padding: 12px; border-radius: 10px; width: 100%; margin-bottom: 15px; font-weight: 600; }
            .btn-submit { background: #34C759; color: white; padding: 16px; border: none; border-radius: 14px; width: 100%; font-weight: bold; font-size: 17px; }
        </style>
        <script>
            function getUbicacion() {
                const btn = document.getElementById('gps-btn');
                if (navigator.geolocation) {
                    btn.innerText = "Localizando...";
                    navigator.geolocation.getCurrentPosition(function(position) {
                        document.getElementById('ubicacion').value = position.coords.latitude + ", " + position.coords.longitude;
                        btn.innerText = "📍 Ubicación Capturada";
                        btn.style.background = "#34C759";
                    });
                }
            }
        </script>
    </head>
    <body>
        <div class="form-card">
            <form method="POST" enctype="multipart/form-data">
                <label>Punto de Venta</label>
                <input type="text" name="pv" required placeholder="Nombre del PV">
                
                <label>N. Documento</label>
                <input type="text" name="n_documento" required placeholder="ID o Cédula">
                
                <label>Fecha Visita</label>
                <input type="date" name="fecha" required>

                <label>BMB (Texto Libre)</label>
                <input type="text" name="bmb" required placeholder="Anotación BMB">

                <label>Ubicación GPS</label>
                <button type="button" id="gps-btn" class="btn-gps" onclick="getUbicacion()">Obtener Coordenadas Actuales</button>
                <input type="hidden" name="ubicacion" id="ubicacion" required>

                <label>Motivo de la Visita</label>
                <div class="motivo-grid">
                    <div class="motivo-item">
                        <input type="radio" name="motivo" id="m1" value="Maquina Retirada" required>
                        <label for="m1">Máquina Retirada</label>
                    </div>
                    <div class="motivo-item">
                        <input type="radio" name="motivo" id="m2" value="Fuera de Rango">
                        <label for="m2">Fuera de Rango</label>
                    </div>
                    <div class="motivo-item">
                        <input type="radio" name="motivo" id="m3" value="No sale en Trade">
                        <label for="m3">No sale en Trade</label>
                    </div>
                    <div class="motivo-item">
                        <input type="radio" name="motivo" id="m4" value="Punto Cerrado">
                        <label for="m4">Punto Cerrado</label>
                    </div>
                </div>

                <label>Foto BMB (Cámara)</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera" required>
                
                <label>Foto Fachada (Cámara)</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera" required>

                <button type="submit" class="btn-submit">FINALIZAR REPORTE</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/descargar')
def descargar():
    registros = list(coleccion.find())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Punto de Venta', 'Documento', 'Fecha', 'Motivo', 'BMB', 'Ubicación'])
    for r in registros:
        writer.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('motivo'), r.get('bmb'), r.get('ubicacion')])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=Reporte_Ejecutivo.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
