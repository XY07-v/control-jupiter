from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- CONFIGURACIÓN DE MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

@app.route('/')
def index():
    # Los días se cuentan de lunes a sábado; domingos y festivos no se cuentan [cite: 2026-03-11]
    # Traemos los datos de la base de datos en la nube
    registros = list(coleccion.find().sort("_id", -1))
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Control Nestlé - POC</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f0f2f5; color: #333; }
            .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
            h1 { color: #0056a0; border-bottom: 2px solid #eee; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #0056a0; color: white; padding: 12px; text-align: left; font-size: 14px; }
            td { border-bottom: 1px solid #eee; padding: 12px; font-size: 13px; }
            .btn { background: #0056a0; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; transition: 0.3s; }
            .btn:hover { background: #003d73; }
            .status-pos { color: #27ae60; font-weight: bold; background: #e8f5e9; padding: 4px 8px; border-radius: 4px; }
            .status-neg { color: #e74c3c; font-weight: bold; background: #ffebee; padding: 4px 8px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visitas POC Nestlé</h1>
            <div style="margin-bottom: 25px;">
                <a href="/formulario" class="btn">+ Nuevo Registro de Visita</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>ID PV</th>
                        <th>Punto de Venta</th>
                        <th>Nombre Responsable</th>
                        <th>MES</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in registros %}
                    <tr>
                        <td>{{ r.id_pv }}</td>
                        <td>{{ r.pv }}</td>
                        <td>{{ r.nombre }}</td>
                        <td>{{ r.mes }}</td>
                        <td>
                            {# El -1 es positivo (chulo) y el vacío es el déficit (x) [cite: 2026-03-09] #}
                            {% if r.estado == "-1" %}
                                <span class="status-pos">✅ POSITIVO</span>
                            {% else %}
                                <span class="status-neg">❌ DÉFICIT</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # La columna MES está en formato texto y contiene el nombre de cada mes [cite: 2026-02-22]
        nueva_visita = {
            "id_pv": request.form.get('id_pv'),
            "pv": request.form.get('pv'),
            "nombre": request.form.get('nombre'),
            "mes": request.form.get('mes'),
            "estado": request.form.get('estado'), # Guardamos -1 o vacío según tu regla [cite: 2026-03-09]
            "motivo": request.form.get('motivo')
        }
        coleccion.insert_one(nueva_visita)
        return redirect('/')
    
    return render_template_string("""
    <div style="max-width:450px; margin: 50px auto; background: white; padding: 35px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); font-family: sans-serif;">
        <h2 style="text-align: center; color: #0056a0; margin-bottom: 25px;">Registrar Visita</h2>
        <form method="POST">
            <label style="display:block; margin-bottom: 5px; font-weight: bold; font-size: 13px;">ID Punto de Venta:</label>
            <input type="text" name="id_pv" required style="width:100%; margin-bottom:15px; padding:12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box;">
            
            <label style="display:block; margin-bottom: 5px; font-weight: bold; font-size: 13px;">Nombre del Establecimiento:</label>
            <input type="text" name="pv" required style="width:100%; margin-bottom:15px; padding:12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box;">
            
            <label style="display:block; margin-bottom: 5px; font-weight: bold; font-size: 13px;">Nombre Completo:</label>
            <input type="text" name="nombre" style="width:100%; margin-bottom:15px; padding:12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box;">
            
            <label style="display:block; margin-bottom: 5px; font-weight: bold; font-size: 13px;">MES (Texto):</label>
            <input type="text" name="mes" placeholder="Ej: MARZO" required style="width:100%; margin-bottom:15px; padding:12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box;">
            
            <label style="display:block; margin-bottom: 5px; font-weight: bold; font-size: 13px;">Estado de la Visita:</label>
            <select name="estado" style="width:100%; margin-bottom:20px; padding:12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; background: #f9f9f9;">
                <option value="-1">✅ Positivo (-1)</option>
                <option value="">❌ Déficit (Vacío)</option>
            </select>
            
            <button type="submit" style="width:100%; background:#27ae60; color:white; padding:15px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size: 16px; margin-bottom: 10px;">GUARDAR EN LA NUBE</button>
            <a href="/" style="display:block; text-align:center; color: #888; text-decoration: none; font-size: 14px;">Volver al listado</a>
        </form>
    </div>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
