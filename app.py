from flask import Flask, render_template_string, request, redirect, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64

app = Flask(__name__)

# Conexión Robusta con reintentos automáticos
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_documento(doc):
    """Convierte el ID de MongoDB a texto para evitar el Internal Server Error"""
    doc['_id'] = str(doc['_id'])
    return doc

@app.route('/')
def index():
    # Solo traemos texto para velocidad extrema
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_documento(r) for r in cursor]
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <style>
            :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background:white; padding:10px; border-radius:12px; }
            .header img { height: 25px; width: auto; max-width: 90px; object-fit: contain; }
            .btn-new { background: var(--ios-blue); color: white; padding: 16px; border-radius: 14px; text-decoration: none; display: block; text-align: center; font-weight: 700; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,122,255,0.2); }
            
            .list { background: white; border-radius: 16px; overflow: hidden; }
            .item { padding: 15px; border-bottom: 0.5px solid #E5E5EA; cursor: pointer; -webkit-tap-highlight-color: transparent; }
            .item:active { background: #F2F2F7; }
            .item h4 { margin: 0; font-size: 16px; color: #1C1C1E; }
            .item p { margin: 4px 0 0; font-size: 13px; color: #8E8E93; }

            /* Modal Estilo Hoja de iPhone */
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: flex-end; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 90vh; overflow-y: auto; animation: slideUp 0.3s ease-out; }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
            
            .detail-row { margin-bottom: 12px; }
            .label { font-size: 11px; font-weight: 700; color: #8E8E93; text-transform: uppercase; }
            .val { font-size: 16px; color: #1C1C1E; border-bottom: 1px solid #F2F2F7; padding-bottom: 5px; }
            
            .btn-photo { background: #F2F2F7; color: var(--ios-blue); border: none; width: 100%; padding: 14px; border-radius: 12px; font-weight: 600; margin-top: 15px; }
            .img-res { width: 100%; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid #eee; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/b/bf/Nestl%C3%A9_logo.svg">
            <span style="font-weight:800; color:#444">CONTROL</span>
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a0/ManpowerGroup_logo.svg">
        </div>

        <a href="/formulario" class="btn-new">＋ NUEVO REPORTE</a>

        <div class="list">
            {% for r in registros %}
            <div class="item" onclick='abrirDetalle({{ r|tojson }})'>
                <h4>{{ r.pv }}</h4>
                <p>{{ r.fecha }} | {{ "✅ Positivo" if r.bmb == "-1" else r.bmb }}</p>
            </div>
            {% endfor %}
        </div>

        <div id="modal" class="modal" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="modalBody"></div>
                <button onclick="cerrarModal()" style="width:100%; margin-top:20px; padding:15px; border:none; background:#F2F2F7; border-radius:12px; font-weight:700; color:#FF3B30;">Cerrar Detalle</button>
            </div>
        </div>

        <script>
            function abrirDetalle(data) {
                const body = document.getElementById('modalBody');
                body.innerHTML = `
                    <h2 style="margin:0 0 20px 0">${data.pv}</h2>
                    <div class="detail-row"><div class="label">Documento</div><div class="val">${data.n_documento}</div></div>
                    <div class="detail-row"><div class="label">Fecha</div><div class="val">${data.fecha}</div></div>
                    <div class="detail-row"><div class="label">Estado BMB</div><div class="val">${data.bmb === "-1" ? "Positivo" : data.bmb}</div></div>
                    <div class="detail-row"><div class="label">Motivo</div><div class="val">${data.motivo || 'N/A'}</div></div>
                    
                    <button class="btn-photo" id="btn-foto" onclick="cargarFoto('${data._id}')">🖼 VER FOTOS DE EVIDENCIA</button>
                    <img id="f1" class="img-res">
                    <img id="f2" class="img-res">
                `;
                document.getElementById('modal').style.display = 'flex';
            }

            async function cargarFoto(id) {
                const btn = document.getElementById('btn-foto');
                btn.innerText = "⌛ Consultando base de datos...";
                try {
                    const res = await fetch('/obtener_foto/' + id);
                    const fotos = await res.json();
                    if(fotos.f_bmb) { document.getElementById('f1').src = fotos.f_bmb; document.getElementById('f1').style.display = 'block'; }
                    if(fotos.f_fachada) { document.getElementById('f2').src = fotos.f_fachada; document.getElementById('f2').style.display = 'block'; }
                    btn.style.display = 'none';
                } catch(e) { btn.innerText = "❌ Error de conexión"; }
            }

            function cerrarModal() { document.getElementById('modal').style.display = 'none'; }
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/obtener_foto/<id>')
def obtener_foto(id):
    doc = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({
        "f_bmb": doc.get('f_bmb', ''),
        "f_fachada": doc.get('f_fachada', '')
    })

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Conversión segura de imágenes
        f_bmb = ""
        f_fachada = ""
        if 'f_bmb' in request.files:
            file = request.files['f_bmb']
            if file.filename != '':
                f_bmb = f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"
        
        if 'f_fachada' in request.files:
            file = request.files['f_fachada']
            if file.filename != '':
                f_fachada = f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode('utf-8')}"

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
    <body style="font-family:-apple-system,sans-serif; background:#F2F2F7; padding:20px; margin:0;">
        <div style="max-width:500px; margin:auto;">
            <a href="/" style="text-decoration:none; color:#007AFF; font-weight:600;">✕ SALIR SIN GUARDAR</a>
            <form method="POST" enctype="multipart/form-data" style="background:white; padding:25px; border-radius:20px; margin-top:15px; box-shadow:0 4px 15px rgba(0,0,0,0.05);">
                <h2 style="margin-top:0;">Nueva Visita</h2>
                <label style="font-size:12px; font-weight:700; color:#8E8E93;">PUNTO DE VENTA</label>
                <input type="text" name="pv" required style="width:100%; padding:14px; margin:5px 0 15px; border:1px solid #D1D1D6; border-radius:12px; box-sizing:border-box;">
                
                <label style="font-size:12px; font-weight:700; color:#8E8E93;">BMB (-1 = Positivo)</label>
                <input type="text" name="bmb" required style="width:100%; padding:14px; margin:5px 0 15px; border:1px solid #D1D1D6; border-radius:12px; box-sizing:border-box;">
                
                <label style="font-size:12px; font-weight:700; color:#8E8E93;">FECHA</label>
                <input type="date" name="fecha" required style="width:100%; padding:14px; margin:5px 0 15px; border:1px solid #D1D1D6; border-radius:12px; box-sizing:border-box;">

                <label style="font-size:12px; font-weight:700; color:#8E8E93;">FOTO BMB</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera" style="margin-bottom:15px;">

                <button type="submit" style="width:100%; padding:18px; background:#34C759; color:white; border:none; border-radius:15px; font-weight:800; font-size:16px;">FINALIZAR Y GUARDAR</button>
            </form>
        </div>
    </body>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
