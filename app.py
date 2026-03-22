from flask import Flask, render_template_string, request, redirect, jsonify, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64, io, csv, requests

app = Flask(__name__)

# Conexión Segura a MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_id(doc):
    doc['_id'] = str(doc['_id'])
    return doc

# --- VISTA PRINCIPAL ---
@app.route('/')
def index():
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_id(r) for r in cursor]
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Visitas a POC - Control</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root { --ios-blue: #007AFF; --ios-green: #34C759; --ios-red: #FF3B30; --bg: #F2F2F7; }
            body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; color: #1C1C1E; }
            
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 12px 18px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            .header-title { font-size: 16px; font-weight: 800; letter-spacing: -0.5px; }
            
            .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
            .btn { padding: 15px; border-radius: 14px; text-decoration: none; text-align: center; font-weight: 700; font-size: 14px; border: none; cursor: pointer; transition: 0.2s; }
            .btn-new { background: var(--ios-blue); color: white; }
            .btn-download { background: white; color: #1C1C1E; border: 1.5px solid #D1D1D6; }
            
            .list { background: white; border-radius: 18px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .item { padding: 16px; border-bottom: 0.5px solid #E5E5EA; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
            .item:active { background: #F2F2F7; }
            .item h4 { margin: 0; font-size: 16px; font-weight: 600; }
            .item p { margin: 4px 0 0; font-size: 13px; color: #8E8E93; }

            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: flex-end; }
            .modal-content { background: white; width: 100%; border-radius: 25px 25px 0 0; padding: 25px; box-sizing: border-box; max-height: 90vh; overflow-y: auto; animation: slideUp 0.35s cubic-bezier(0.2, 0.8, 0.2, 1); }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
            
            .detail-row { margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #F2F2F7; }
            .label { font-size: 10px; font-weight: 700; color: #8E8E93; text-transform: uppercase; margin-bottom: 3px; }
            .val { font-size: 16px; font-weight: 400; }
            
            .btn-reveal { width: 100%; padding: 14px; border-radius: 12px; border: 2px solid var(--ios-blue); color: var(--ios-blue); background: white; font-weight: 700; margin-top: 10px; cursor: pointer; }
            .img-res { width: 100%; border-radius: 14px; margin-top: 15px; display: none; }
            #map { height: 200px; width: 100%; border-radius: 14px; margin-top: 15px; display: none; }
            
            /* Alertas de Éxito/Error */
            .alert { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); padding: 15px 25px; border-radius: 30px; color: white; font-weight: 600; z-index: 2000; display: none; box-shadow: 0 10px 20px rgba(0,0,0,0.15); }
            .alert-success { background: var(--ios-green); }
            .alert-error { background: var(--ios-red); }
        </style>
    </head>
    <body>
        <div id="alert" class="alert"></div>

        <div class="header">
            <span style="font-size: 24px;">💻</span>
            <div class="header-title">Visitas a POC - Control</div>
            <span style="font-size: 24px; color: var(--ios-red);">📍</span>
        </div>

        <div class="actions">
            <a href="/formulario" class="btn btn-new">＋ REGISTRAR</a>
            <a href="/descargar" class="btn btn-download">💾 REPORTE</a>
        </div>

        <div class="list">
            {% for r in registros %}
            <div class="item" onclick='abrirDetalle({{ r|tojson }})'>
                <div>
                    <h4>{{ r.pv }}</h4>
                    <p>{{ r.fecha }} | {{ "✅ Positivo" if r.bmb == "-1" else r.bmb }}</p>
                </div>
                <span style="color: #C7C7CC; font-size: 20px;">›</span>
            </div>
            {% endfor %}
        </div>

        <div id="modal" class="modal" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="modalBody"></div>
                <button onclick="cerrarModal()" style="width:100%; margin-top:25px; padding:16px; border:none; background:#F2F2F7; border-radius:15px; font-weight:700; color:var(--ios-red);">Cerrar</button>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapInstance = null;

            function abrirDetalle(data) {
                const body = document.getElementById('modalBody');
                body.innerHTML = `
                    <h2 style="margin:0 0 20px 0; font-size: 24px;">${data.pv}</h2>
                    <div class="detail-row"><div class="label">Ubicación Proyectada</div><div class="val">${data.direccion || 'No disponible'}</div></div>
                    <div class="detail-row"><div class="label">Ciudad / Depto</div><div class="val">${data.ciudad || '-'} / ${data.departamento || '-'}</div></div>
                    <div class="detail-row"><div class="label">Estado BMB</div><div class="val">${data.bmb === "-1" ? "Positivo" : data.bmb}</div></div>
                    <div class="detail-row"><div class="label">Motivo</div><div class="val">${data.motivo}</div></div>
                    
                    <button id="btn-reveal" class="btn-reveal" onclick="cargarEvidencia('${data._id}', '${data.ubicacion}')">👀 VER FOTOS Y MAPA</button>
                    <div id="map"></div>
                    <img id="f1" class="img-res"><img id="f2" class="img-res">
                `;
                document.getElementById('modal').style.display = 'flex';
            }

            async function cargarEvidencia(id, coords) {
                const btn = document.getElementById('btn-reveal');
                btn.innerText = "⌛ Cargando...";
                
                // Cargar Fotos
                const res = await fetch('/obtener_foto/' + id);
                const json = await res.json();
                
                if(json.f_bmb) { document.getElementById('f1').src = json.f_bmb; document.getElementById('f1').style.display='block'; }
                if(json.f_fachada) { document.getElementById('f2').src = json.f_fachada; document.getElementById('f2').style.display='block'; }
                
                // Mostrar Mapa
                if(coords) {
                    const [lat, lng] = coords.split(',').map(Number);
                    document.getElementById('map').style.display = 'block';
                    if(!mapInstance) {
                        mapInstance = L.map('map').setView([lat, lng], 16);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(mapInstance);
                    }
                    L.marker([lat, lng]).addTo(mapInstance);
                }
                
                btn.style.display = 'none';
            }

            function cerrarModal() { 
                document.getElementById('modal').style.display = 'none';
                if(mapInstance) { mapInstance.remove(); mapInstance = null; }
            }

            // Manejo de mensajes de éxito/error desde la URL
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('success')) {
                const alert = document.getElementById('alert');
                alert.innerText = "¡Formulario enviado con éxito! ✅";
                alert.className = "alert alert-success";
                alert.style.display = "block";
                setTimeout(() => alert.style.display = "none", 4000);
            }
        </script>
    </body>
    </html>
    """, registros=registros)

# --- OBTENER FOTOS (BAJO DEMANDA) ---
@app.route('/obtener_foto/<id>')
def obtener_foto(id):
    doc = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f_bmb": doc.get('f_bmb',''), "f_fachada": doc.get('f_fachada','')})

# --- FORMULARIO DE REGISTRO ---
@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        try:
            # Procesar GPS y obtener dirección (Geocodificación Inversa)
            lat_lng = request.form.get('ubicacion')
            direccion, ciudad, depto = "N/A", "N/A", "N/A"
            
            if lat_lng:
                lat, lon = lat_lng.split(',')
                headers = {'User-Agent': 'NestlePOCControl/1.0'}
                geo_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers=headers).json()
                addr = geo_res.get('address', {})
                direccion = geo_res.get('display_name', 'Dirección no encontrada').split(',')[0]
                ciudad = addr.get('city') or addr.get('town') or addr.get('village') or "N/A"
                depto = addr.get('state', 'N/A')

            # Procesar Imágenes
            f_bmb = f"data:{request.files['f_bmb'].content_type};base64,{base64.b64encode(request.files['f_bmb'].read()).decode('utf-8')}" if 'f_bmb' in request.files and request.files['f_bmb'].filename != '' else ""
            f_fachada = f"data:{request.files['f_fachada'].content_type};base64,{base64.b64encode(request.files['f_fachada'].read()).decode('utf-8')}" if 'f_fachada' in request.files and request.files['f_fachada'].filename != '' else ""
            
            coleccion.insert_one({
                "pv": request.form.get('pv'),
                "n_documento": request.form.get('n_documento'),
                "fecha": request.form.get('fecha'),
                "bmb": request.form.get('bmb'),
                "motivo": request.form.get('motivo'),
                "ubicacion": lat_lng,
                "direccion": direccion,
                "ciudad": ciudad,
                "departamento": depto,
                "f_bmb": f_bmb,
                "f_fachada": f_fachada
            })
            return redirect('/?success=1')
        except Exception as e:
            return redirect('/?error=1')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; padding: 20px; margin: 0; }
            .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
            .label { font-size: 11px; font-weight: 700; color: #8E8E93; text-transform: uppercase; margin-top: 15px; display: block; }
            input, select { width: 100%; padding: 14px; margin-top: 5px; border: 1.5px solid #E5E5EA; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
            .btn-gps { background: #5856D6; color: white; border: none; padding: 14px; border-radius: 12px; width: 100%; font-weight: 700; margin: 15px 0; }
            .btn-save { background: #34C759; color: white; border: none; width: 100%; padding: 18px; border-radius: 16px; font-weight: 800; font-size: 17px; margin-top: 25px; }
        </style>
    </head>
    <body>
        <a href="/" style="text-decoration:none; color: #007AFF; font-weight:600;">✕ CANCELAR REGISTRO</a>
        <div class="card" style="margin-top: 15px;">
            <h2 style="margin:0 0 10px 0;">Nueva Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <label class="label">Punto de Venta</label>
                <input type="text" name="pv" required>
                
                <label class="label">Número de Documento</label>
                <input type="text" name="n_documento" required>
                
                <label class="label">Fecha</label>
                <input type="date" name="fecha" required>
                
                <label class="label">BMB (-1 = Positivo)</label>
                <input type="text" name="bmb" required>
                
                <label class="label">Motivo</label>
                <select name="motivo">
                    <option>Máquina Retirada</option>
                    <option>Fuera de Rango</option>
                    <option>No sale en Trade</option>
                    <option>Punto Cerrado</option>
                </select>

                <button type="button" onclick="getGPS()" id="gps-btn" class="btn-gps">📍 CAPTURAR UBICACIÓN ACTUAL</button>
                <input type="hidden" name="ubicacion" id="ub">

                <label class="label">Foto BMB</label>
                <input type="file" name="f_bmb" accept="image/*" capture="camera">
                
                <label class="label">Foto Fachada</label>
                <input type="file" name="f_fachada" accept="image/*" capture="camera">

                <button type="submit" class="btn-save">ENVIAR REPORTE</button>
            </form>
        </div>
        <script>
            function getGPS() {
                const btn = document.getElementById('gps-btn');
                btn.innerText = "⌛ Localizando...";
                navigator.geolocation.getCurrentPosition(p => {
                    document.getElementById('ub').value = p.coords.latitude + "," + p.coords.longitude;
                    btn.innerText = "✅ UBICACIÓN LISTA";
                    btn.style.background = "#34C759";
                }, () => {
                    alert("Por favor activa el GPS de tu celular.");
                    btn.innerText = "❌ ERROR GPS";
                });
            }
        </script>
    </body>
    </html>
    """)

# --- DESCARGA DE EXCEL ---
@app.route('/descargar')
def descargar():
    cursor = coleccion.find({}, {"f_bmb":0, "f_fachada":0})
    def generate():
        data = io.StringIO()
        w = csv.writer(data)
        w.writerow(['PV', 'Doc', 'Fecha', 'BMB', 'Motivo', 'Direccion', 'Ciudad', 'Depto', 'Coords'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        for r in cursor:
            w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('direccion'), r.get('ciudad'), r.get('departamento'), r.get('ubicacion')])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=visitas_poc.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
