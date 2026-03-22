from flask import Flask, render_template_string, request, redirect, jsonify, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv

app = Flask(__name__)

# Configuración de MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_id(doc):
    doc['_id'] = str(doc['_id'])
    # Lógica de negocio para BMB: -1 es positivo (✅), vacío es déficit (❌)
    val = str(doc.get('bmb', '')).strip()
    if val == "-1":
        doc['bmb_display'] = "✅"
    elif val == "":
        doc['bmb_display'] = "❌"
    else:
        doc['bmb_display'] = val # Por si llega el ID del BMB como en tu ejemplo
    return doc

@app.route('/')
def index():
    # Solo traemos texto para velocidad. Las fotos se cargan bajo demanda.
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_id(r) for r in cursor]
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { font-family: -apple-system, sans-serif; background: #F2F2F7; margin: 0; padding: 15px; }
            .header { padding: 15px; background: white; border-radius: 15px; margin-bottom: 15px; font-weight: bold; }
            .btn-group { display: flex; justify-content: space-between; margin-bottom: 20px; }
            .btn { padding: 15px; border-radius: 12px; text-decoration: none; font-weight: 700; width: 46%; text-align: center; }
            .btn-blue { background: #007AFF; color: white; }
            .btn-white { background: white; color: #1C1C1E; border: 1px solid #D1D1D6; }
            .list { background: white; border-radius: 15px; overflow: hidden; }
            .item { padding: 15px; border-bottom: 1px solid #F2F2F7; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; align-items: flex-end; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; max-height: 90vh; overflow-y: auto; }
            #map { height: 200px; width: 100%; border-radius: 12px; margin-top: 15px; display: none; }
            .img-prev { width: 100%; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <div class="header">Visitas a POC - Control 📍</div>
        <div class="btn-group">
            <a href="/formulario" class="btn btn-blue">＋ REGISTRAR</a>
            <a href="/descargar" class="btn btn-white">💾 EXCEL</a>
        </div>
        <div class="list">
            {% for r in registros %}
            <div class="item" onclick='verDetalle({{ r|tojson }})'>
                <div>
                    <h4 style="margin:0;">{{ r.pv }}</h4>
                    <small style="color: #8E8E93;">{{ r.fecha }} | {{ r.mes }}</small>
                </div>
                <div style="font-size: 20px;">{{ r.bmb_display }}</div>
            </div>
            {% endfor %}
        </div>

        <div id="modal" class="modal" onclick="this.style.display='none'">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="cont"></div>
                <button onclick="document.getElementById('modal').style.display='none'" style="width:100%; padding:15px; margin-top:20px; border:none; border-radius:12px; background:#F2F2F7; font-weight:700; color:red;">Cerrar</button>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapInstance = null;
            function verDetalle(d) {
                document.getElementById('cont').innerHTML = `
                    <h3>${d.pv}</h3>
                    <p><b>Mes:</b> ${d.mes}<br><b>Documento:</b> ${d.n_documento}<br><b>Motivo:</b> ${d.motivo}</p>
                    <button id="btn-f" onclick="cargarFotos('${d._id}','${d.ubicacion}')" style="width:100%; padding:14px; color:#007AFF; border:2px solid #007AFF; background:none; border-radius:12px; font-weight:700;">👁️ VER FOTOS Y MAPA</button>
                    <div id="map"></div>
                    <p id="txt-f" style="display:none; margin-top:15px; font-weight:bold;">Evidencia Fotográfica:</p>
                    <img id="f1" class="img-prev">
                    <img id="f2" class="img-prev">
                `;
                document.getElementById('modal').style.display='flex';
            }

            async function cargarFotos(id, coords) {
                const btn = document.getElementById('btn-f');
                btn.innerText = "Cargando datos...";
                
                const res = await fetch('/obtener_evidencia/' + id);
                const j = await res.json();
                
                if(j.f1) { 
                    document.getElementById('f1').src = j.f1; 
                    document.getElementById('f1').style.display = 'block'; 
                }
                if(j.f2) { 
                    document.getElementById('f2').src = j.f2; 
                    document.getElementById('f2').style.display = 'block'; 
                }
                if(j.f1 || j.f2) document.getElementById('txt-f').style.display = 'block';

                if(coords) {
                    document.getElementById('map').style.display = 'block';
                    const c = coords.split(',').map(Number);
                    if(mapInstance) mapInstance.remove();
                    mapInstance = L.map('map').setView(c, 16);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(mapInstance);
                    L.marker(c).addTo(mapInstance);
                    setTimeout(() => mapInstance.invalidateSize(), 200);
                }
                btn.style.display = 'none';
            }
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/obtener_evidencia/<id>')
def obtener_evidencia(id):
    # Aquí buscamos específicamente las columnas de imagen que no se cargaron al inicio
    d = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/descargar')
def descargar():
    # Incluimos la columna 'mes' y 'bmb' en la descarga
    cursor = coleccion.find({}, {"pv":1, "n_documento":1, "fecha":1, "mes":1, "bmb":1, "motivo":1, "ubicacion":1, "_id":0})
    def gen():
        d = io.StringIO(); w = csv.writer(d)
        w.writerow(['Punto de Venta', 'Documento', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicacion'])
        yield d.getvalue(); d.seek(0); d.truncate(0)
        for r in cursor:
            # Para el Excel, traducimos el -1 a texto claro o dejamos el ID si es lo que necesitas
            bmb_val = r.get('bmb', '')
            if bmb_val == "-1": bmb_val = "POSITIVO (✅)"
            elif bmb_val == "": bmb_val = "DEFICIT (❌)"
            
            w.writerow([r.get('pv',''), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), bmb_val, r.get('motivo',''), r.get('ubicacion','')])
            yield d.getvalue(); d.seek(0); d.truncate(0)
    return Response(gen(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=reporte_nestle.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
