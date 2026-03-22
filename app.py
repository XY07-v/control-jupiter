from flask import Flask, render_template_string, request, redirect, jsonify, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, requests

app = Flask(__name__)

# Configuración de MongoDB
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_id(doc):
    doc['_id'] = str(doc['_id'])
    return doc

FOOTER_HTML = """
<footer style="margin-top: 30px; padding: 20px; text-align: center; border-top: 0.5px solid #C6C6C8; color: #8E8E93; font-size: 12px;">
    Desarrollo de <b>Andres Vanegas - Business Inteligente</b> <br>
    © 2026 Todos los derechos reservados.
</footer>
"""

@app.route('/')
def index():
    # Traemos solo texto para velocidad máxima
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_id(r) for r in cursor]
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #F2F2F7; margin: 0; padding: 15px; }}
            .header {{ display: flex; justify-content: space-between; padding: 15px; background: white; border-radius: 15px; margin-bottom: 15px; }}
            .btn {{ padding: 15px; border-radius: 12px; text-decoration: none; font-weight: 700; display: inline-block; text-align: center; }}
            .btn-blue {{ background: #007AFF; color: white; width: 45%; }}
            .btn-white {{ background: white; color: #1C1C1E; border: 1px solid #D1D1D6; width: 45%; }}
            .list {{ background: white; border-radius: 15px; overflow: hidden; }}
            .item {{ padding: 15px; border-bottom: 1px solid #F2F2F7; cursor: pointer; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; align-items: flex-end; }}
            .modal-content {{ background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 20px; box-sizing: border-box; max-height: 85vh; overflow-y: auto; }}
            #map {{ height: 180px; width: 100%; border-radius: 12px; margin-top: 10px; display: none; }}
            .img-prev {{ width: 100%; border-radius: 10px; margin-top: 10px; display: none; }}
        </style>
    </head>
    <body>
        <div class="header"><b>Visitas a POC</b> 📍</div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
            <a href="/formulario" class="btn btn-blue">＋ REGISTRAR</a>
            <a href="/descargar" class="btn btn-white">💾 EXCEL</a>
        </div>
        <div class="list">
            {{% for r in registros %}}
            <div class="item" onclick='verDetalle({{{{ r|tojson }}}})'>
                <b>{{{{ r.pv }}}}</b><br>
                <small style="color: grey;">{{{{ r.fecha }}}} | {{{{ r.ciudad }}}}</small>
            </div>
            {{% endfor %}}
        </div>
        <div id="modal" class="modal" onclick="this.style.display='none'">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="cont"></div>
                <button onclick="document.getElementById('modal').style.display='none'" style="width:100%; padding:15px; margin-top:15px; border:none; border-radius:10px; background:#EEE;">Cerrar</button>
            </div>
        </div>
        {FOOTER_HTML}
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let map = null;
            function verDetalle(d) {{
                document.getElementById('cont').innerHTML = `
                    <h3>${{d.pv}}</h3>
                    <p><b>Dirección:</b> ${{d.direccion}}<br><b>Ciudad:</b> ${{d.ciudad}} | ${{d.departamento}}</p>
                    <button id="btn-f" onclick="loadF('${{d._id}}','${{d.ubicacion}}')" style="width:100%; padding:12px; color:#007AFF; border:1px solid #007AFF; background:none; border-radius:10px;">Ver Fotos y Mapa</button>
                    <div id="map"></div>
                    <img id="i1" class="img-prev"><img id="i2" class="img-prev">
                `;
                document.getElementById('modal').style.display='flex';
            }}
            async function loadF(id, coords) {{
                document.getElementById('btn-f').innerText = "Cargando...";
                const res = await fetch('/get_f/' + id);
                const j = await res.json();
                if(j.f1) {{ document.getElementById('i1').src=j.f1; document.getElementById('i1').style.display='block'; }}
                if(j.f2) {{ document.getElementById('i2').src=j.f2; document.getElementById('i2').style.display='block'; }}
                if(coords) {{
                    document.getElementById('map').style.display='block';
                    const c = coords.split(',').map(Number);
                    if(map) map.remove();
                    map = L.map('map').setView(c, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                    L.marker(c).addTo(map);
                }}
                document.getElementById('btn-f').style.display='none';
            }}
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/get_f/<id>')
def get_f(id):
    d = coleccion.find_one({{"_id": ObjectId(id)}}, {{"f_bmb": 1, "f_fachada": 1}})
    return jsonify({{"f1": d.get('f_bmb'), "f2": d.get('f_fachada')}})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        try:
            loc = request.form.get('ubicacion')
            dir, ciu, dep = "N/A", "N/A", "N/A"
            if loc:
                lat, lon = loc.split(',')
                g = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={{lat}}&lon={{lon}}", headers={{'User-Agent':'App'}}).json()
                dir = g.get('display_name','').split(',')[0]
                a = g.get('address', {{}})
                ciu = a.get('city') or a.get('town') or "N/A"
                dep = a.get('state', 'N/A')

            def enc(f):
                if f and f.filename != '':
                    return f"data:{{f.content_type}};base64,{{base64.b64encode(f.read()).decode()}}"
                return ""

            coleccion.insert_one({{
                "pv": request.form.get('pv'), "n_documento": request.form.get('n_documento'),
                "fecha": request.form.get('fecha'), "bmb": request.form.get('bmb'),
                "motivo": request.form.get('motivo'), "ubicacion": loc,
                "direccion": dir, "ciudad": ciu, "departamento": dep,
                "f_bmb": enc(request.files.get('f1')), "f_fachada": enc(request.files.get('f2'))
            }})
            return redirect('/?success=1')
        except: return redirect('/?error=1')
    
    return render_template_string(f"""
    <body style="font-family:sans-serif; background:#F2F2F7; padding:20px;">
        <div style="background:white; padding:20px; border-radius:15px;">
            <h2>Nuevo Registro</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; padding:12px; margin-bottom:10px;">
                <input type="text" name="n_documento" placeholder="Documento" required style="width:100%; padding:12px; margin-bottom:10px;">
                <input type="date" name="fecha" required style="width:100%; padding:12px; margin-bottom:10px;">
                <input type="text" name="bmb" placeholder="BMB (-1 = Positivo)" required style="width:100%; padding:12px; margin-bottom:10px;">
                <select name="motivo" style="width:100%; padding:12px; margin-bottom:10px;">
                    <option>Máquina Retirada</option><option>Fuera de Rango</option>
                </select>
                <button type="button" onclick="geo()" id="gb" style="width:100%; padding:12px; background:#5856D6; color:white; border:none; border-radius:10px;">📍 CAPTURAR GPS</button>
                <input type="hidden" name="ubicacion" id="u">
                <p>Foto BMB:</p><input type="file" name="f1" accept="image/*" capture="camera">
                <p>Foto Fachada:</p><input type="file" name="f2" accept="image/*" capture="camera">
                <button type="submit" style="width:100%; padding:15px; background:#34C759; color:white; border:none; border-radius:10px; margin-top:20px; font-weight:700;">GUARDAR</button>
            </form>
        </div>
        {FOOTER_HTML}
        <script>
            function geo() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('u').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gb').innerText = "✅ GPS LISTO";
                    document.getElementById('gb').style.background = "#34C759";
                }});
            }}
        </script>
    </body>
    """)

@app.route('/descargar')
def descargar():
    cursor = coleccion.find({}, {"f_bmb":0, "f_fachada":0})
    def gen():
        d = io.StringIO(); w = csv.writer(d)
        w.writerow(['PV','Doc','Fecha','BMB','Motivo','Direccion','Ciudad','Depto','GPS'])
        yield d.getvalue(); d.seek(0); d.truncate(0)
        for r in cursor:
            w.writerow([r.get('pv'),r.get('n_documento'),r.get('fecha'),r.get('bmb'),r.get('motivo'),r.get('direccion'),r.get('ciudad'),r.get('departamento'),r.get('ubicacion')])
            yield d.getvalue(); d.seek(0); d.truncate(0)
    return Response(gen(), mimetype='text/csv', headers={{"Content-Disposition":"attachment;filename=reporte.csv"}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
