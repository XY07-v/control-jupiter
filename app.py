from flask import Flask, render_template_string, request, redirect, Response
from pymongo import MongoClient
import os, io, csv

app = Flask(__name__)

# Configuración de MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['NestleDB']
coleccion = db['visitas']

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
        <title>POC Nestlé | Manpower</title>
        <style>
            :root { --ios-blue: #007AFF; --ios-bg: #F2F2F7; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--ios-bg); margin: 0; padding: 0; }
            
            .header { background: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #d1d1d6; }
            .header img { height: 40px; }
            
            .container { padding: 15px; }
            .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
            
            h1 { font-size: 22px; font-weight: 700; margin: 0; color: #000; }
            .btn-main { background: var(--ios-blue); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; font-weight: 600; margin-bottom: 15px; }
            .btn-download { background: #34C759; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; display: inline-block; }
            
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
            th { text-align: left; padding: 12px; font-size: 12px; color: #8E8E93; text-transform: uppercase; }
            td { padding: 12px; border-top: 1px solid #F2F2F7; font-size: 14px; }
            .status-ok { color: #34C759; } .status-no { color: #FF3B30; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg" alt="Nestle">
            <h1>Visitas</h1>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg" alt="Manpower">
        </div>
        
        <div class="container">
            <a href="/formulario" class="btn-main">+ Nueva Visita</a>
            <a href="/descargar" class="btn-download">⬇ Descargar Reporte (CSV)</a>
            
            <div class="card" style="margin-top:20px; padding:0;">
                <table>
                    <thead>
                        <tr>
                            <th>PV / Documento</th>
                            <th>Fecha</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in registros %}
                        <tr>
                            <td><b>{{ r.pv }}</b><br><span style="color:#8E8E93; font-size:12px;">{{ r.n_documento }}</span></td>
                            <td>{{ r.fecha }}</td>
                            <td class="{{ 'status-ok' if r.bmb == '-1' else 'status-no' }}">
                                {# -1 es positivo (chulo) [cite: 2026-03-09] #}
                                {{ '✅' if r.bmb == '-1' else '❌' }}
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
        # Los días se cuentan de lunes a sábado [cite: 2026-03-11]
        nueva_visita = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "motivo": request.form.get('motivo'),
            "bmb": request.form.get('bmb'), # -1 positivo, vacío déficit [cite: 2026-03-09]
            "mes": request.form.get('fecha')[:7] # Mes texto extraído de fecha [cite: 2026-02-22]
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
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; padding: 20px; }
            .form-card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            label { display: block; font-weight: 600; font-size: 14px; margin-bottom: 5px; color: #3A3A3C; }
            input, select, textarea { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #D1D1D6; border-radius: 10px; box-sizing: border-box; font-size: 16px; }
            .btn-save { background: #007AFF; color: white; padding: 15px; border: none; border-radius: 12px; width: 100%; font-weight: bold; font-size: 17px; }
            .photo-btn { background: #E5E5EA; color: #007AFF; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-weight: 600; cursor: pointer; display: block; border: 1px dashed #007AFF; }
        </style>
    </head>
    <body>
        <div class="form-card">
            <h2 style="margin-top:0;">Registro Ejecutivo</h2>
            <form method="POST">
                <label>Punto de Venta</label>
                <input type="text" name="pv" required>
                
                <label>N. Documento</label>
                <input type="text" name="n_documento" required>
                
                <label>Fecha Visita</label>
                <input type="date" name="fecha" required>
                
                <label>Estado BMB</label>
                <select name="bmb">
                    <option value="-1">✅ Positivo (-1)</option>
                    <option value="">❌ Déficit (Vacío)</option>
                </select>

                <label>Motivo</label>
                <textarea name="motivo" rows="2"></textarea>

                <label>Foto BMB (Cámara)</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera">
                
                <label>Foto Fachada (Cámara)</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera">

                <button type="submit" class="btn-save">Guardar Registro</button>
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
    # Encabezados solicitados
    writer.writerow(['Punto de Venta', 'N. Documento', 'Fecha Visita', 'Motivo', 'BMB', 'MES'])
    
    for r in registros:
        writer.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('motivo'), r.get('bmb'), r.get('mes')])
    
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=reporte_nestle.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
