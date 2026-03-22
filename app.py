from flask import Flask, render_template_string, request, redirect, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, io, csv, base64

app = Flask(__name__)

# Conexión MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def image_to_base64(file):
    if file and file.filename != '':
        return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"
    return None

@app.route('/')
def index():
    registros = list(coleccion.find().sort("_id", -1))
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; }
            .header-logos { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
            .header-logos img { height: 30px; object-fit: contain; }
            .btn-main { background: var(--ios-blue); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; font-weight: 600; margin-bottom: 10px; }
            
            /* Tabla Compacta */
            .list-container { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .row { display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid #E5E5EA; }
            .info { flex-grow: 1; min-width: 0; }
            .title { font-size: 14px; font-weight: bold; margin: 0; display: flex; align-items: center; gap: 5px; }
            .meta { font-size: 11px; color: #8E8E93; margin-top: 2px; }
            .bmb-tag { font-size: 10px; background: #E5E5EA; padding: 2px 6px; border-radius: 4px; }
            
            .photo-box { display: flex; gap: 4px; margin-right: 10px; }
            .thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: #eee; border: 0.5px solid #ddd; }
            .btn-edit { color: var(--ios-blue); font-size: 13px; text-decoration: none; font-weight: 500; padding: 5px; }
        </style>
    </head>
    <body>
        <div class="header-logos">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg" alt="Nestle">
            <span style="font-weight:700; color:#555">Control Visitas</span>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg" alt="Manpower">
        </div>

        <a href="/formulario" class="btn-main">+ Registrar Nueva Visita</a>

        <div class="list-container">
            {% for r in registros %}
            <div class="row">
                <div class="photo-box">
                    {% if r.f_bmb %}<img src="{{ r.f_bmb }}" class="thumb">{% endif %}
                    {% if r.f_fachada %}<img src="{{ r.f_fachada }}" class="thumb">{% endif %}
                </div>
                <div class="info">
                    <div class="title">
                        {{ r.pv }} 
                        <span class="bmb-tag">{{ '✅' if r.bmb == '-1' else '❌ ' + (r.bmb if r.bmb else 'Vacío') }}</span>
                    </div>
                    <div class="meta">{{ r.fecha }} | ID: {{ r.n_documento }}</div>
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
        # (Lógica de guardado igual a la anterior con todos los campos obligatorios)
        pass
    return render_template_string("")

# RUTA PARA EDITAR QUE YA FUNCIONA
@app.route('/editar/<id>', methods=['GET', 'POST'])
def editar(id):
    registro = coleccion.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        updates = {
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo')
        }
        # Solo actualizar fotos si se suben nuevas
        f_bmb = image_to_base64(request.files.get('f_bmb'))
        if f_bmb: updates["f_bmb"] = f_bmb
        
        coleccion.update_one({"_id": ObjectId(id)}, {"$set": updates})
        return redirect('/')
    
    return render_template_string("""
    <h1>Editar Registro: {{ r.pv }}</h1>
    <form method="POST" enctype="multipart/form-data">
        <input type="text" name="pv" value="{{ r.pv }}" required>
        <input type="text" name="bmb" value="{{ r.bmb }}">
        <button type="submit">Guardar Cambios</button>
    </form>
    """, r=registro)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
