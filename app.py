from flask import Flask, render_template_string, request, redirect
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- CONEXIÓN A MONGODB ---
# Usando tu contraseña: control-jupiter1234
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

@app.route('/')
def index():
    # Se obtienen los registros de la base de datos
    registros = list(coleccion.find().sort("_id", -1))
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Control Nestlé</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f4f7f6; }
            .container { max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #0056a0; color: white; padding: 10px; }
            td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            .btn { background: #27ae60; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visitas POC Nestlé</h1>
            <a href="/formulario" class="btn">+ Nuevo Registro</a>
            <table>
                <tr>
                    <th>ID PV</th><th>Punto de Venta</th><th>Nombre</th><th>MES</th><th>Estado</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r.id_pv }}</td>
                    <td>{{ r.pv }}</td>
                    <td>{{ r.nombre }}</td>
                    <td>{{ r.mes }}</td>
                    <td>
                        {# El -1 es positivo y el vacío es déficit [cite: 2026-03-09] #}
                        {{ '✅' if r.estado == '-1' else '❌' }}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Los meses se guardan como texto [cite: 2026-02-22]
        nueva_visita = {
            "id_pv": request.form.get('id_pv'),
            "pv": request.form.get('pv'),
            "nombre": request.form.get('nombre'),
            "mes": request.form.get('mes'),
            "estado": request.form.get('estado')
        }
        coleccion.insert_one(nueva_visita)
        return redirect('/')
    
    return render_template_string("""
    <div style="max-width:400px; margin:auto; background:white; padding:25px; border-radius:10px; font-family:sans-serif;">
        <h2>Nueva Visita</h2>
        <form method="POST">
            <input type="text" name="id_pv" placeholder="ID PV" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="mes" placeholder="Mes (Ej: MARZO)" required style="width:100%; margin-bottom:10px; padding:10px;">
            <select name="estado" style="width:100%; margin-bottom:10px; padding:10px;">
                <option value="-1">Positivo (-1 ✅)</option>
                <option value="">Déficit (Vacío ❌)</option>
            </select>
            <button type="submit" style="width:100%; background:green; color:white; padding:12px; border:none; border-radius:5px; cursor:pointer;">GUARDAR</button>
        </form>
    </div>
    """)

if __name__ == '__main__':
    # Render asigna el puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
