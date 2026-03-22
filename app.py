from flask import Flask, render_template_string, request, redirect, Response
from pymongo import MongoClient
import os, io, csv, base64

app = Flask(__name__)

# Conexión a MongoDB
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
        <title>Control Ejecutivo Nestlé</title>
        <style>
            :root { --ios-blue: #007AFF; --ios-bg: #F2F2F7; }
            body { font-family: -apple-system, system-ui, sans-serif; background: var(--ios-bg); margin: 0; padding-bottom: 50px; }
            .navbar { background: rgba(255,255,255,0.8); backdrop-filter: blur(10px); padding: 15px; position: sticky; top: 0; border-bottom: 1px solid #d1d1d6; display: flex; justify-content: space-between; align-items: center; z-index: 100; }
            .navbar img { height: 30px; }
            .container { padding: 15px; }
            .btn-action { background: var(--ios-blue); color: white; padding: 14px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: 600; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,122,255,0.2); }
            .btn-csv { background: #34C759; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 600; }
            .card { background: white; border-radius: 14px; padding: 0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; }
            th { background: #F9F9F9; padding: 12px; font-size: 11px; color: #8E8E93; text-transform: uppercase; text-align: left; }
            td { padding: 14px; border-top: 1px solid #F2F2F7; font-size: 14px; }
            .thumb { width: 45px; height: 45px; border-radius: 6px; object-fit: cover; background: #eee; }
            .status { font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="navbar">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg">
            <span style="font-weight:700; font-size:17px;">POC Control</span>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg">
        </div>
        
        <div class="container">
            <a href="/formulario" class="btn-action">＋ Registrar Visita</a>
            <a href="/descargar" class="btn-csv">📥 Descargar Reporte Excel (CSV)</a>
            
            <div class="card" style="margin-top:20px;">
                <table>
                    <thead>
                        <tr>
                            <th>Punto de Venta</th>
                            <th>Estado</th>
                            <th>Fotos</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in registros %}
                        <tr>
                            <td><b>{{ r.pv }}</b><br><small style="color:#8E8E93;">{{ r.fecha }}</small></td>
                            <td class="status">
                                {# -1 es positivo y el vacío es el déficit [cite: 2026-03-09] #}
                                {{ '✅' if r.bmb == '-1' else '❌' }}
                            </td>
                            <td>
                                {% if r.f_bmb %}<img src="{{ r.f_bmb }}" class="thumb">{% endif %}
                                {% if r.f_fachada %}<img src="{{ r.f_fachada }}" class="thumb">{% endif %}
                            </td>
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
        # Procesar imágenes a base64
        f_bmb_data = image_to_base64(request.files.get('f_bmb'))
        f_fachada_data = image_to_base64(request.files.get('f_fachada'))
        
        # MES está en formato texto [cite: 2026-02-22]
        # Los días son de Lunes a Sábado [cite: 2026-03-11]
        nueva_visita = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "motivo": request.form.get('motivo'),
            "bmb": request.form.get('bmb'),
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
            .header { text-align:center; margin-bottom: 20px; }
            .form-card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
            label { display: block; font-weight: 600; font-size: 13px; color: #8E8E93; margin-bottom: 6px; margin-left: 4px; }
            input, select, textarea { width: 100%; padding: 14px; margin-bottom: 18px; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; -webkit-appearance: none; }
            .input-file { background: #F2F2F7; border: 1px dashed #007AFF; color: #007AFF; font-weight: 600; }
            .btn-submit { background: #007AFF; color: white; padding: 16px; border: none; border-radius: 14px; width: 100%; font-weight: bold; font-size: 17px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="margin:0; font-size:22px;">Nuevo Reporte</h2>
            <p style="color:#8E8E93; margin:5px 0 0 0;">Complete los datos de la visita</p>
        </div>
        <div class="form-card">
            <form method="POST" enctype="multipart/form-data">
                <label>PUNTO DE VENTA</label>
                <input type="text" name="pv" required placeholder="Nombre de la tienda">
                
                <label>N. DOCUMENTO / ID</label>
                <input type="text" name="n_documento" required placeholder="Cédula o ID PV">
                
                <label>FECHA DE VISITA</label>
                <input type="date" name="fecha" required>
                
                <label>ESTADO BMB</label>
                <select name="bmb">
                    <option value="-1">✅ POSITIVO (-1)</option>
                    <option value="">❌ DÉFICIT (VACÍO)</option>
                </select>

                <label>FOTO BMB (DIRECTO CÁMARA)</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera" class="input-file">
                
                <label>FOTO FACHADA (DIRECTO CÁMARA)</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera" class="input-file">

                <label>MOTIVO / OBSERVACIONES</label>
                <textarea name="motivo" rows="3" placeholder="Detalles adicionales..."></textarea>

                <button type="submit" class="btn-submit">Enviar a Base de Datos</button>
                <a href="/" style="display:block; text-align:center; margin-top:15px; color:#8E8E93; text-decoration:none; font-size:14px;">Cancelar</a>
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
    writer.writerow(['Punto de Venta', 'Documento', 'Fecha', 'Motivo', 'BMB', 'MES'])
    for r in registros:
        writer.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('motivo'), r.get('bmb'), r.get('mes')])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=Reporte_Nestle.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
