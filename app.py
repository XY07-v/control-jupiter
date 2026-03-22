from flask import Flask, render_template_string, request, redirect, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64

app = Flask(__name__)

# Conexión optimizada
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

@app.route('/')
def index():
    # Solo traemos los campos de texto
    registros = list(coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1))
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .header img { height: 28px; width: auto; }
            .btn-new { background: var(--ios-blue); color: white; padding: 15px; border-radius: 12px; text-decoration: none; display: block; text-align: center; font-weight: 700; margin-bottom: 15px; }
            
            .list { background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .item { padding: 15px; border-bottom: 0.5px solid #C6C6C8; cursor: pointer; }
            .item:active { background: #E5E5EA; }
            .item h4 { margin: 0; font-size: 16px; color: #1C1C1E; }
            .item p { margin: 4px 0 0; font-size: 13px; color: #8E8E93; }

            /* Modal Estilo iPhone */
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; justify-content: center; align-items: flex-end; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 90vh; overflow-y: auto; animation: slideUp 0.3s ease-out; }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
            
            .detail-row { margin-bottom: 15px; border-bottom: 0.5px solid #eee; padding-bottom: 8px; }
            .label { font-size: 11px; font-weight: 700; color: #8E8E93; text-transform: uppercase; }
            .val { font-size: 16px; color: #1C1C1E; margin-top: 2px; }
            
            .btn-photo { background: #E5E5EA; color: #007AFF; border: none; width: 100%; padding: 12px; border-radius: 10px; font-weight: 600; margin-top: 10px; cursor: pointer; }
            .img-container img { width: 100%; border-radius: 12px; margin-top: 10px; display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg">
        </div>

        <a href="/formulario" class="btn-new">＋ NUEVA VISITA</a>

        <div class="list">
            {% for r in registros %}
            <div class="item" onclick='abrirDetalle({{ r|tojson }})'>
                <h4>{{ r.pv }}</h4>
                <p>{{ r.fecha }} | {{ r.bmb if r.bmb != "-1" else "Positivo" }}</p>
            </div>
            {% endfor %}
        </div>

        <div id="modal" class="modal" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="modalBody"></div>
                <button onclick="cerrarModal()" style="width:100%; margin-top:20px; padding:15px; border:none; background:#F2F2F7; border-radius:12px; font-weight:600; color:#FF3B30;">Cerrar</button>
            </div>
        </div>

        <script>
            function abrirDetalle(data) {
                const body = document.getElementById('modalBody');
                body.innerHTML = `
                    <h2 style="margin:0 0 20px 0">${data.pv}</h2>
                    <div class="detail-row"><div class="label">Documento</div><div class="val">${data.n_documento}</div></div>
                    <div class="detail-row"><div class="label">Fecha</div><div class="val">${data.fecha}</div></div>
                    <div class="detail-row"><div class="label">Motivo</div><div class="val">${data.motivo || 'N/A'}</div></div>
                    <div class="detail-row"><div class="label">BMB</div><div class="val">${data.bmb === "-1" ? "Positivo" : data.bmb}</div></div>
                    
                    <button class="btn-photo" id="btn-foto" onclick="cargarFoto('${data._id.$oid}')">🖼 VER FOTOS DEL REGISTRO</button>
                    <div class="img-container" id="fotos-area">
                        <img id="f1"><img id="f2">
                    </div>
                `;
                document.getElementById('modal').style.display = 'flex';
            }

            async function cargarFoto(id) {
                const btn = document.getElementById('btn-foto');
                btn.innerText = "⌛ Cargando desde Base de Datos...";
                try {
                    const res = await fetch('/obtener_foto/' + id);
                    const fotos = await res.json();
                    if(fotos.f_bmb) {
                        document.getElementById('f1').src = fotos.f_bmb;
                        document.getElementById('f1').style.display = 'block';
                    }
                    if(fotos.f_fachada) {
                        document.getElementById('f2').src = fotos.f_fachada;
                        document.getElementById('f2').style.display = 'block';
                    }
                    btn.style.display = 'none';
                } catch(e) { btn.innerText = "❌ Error al cargar"; }
            }

            function cerrarModal() { document.getElementById('modal').style.display = 'none'; }
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/obtener_foto/<id>')
def obtener_foto(id):
    # Esta ruta SOLO se llama cuando el usuario quiere ver la foto
    doc = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({
        "f_bmb": doc.get('f_bmb', ''),
        "f_fachada": doc.get('f_fachada', '')
    })

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # (Lógica de guardado simplificada)
        f_bmb = f"data:{request.files['f_bmb'].content_type};base64,{base64.b64encode(request.files['f_bmb'].read()).decode('utf-8')}" if 'f_bmb' in request.files else ""
        f_fachada = f"data:{request.files['f_fachada'].content_type};base64,{base64.b64encode(request.files['f_fachada'].read()).decode('utf-8')}" if 'f_fachada' in request.files else ""
        
        coleccion.insert_one({
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'),
            "f_bmb": f_bmb,
            "f_fachada": f_fachada
        })
        return redirect('/')
    
    return render_template_string("""
    <body style="font-family:sans-serif; background:#F2F2F7; padding:20px;">
        <a href="/" style="text-decoration:none; color:#8E8E93;">✕ Cancelar</a>
        <form method="POST" enctype="multipart/form-data" style="background:white; padding:20px; border-radius:15px; margin-top:15px;">
            <h3>Nuevo Registro</h3>
            <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; padding:12px; margin-bottom:10px; border-radius:8px; border:1px solid #ddd;">
            <input type="text" name="n_documento" placeholder="Documento" required style="width:100%; padding:12px; margin-bottom:10px; border-radius:8px; border:1px solid #ddd;">
            <input type="date" name="fecha" required style="width:100%; padding:12px; margin-bottom:10px; border-radius:8px; border:1px solid #ddd;">
            <input type="text" name="bmb" placeholder="BMB (-1 para positivo)" required style="width:100%; padding:12px; margin-bottom:10px; border-radius:8px; border:1px solid #ddd;">
            <select name="motivo" style="width:100%; padding:12px; margin-bottom:10px; border-radius:8px; border:1px solid #ddd;">
                <option>Maquina Retirada</option>
                <option>Fuera de Rango</option>
                <option>No sale en Trade</option>
            </select>
            <label style="font-size:12px; color:#888;">Foto BMB</label>
            <input type="file" name="f_bmb" accept="image/*" capture="camera" style="margin-bottom:10px;">
            <label style="font-size:12px; color:#888;">Foto Fachada</label>
            <input type="file" name="f_fachada" accept="image/*" capture="camera" style="margin-bottom:10px;">
            <button type="submit" style="width:100%; padding:15px; background:#34C759; color:white; border:none; border-radius:12px; font-weight:700;">GUARDAR</button>
        </form>
    </body>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
