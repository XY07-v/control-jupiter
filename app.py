from flask import Flask, render_template_string, request, redirect, jsonify, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, gc, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_ultra_light_v1"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']

# --- CSS ESTILO IOS (LIGERO) ---
CSS = """
<style>
    :root { --blue: #007AFF; --bg: #F2F2F7; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: #1c1c1e; }
    .card { background: white; border-radius: 15px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .btn { width: 100%; padding: 12px; border-radius: 10px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; transition: 0.2s; }
    .btn-blue { background: var(--blue); color: white; }
    .btn-white { background: white; color: var(--blue); border: 1px solid var(--blue); }
    .btn-red { background: #FF3B30; color: white; }
    .nav-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
    .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); z-index: 1000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 500px; border-radius: 20px; padding: 20px; max-height: 80vh; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
    img { width: 100%; border-radius: 10px; margin-top: 10px; border: 1px solid #ddd; }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body>
        <h2>Nestlé BI - Consola</h2>
        <p>Hola, <b>{session.get('user_name')}</b></p>
        
        <div class="nav-grid">
            <button class="btn btn-blue" onclick="cargarColeccion('visitas')">Ver Visitas</button>
            <button class="btn btn-blue" onclick="cargarColeccion('puntos')">Ver Puntos</button>
            <button class="btn btn-white" onclick="cargarColeccion('usuarios')">Ver Usuarios</button>
            <a href="/formulario" class="btn btn-white">Nuevo Reporte</a>
        </div>

        <div id="tabla_contenedor">
            <p style="text-align:center; color:gray;">Selecciona una colección para visualizar datos.</p>
        </div>

        <div id="modal_img" class="modal">
            <div class="modal-content" id="cont_img"></div>
        </div>

        <script>
            async function cargarColeccion(tipo) {{
                const cont = document.getElementById('tabla_contenedor');
                cont.innerHTML = '<p style="text-align:center;">Consultando base de datos...</p>';
                
                const r = await fetch('/api/coleccion/' + tipo);
                const data = await r.json();
                
                let html = '<h3>Registros: ' + tipo.toUpperCase() + '</h3>';
                if (data.length === 0) {{ html += '<p>No hay datos.</p>'; }}
                else {{
                    html += '<div class="card"><table>';
                    if (tipo === 'visitas') {{
                        data.forEach(v => {{
                            html += `<tr><td>${{v.pv}}<br><small>${{v.fecha}}</small></td>
                                     <td><button class="btn btn-blue" style="padding:5px; font-size:10px;" onclick="verFotos('${{v._id}}')">Fotos</button></td></tr>`;
                        }});
                    }} else if (tipo === 'puntos') {{
                        data.forEach(p => {{ html += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p.BMB}}</td></tr>`; }});
                    }} else {{
                        data.forEach(u => {{ html += `<tr><td>${{u.nombre_completo}}</td><td>${{u.rol}}</td></tr>`; }});
                    }}
                    html += '</table></div>';
                }}
                cont.innerHTML = html;
            }}

            async function verFotos(id) {{
                const modal = document.getElementById('modal_img');
                const cont = document.getElementById('cont_img');
                modal.style.display = 'block';
                cont.innerHTML = 'Cargando soportes...';
                
                const r = await fetch('/api/fotos/' + id);
                const d = await r.json();
                
                cont.innerHTML = `
                    <button class="btn btn-light" onclick="document.getElementById('modal_img').style.display='none'">Cerrar</button>
                    <img src="${{d.f1}}">
                    <img src="${{d.f2}}">
                `;
            }}
        </script>
        <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
    </body></html>
    """)

# --- API DE CONSULTA INDIVIDUAL POR BOTÓN ---

@app.route('/api/coleccion/<tipo>')
def api_coleccion(tipo):
    try:
        if tipo == 'visitas':
            # IMPORTANTE: Excluimos campos pesados de imagen
            res = list(db['visitas'].find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1).limit(50))
        elif tipo == 'puntos':
            res = list(db['puntos_venta'].find({}, {"_id": 0}).limit(100))
        else:
            res = list(db['usuarios'].find({}, {"_id": 0}))
        
        for doc in res:
            if '_id' in doc: doc['_id'] = str(doc['_id'])
        return jsonify(res)
    except:
        return jsonify([])

@app.route('/api/fotos/<id>')
def api_fotos(id):
    # Solo carga imágenes para un ID específico (Ahorro total de RAM)
    doc = db['visitas'].find_one({"_id": ObjectId(id)})
    gc.collect() # Limpiar RAM tras consulta pesada
    return jsonify({
        "f1": doc.get('f_bmb', ''),
        "f2": doc.get('f_fachada', '')
    })

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def to_b64(f):
            if not f: return ""
            b = base64.b64encode(f.read()).decode()
            f.close()
            return f"data:image/jpeg;base64,{b}"
        
        db['visitas'].insert_one({
            "pv": request.form.get('pv'),
            "fecha": request.form.get('fecha'),
            "n_documento": session.get('user_name'),
            "f_bmb": to_b64(request.files.get('f1')),
            "f_fachada": to_b64(request.files.get('f2')),
            "estado": "Pendiente"
        })
        gc.collect()
        return redirect('/')
    
    return render_template_string(f"<html><head>{CSS}</head><body><div class='card'><h3>Nuevo Reporte</h3><form method='POST' enctype='multipart/form-data'><input type='text' name='pv' placeholder='Punto de Venta' style='width:100%; margin-bottom:10px; padding:10px;'><input type='date' name='fecha' style='width:100%; margin-bottom:10px; padding:10px;'><input type='file' name='f1' accept='image/*' capture='camera'><br><input type='file' name='f2' accept='image/*' capture='camera'><br><button class='btn btn-blue'>Enviar</button><a href='/' class='btn btn-white'>Cancelar</a></form></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = db['usuarios'].find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u:
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo']})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='card' style='width:300px;'><h3>Nestlé BI</h3><form method='POST'><input type='text' name='u' placeholder='Usuario' style='width:100%; margin-bottom:10px; padding:10px;'><input type='password' name='p' placeholder='Clave' style='width:100%; margin-bottom:10px; padding:10px;'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
