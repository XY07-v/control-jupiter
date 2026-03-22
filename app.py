from flask import Flask, render_template_string, request, redirect, jsonify, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, base64, io, csv, requests

app = Flask(__name__)

# Conexión Segura
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']

def limpiar_id(doc):
    doc['_id'] = str(doc['_id'])
    return doc

# Firma de autoría para todas las vistas
FOOTER_HTML = """
<footer style="margin-top: 30px; padding: 20px; text-align: center; border-top: 0.5px solid #C6C6C8; color: #8E8E93; font-size: 12px;">
    Desarrollo de <b>Andres Vanegas - Business Inteligente</b> <br>
    © 2026 Todos los derechos reservados.
</footer>
"""

@app.route('/')
def index():
    # Solo traemos texto para que sea ultra rápido
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    registros = [limpiar_id(r) for r in cursor]
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Visitas a POC - Control</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root {{ --ios-blue: #007AFF; --bg: #F2F2F7; }}
            body {{ font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 12px; border-radius: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            .btn-new {{ background: var(--ios-blue); color: white; padding: 16px; border-radius: 14px; text-decoration: none; display: block; text-align: center; font-weight: 700; margin-bottom: 20px; }}
            .list {{ background: white; border-radius: 16px; overflow: hidden; }}
            .item {{ padding: 15px; border-bottom: 0.5px solid #E5E5EA; cursor: pointer; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: flex-end; }}
            .modal-content {{ background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 90vh; overflow-y: auto; }}
            #map {{ height: 200px; width: 100%; border-radius: 12px; margin-top: 15px; display: none; border: 1px solid #ddd; }}
            .img-res {{ width: 100%; border-radius: 12px; margin-top: 10px; display: none; }}
        </style>
    </head>
    <body>
        <div class="header">
            <span style="font-size: 24px;">💻</span>
            <div style="font-weight: 800; font-size: 16px;">Visitas a POC - Control</div>
            <span style="font-size: 24px; color: #FF3B30;">📍</span>
        </div>

        <a href="/formulario" class="btn-new">＋ NUEVO REPORTE</a>

        <div class="list">
            {{% for r in registros %}}
            <div class="item" onclick='abrirDetalle({{{{ r|tojson }}}})'>
                <h4 style="margin:0;">{{{{ r.pv }}}}</h4>
                <p style="margin:4px 0 0; font-size:13px; color:#8E8E93;">{{{{ r.fecha }}}} | {{{{ "✅ Positivo" if r.bmb == "-1" else r.bmb }}}}</p>
            </div>
            {{% endfor %}}
        </div>

        <div id="modal" class="modal" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="modalBody"></div>
                <button onclick="cerrarModal()" style="width:100%; margin-top:20px; padding:15px; border:none; background:#F2F2F7; border-radius:12px; font-weight:700; color:#FF3B30;">Cerrar Detalle</button>
            </div>
        </div>

        {FOOTER_HTML}

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapInstance = null;

            function abrirDetalle(data) {{
                const body = document.getElementById('modalBody');
                body.innerHTML = `
                    <h2 style="margin:0 0 15px 0;">${{data.pv}}</h2>
                    <div style="margin-bottom:10px; font-size:14px;">
                        <p><b>📍 Dirección:</b> ${{data.direccion || 'N/A'}}</p>
                        <p><b>🏙️ Ciudad:</b> ${{data.ciudad || '-'}} | <b>🗺️ Depto:</b> ${{data.departamento || '-'}}</p>
                        <p><b>📄 Documento:</b> ${{data.n_documento}}</p>
                        <p><b>📉 BMB:</b> ${{data.bmb === "-1" ? "Positivo" : data.bmb}}</p>
                    </div>
                    
                    <button id="btn-foto" onclick="cargarEvidencia('${{data._id}}', '${{data.ubicacion}}')" style="width:100%; padding:14px; border-radius:12px; border:2px solid #007AFF; color:#007AFF; background:none; font-weight:700;">🖼️ VER FOTOS Y MAPA</button>
                    
                    <div id="map"></div>
                    <img id="f1" class="img-res">
                    <img id="f2" class="img-res">
                `;
                document.getElementById('modal').style.display = 'flex';
            }}

            async function cargarEvidencia(id, coords) {{
                const btn = document.getElementById('btn-foto');
                btn.innerText = "⌛ Consultando base de datos...";
                
                try {{
                    const res = await fetch('/obtener_foto/' + id);
                    const fotos = await res.json();
                    
                    if(fotos.f_bmb) {{ document.getElementById('f1').src = fotos.f_bmb; document.getElementById('f1').style.display = 'block'; }}
                    if(fotos.f_fachada) {{ document.getElementById('f2').src = fotos.f_fachada; document.getElementById('f2').style.display = 'block'; }}
                    
                    if(coords) {{
                        const [lat, lng] = coords.split(',').map(Number);
                        document.getElementById('map').style.display = 'block';
                        if(!mapInstance) {{
                            mapInstance = L.map('map').setView([lat, lng], 16);
                            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapInstance);
                        }}
                        L.marker([lat, lng]).addTo(mapInstance);
                    }}
                    btn.style.display = 'none';
                }} catch(e) {{ btn.innerText = "❌ Error de conexión"; }}
            }}

            function cerrarModal() {{ 
                document.getElementById('modal').style.display = 'none';
                if(mapInstance) {{ mapInstance.remove(); mapInstance = null; }}
            {{
        </script>
    </body>
    </html>
    """, registros=registros)

@app.route('/obtener_foto/<id>')
def obtener_foto(id):
    doc = coleccion.find_one({{"_id": ObjectId(id)}}, {{"f_bmb": 1, "f_fachada": 1}})
    return jsonify({{"f_bmb": doc.get('f_bmb', ''), "f_fachada": doc.get('f_fachada', '')}})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        try:
            lat_lng = request.form.get('ubicacion')
            direccion, ciudad, depto = "N/A", "N/A", "N/A"
            
            if lat_lng:
                lat, lon = lat_lng.split(',')
                headers = {{'User-Agent': 'NestlePOC/1.0'}}
                geo_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={{lat}}&lon={{lon}}", headers=headers).json()
                direccion = geo_res.get('display_name', '').split(',')[0]
                addr = geo_res.get('address', {{}})
                ciudad = addr.get('city') or addr.get('town') or "N/A"
                depto = addr.get('state', 'N/A')

            f_bmb = f"data:{{request.files['f_bmb'].content_type}};base64,{{base64.b64encode(request.files['f_bmb'].read()).decode('utf-8')}}" if 'f_bmb' in request.files and request.files['f_bmb'].filename != '' else ""
            f_fachada = f"data:{{request.files['f_fachada'].content_type}};base64,{{base64.b64encode(request.files['f_fachada'].read()).decode('utf-8')}}" if 'f_fachada' in request.files and request.files['f_fachada'].filename != '' else ""

            coleccion.insert_one({{
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
            }})
            return redirect('/?success=1')
        except:
            return redirect('/?error=1')
    
    return render_template_string(f"""
    <body style="font-family:sans-serif; background:#F2F2F7; padding:20px;">
        <div style="max-width:500px; margin:auto; background:white; padding:25px; border-radius:20px; box-shadow:0 4px 15px rgba(0,0,0,0.05);">
            <a href="/" style="text-decoration:none; color:#007AFF; font-weight:700;">✕ CANCELAR</a>
            <h2 style="margin-top:15px;">Nueva Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px;">
                <input type="text" name="n_documento" placeholder="N. Documento" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px;">
                <input type="date" name="fecha" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px;">
                <input type="text" name="bmb" placeholder="BMB (-1 = Positivo)" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px;">
                
                <select name="motivo" style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px;">
                    <option>Máquina Retirada</option>
                    <option>Fuera de Rango</option>
                    <option>Punto Cerrado</option>
                </select>

                <button type="button" onclick="getGPS()" id="gps-btn" style="width:100%; padding:14px; background:#5856D6; color:white; border:none; border-radius:12px; font-weight:700;">📍 CAPTURAR GPS</button>
                <input type="hidden" name="ubicacion" id="ub">

                <p style="font-size:12px; color:#888; margin-top:15px;">FOTO BMB</p>
                <input type="file" name="f_bmb" accept="image/*" capture="camera">
                
                <p style="font-size:12px; color:#888; margin-top:10px;">FOTO FACHADA</p>
                <input type="file" name="f_fachada" accept="image/*" capture="camera">

                <button type="submit" style="width:100%; padding:18px; background:#34C759; color:white; border:none; border-radius:15px; font-weight:800; font-size:16px; margin-top:20px;">GUARDAR VISITA</button>
            </form>
        </div>
        {FOOTER_HTML}
        <script>
            function getGPS() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('ub').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps-btn').innerText = "✅ GPS CAPTURADO";
                    document.getElementById('gps-btn').style.background = "#34C759";
                }});
            }}
        </script>
    </body>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
