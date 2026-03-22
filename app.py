from flask import Flask, render_template_string, request, redirect, jsonify, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64, io, csv

app = Flask(__name__)

# Conexión Segura
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_id(doc):
    doc['_id'] = str(doc['_id'])
    return doc

@app.route('/')
def index():
    # Carga rápida: excluimos binarios pesados de la lista inicial
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_id(r) for r in cursor]
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Visitas a POC - Control</title>
        <style>
            :root { --ios-blue: #007AFF; --ios-green: #34C759; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }
            
            /* Header con Iconos Nuevos */
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 12px; border-radius: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
            .header-title { font-size: 16px; font-weight: 800; color: #1C1C1E; letter-spacing: -0.5px; }
            .icon-tech { font-size: 24px; } /* Icono Tecnología */
            .icon-loc { font-size: 24px; color: #FF3B30; } /* Icono Ubicación */
            
            .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
            .btn { padding: 14px; border-radius: 12px; text-decoration: none; text-align: center; font-weight: 700; font-size: 14px; border: none; cursor: pointer; }
            .btn-new { background: var(--ios-blue); color: white; }
            .btn-download { background: white; color: #1C1C1E; border: 1px solid #D1D1D6; }
            
            /* Lista */
            .list { background: white; border-radius: 16px; overflow: hidden; }
            .item { padding: 15px; border-bottom: 0.5px solid #E5E5EA; cursor: pointer; }
            .item:active { background: #F2F2F7; }
            .item h4 { margin: 0; font-size: 15px; }
            .item p { margin: 3px 0 0; font-size: 12px; color: #8E8E93; }

            /* Modal Estilo Hoja */
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 1000; align-items: flex-end; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 85vh; overflow-y: auto; animation: slideUp 0.3s; }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
            .detail-row { margin-bottom: 12px; padding-bottom: 8px; border-bottom: 0.5px solid #F2F2F7; }
            .label { font-size: 10px; font-weight: 700; color: #8E8E93; text-transform: uppercase; }
            .val { font-size: 15px; color: #1C1C1E; margin-top: 2px; }
            .img-prev { width: 100%; border-radius: 12px; margin-top: 10px; display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <span class="icon-tech">💻</span>
            <div class="header-title">Visitas a POC - Control</div>
            <span class="icon-loc">📍</span>
        </div>

        <div class="actions">
            <a href="/formulario" class="btn btn-new">＋ NUEVA</a>
            <a href="/descargar" class="btn btn-download">💾 EXCEL</a>
        </div>

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
                <button onclick="cerrarModal()" style="width:100%; margin-top:20px; padding:15px; border:none; background:#F2F2F7; border-radius:12px; font-weight:700; color:#FF3B30;">Cerrar</button>
            </div>
        </div>

        <script>
            function abrirDetalle(data) {
                document.getElementById('modalBody').innerHTML = `
                    <h2 style="margin:0 0 15px 0">${data.pv}</h2>
                    <div class="detail-row"><div class="label">Documento</div><div class="val">${data.n_documento}</div></div>
                    <div class="detail-row"><div class="label">Fecha</div><div class="val">${data.fecha}</div></div>
                    <div class="detail-row"><div class="label">Estado BMB</div><div class="val">${data.bmb === "-1" ? "Positivo" : data.bmb}</div></div>
                    <div class="detail-row"><div class="label">Motivo</div><div class="val">${data.motivo}</div></div>
                    <div class="detail-row"><div class="label">GPS</div><div class="val">${data.ubicacion || 'Sin GPS'}</div></div>
                    
                    <button id="btn-foto" onclick="verFotos('${data._id}')" style="width:100%; padding:12px; border-radius:10px; border:1.5px solid var(--ios-blue); color:var(--ios-blue); background:none; font-weight:600;">VER EVIDENCIA FOTOGRÁFICA</button>
                    <img id="img1" class="img-prev"><img id="img2" class="img-prev">
                `;
                document.getElementById('modal').style.display = 'flex';
            }

            async function verFotos(id) {
                const btn = document.getElementById('btn-foto');
                btn.innerText = "⌛ Consultando...";
                const res = await fetch('/obtener_foto/' + id);
                const json = await res.json();
                if(json.f_bmb) { document.getElementById('img1').src = json.f_bmb; document.getElementById('img1').style.display='block'; }
                if(json.f_fachada) { document.getElementById('img2').src = json.f_fachada; document.getElementById('img2').style.display='block'; }
                btn.style.display = 'none';
            }
            function cerrarModal() { document.getElementById('modal').style.display = 'none'; }
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/obtener_foto/<id>')
def obtener_foto(id):
    doc = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f_bmb": doc.get('f_bmb',''), "f_fachada": doc.get('f_fachada','')})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        f_bmb = f"data:{request.files['f_bmb'].content_type};base64,{base64.b64encode(request.files['f_bmb'].read()).decode('utf-8')}" if 'f_bmb' in request.files and request.files['f_bmb'].filename != '' else ""
        f_fachada = f"data:{request.files['f_fachada'].content_type};base64,{base64.b64encode(request.files['f_fachada'].read()).decode('utf-8')}" if 'f_fachada' in request.files and request.files['f_fachada'].filename != '' else ""
        
        coleccion.insert_one({
            "pv": request.form.get('pv'),
            "n_documento": request.form.get('n_documento'),
            "fecha": request.form.get('fecha'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'),
            "ubicacion": request.form.get('ubicacion'),
            "f_bmb": f_bmb,
            "f_fachada": f_fachada
        })
        return redirect('/')
    
    return render_template_string("""
    <body style="font-family:sans-serif; background:#F2F2F7; padding:20px;">
        <a href="/" style="text-decoration:none; color:#007AFF; font-weight:700;">✕ CANCELAR</a>
        <form method="POST" enctype="multipart/form-data" style="background:white; padding:20px; border-radius:18px; margin-top:15px;">
            <h2 style="margin:0 0 20px 0;">Nuevo Reporte</h2>
            
            <label style="font-size:11px; font-weight:700; color:#888;">PUNTO DE VENTA</label>
            <input type="text" name="pv" required style="width:100%; padding:12px; margin:5px 0 15px; border-radius:10px; border:1px solid #ddd;">
            
            <label style="font-size:11px; font-weight:700; color:#888;">N. DOCUMENTO</label>
            <input type="text" name="n_documento" required style="width:100%; padding:12px; margin:5px 0 15px; border-radius:10px; border:1px solid #ddd;">
            
            <label style="font-size:11px; font-weight:700; color:#888;">FECHA DE VISITA</label>
            <input type="date" name="fecha" required style="width:100%; padding:12px; margin:5px 0 15px; border-radius:10px; border:1px solid #ddd;">
            
            <label style="font-size:11px; font-weight:700; color:#888;">BMB (-1 = POSITIVO)</label>
            <input type="text" name="bmb" required style="width:100%; padding:12px; margin:5px 0 15px; border-radius:10px; border:1px solid #ddd;">
            
            <label style="font-size:11px; font-weight:700; color:#888;">MOTIVO DE LA VISITA</label>
            <select name="motivo" style="width:100%; padding:12px; margin:5px 0 15px; border-radius:10px; border:1px solid #ddd;">
                <option>Máquina Retirada</option>
                <option>Fuera de Rango</option>
                <option>No sale en Trade</option>
                <option>Punto Cerrado</option>
            </select>

            <button type="button" onclick="getGPS()" id="gps-btn" style="width:100%; padding:10px; background:#5856D6; color:white; border:none; border-radius:8px; margin-bottom:15px;">📍 CAPTURAR GPS</button>
            <input type="hidden" name="ubicacion" id="ub">

            <label style="font-size:11px; font-weight:700; color:#888;">FOTO BMB</label>
            <input type="file" name="f_bmb" accept="image/*" capture="camera" style="margin-bottom:15px;">

            <label style="font-size:11px; font-weight:700; color:#888;">FOTO FACHADA</label>
            <input type="file" name="f_fachada" accept="image/*" capture="camera" style="margin-bottom:15px;">

            <button type="submit" style="width:100%; padding:16px; background:#34C759; color:white; border:none; border-radius:15px; font-weight:800; font-size:16px;">GUARDAR VISITA</button>
        </form>
        <script>
            function getGPS() {
                navigator.geolocation.getCurrentPosition(p => {
                    document.getElementById('ub').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps-btn').innerText = "✅ GPS CAPTURADO";
                    document.getElementById('gps-btn').style.background = "#34C759";
                });
            }
        </script>
    </body>
    """)

@app.route('/descargar')
def descargar():
    cursor = coleccion.find({}, {"f_bmb":0, "f_fachada":0})
    def generate():
        data = io.StringIO()
        w = csv.writer(data)
        w.writerow(['Punto de Venta', 'Documento', 'Fecha', 'BMB', 'Motivo', 'Ubicacion'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        for r in cursor:
            w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('ubicacion')])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=visitas.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
