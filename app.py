from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv

app = Flask(__name__)
# La Secret Key es necesaria para usar sessiones. Cámbiala por algo aleatorio.
app.secret_key = "nestle_secret_2026_control"

# --- CONFIGURACIÓN DE MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']
usuarios_col = db['usuarios'] # Tu nueva colección

# --- FUNCIONES DE UTILIDAD ---
def procesar_registro(doc):
    doc['_id'] = str(doc['_id'])
    val = str(doc.get('bmb', '')).strip()
    if val == "-1":
        doc['bmb_icon'] = "✅"
    elif val == "":
        doc['bmb_icon'] = "❌"
    else:
        doc['bmb_icon'] = val
    return doc

# Componente para el perfil del usuario (arriba a la derecha)
def get_user_header():
    if 'user_name' in session:
        return f"""
        <div style="position: absolute; top: 15px; right: 15px; background: #E5E5EA; padding: 8px 15px; border-radius: 20px; font-size: 13px; font-weight: 600;">
            👤 {session['user_name']} | <a href="/logout" style="color: #FF3B30; text-decoration: none;">Salir</a>
        </div>
        """
    return ""

FOOTER = """
<footer style="margin-top:30px; padding:20px; text-align:center; border-top:0.5px solid #C6C6C8; color:#8E8E93; font-size:12px;">
    Desarrollo de <b>Andres Vanegas - Business Intelligence</b> <br>
    © 2026 Todos los derechos reservados.
</footer>
"""

# --- RUTA 0: LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form.get('usuario')
        pass_input = request.form.get('password')
        
        # Buscamos al usuario en la BD
        user_db = usuarios_col.find_one({{"usuario": user_input, "password": pass_input}})
        
        if user_db:
            session['user_id'] = str(user_db['_id'])
            session['user_name'] = user_db.get('nombre_completo', user_input)
            return redirect('/')
        else:
            error = "Usuario o contraseña incorrectos ❌"

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #F2F2F7; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
            .login-card {{ background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 320px; text-align: center; }}
            input {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 14px; background: #007AFF; color: white; border: none; border-radius: 12px; font-weight: bold; margin-top: 15px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2 style="margin-bottom: 25px;">Nestlé Control ☕</h2>
            <form method="POST">
                <input type="text" name="usuario" placeholder="Usuario" required>
                <input type="password" name="password" placeholder="Contraseña" required>
                {f'<p style="color: red; font-size: 12px;">{error}</p>' if error else ''}
                <button type="submit">Iniciar Sesión</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- RUTA 1: LISTA PRINCIPAL ---
@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    
    cursor = coleccion.find({{}}, {{"f_bmb": 0, "f_fachada": 0}}).sort("fecha", -1)
    registros = [procesar_registro(r) for r in cursor]
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #F2F2F7; margin: 0; padding: 15px; position: relative; }}
            .header {{ padding: 15px; background: white; border-radius: 15px; margin-bottom: 15px; font-weight: bold; }}
            .nav {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            .btn {{ padding: 15px; border-radius: 12px; text-decoration: none; font-weight: 700; width: 46%; text-align: center; }}
            .btn-blue {{ background: #007AFF; color: white; }}
            .btn-white {{ background: white; color: #1C1C1E; border: 1px solid #D1D1D6; }}
            .list {{ background: white; border-radius: 15px; overflow: hidden; }}
            .item {{ padding: 15px; border-bottom: 1px solid #F2F2F7; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; align-items: flex-end; }}
            .modal-content {{ background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 90vh; overflow-y: auto; }}
            #map {{ height: 200px; width: 100%; border-radius: 12px; margin-top: 15px; display: none; }}
            .img-box {{ width: 100%; border-radius: 12px; margin-top: 10px; display: none; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        {get_user_header()}
        <div class="header">Visitas a POC - Control 📍</div>
        <div class="nav">
            <a href="/formulario" class="btn btn-blue">＋ REGISTRAR</a>
            <a href="/descargar" class="btn btn-white">💾 EXCEL</a>
        </div>
        <div class="list">
            {{% for r in registros %}}
            <div class="item" onclick='verDetalle({{{{ r|tojson }}}})'>
                <div>
                    <h4 style="margin:0;">{{{{ r.pv }}}}</h4>
                    <small style="color: #8E8E93;">{{{{ r.fecha }}}} | {{{{ r.mes }}}}</small>
                </div>
                <div style="font-size: 20px;">{{{{ r.bmb_icon }}}}</div>
            </div>
            {{% endfor %}}
        </div>

        <div id="modal" class="modal" onclick="this.style.display='none'">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="cont"></div>
                <button onclick="document.getElementById('modal').style.display='none'" style="width:100%; padding:15px; margin-top:20px; border:none; border-radius:12px; background:#F2F2F7; font-weight:700; color:red;">Cerrar</button>
            </div>
        </div>
        {FOOTER}

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapObj = null;
            function verDetalle(d) {{
                document.getElementById('cont').innerHTML = `
                    <h3>${{d.pv}}</h3>
                    <p><b>Mes:</b> ${{d.mes}}<br><b>Doc:</b> ${{d.n_documento}}<br><b>Motivo:</b> ${{d.motivo}}</p>
                    <button id="btn-load" onclick="getImages('${{d._id}}','${{d.ubicacion}}')" style="width:100%; padding:14px; color:#007AFF; border:2px solid #007AFF; background:none; border-radius:12px; font-weight:700;">👁️ VER FOTOS Y MAPA</button>
                    <div id="map"></div>
                    <img id="img1" class="img-box"><img id="img2" class="img-box">
                `;
                document.getElementById('modal').style.display='flex';
            }}

            async function getImages(id, coords) {{
                const b = document.getElementById('btn-load');
                b.innerText = "Cargando...";
                const res = await fetch('/get_img/' + id);
                const data = await res.json();
                if(data.f1) {{ document.getElementById('img1').src=data.f1; document.getElementById('img1').style.display='block'; }}
                if(data.f2) {{ document.getElementById('img2').src=data.f2; document.getElementById('img2').style.display='block'; }}
                if(coords) {{
                    document.getElementById('map').style.display='block';
                    const loc = coords.split(',').map(Number);
                    if(mapObj) mapObj.remove();
                    mapObj = L.map('map').setView(loc, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapObj);
                    L.marker(loc).addTo(mapObj);
                    setTimeout(() => mapObj.invalidateSize(), 300);
                }}
                b.style.display='none';
            }}
        </script>
    </body>
    </html>
    """, registros=registros)

# --- LAS DEMÁS RUTAS (FORMULARIO, GET_IMG, DESCARGAR) DEBEN INCLUIR LA VALIDACIÓN DE SESIÓN ---
@app.route('/get_img/<id>')
def get_img(id):
    if 'user_id' not in session: return jsonify({{}})
    doc = coleccion.find_one({{"_id": ObjectId(id)}}, {{"f_bmb": 1, "f_fachada": 1}})
    return jsonify({{"f1": doc.get('f_bmb'), "f2": doc.get('f_fachada')}})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        try:
            def to_base64(file):
                if file and file.filename != '':
                    return f"data:{{file.content_type}};base64,{{base64.b64encode(file.read()).decode()}}"
                return ""
            f = request.form.get('fecha')
            coleccion.insert_one({{
                "pv": request.form.get('pv'),
                "n_documento": request.form.get('n_documento'),
                "fecha": f,
                "mes": f[:7] if f else "",
                "bmb": request.form.get('bmb'),
                "motivo": request.form.get('motivo'),
                "ubicacion": request.form.get('ubicacion'),
                "f_bmb": to_base64(request.files.get('f1')),
                "f_fachada": to_base64(request.files.get('f2'))
            }})
            return redirect('/')
        except: return "Error al guardar."

    return render_template_string(f"""
    <body style="font-family:sans-serif; background:#F2F2F7; padding:20px;">
        {get_user_header()}
        <div style="background:white; padding:25px; border-radius:20px; max-width:500px; margin:auto; margin-top: 40px;">
            <a href="/" style="text-decoration:none; color:#007AFF; font-weight:bold;">✕ CANCELAR</a>
            <h2>Nueva Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px; box-sizing:border-box;">
                <input type="text" name="n_documento" placeholder="Documento" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px; box-sizing:border-box;">
                <input type="date" name="fecha" required style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px; box-sizing:border-box;">
                <input type="text" name="bmb" placeholder="BMB (-1 o vacío)" style="width:100%; padding:14px; margin-bottom:12px; border:1px solid #ddd; border-radius:10px; box-sizing:border-box;">
                <select name="motivo" style="width:100%; padding:14px; margin-bottom:12px; border-radius:10px; border:1px solid #ddd;">
                    <option>Máquina Retirada</option><option>Fuera de Rango</option><option>Punto Cerrado</option>
                </select>
                <button type="button" onclick="getGPS()" id="btn-gps" style="width:100%; padding:14px; background:#5856D6; color:white; border:none; border-radius:12px; font-weight:700;">📍 CAPTURAR GPS</button>
                <input type="hidden" name="ubicacion" id="gps_input">
                <p style="margin-top:15px; font-size:12px;">Foto BMB:</p><input type="file" name="f1" accept="image/*" capture="camera">
                <p style="margin-top:10px; font-size:12px;">Foto Fachada:</p><input type="file" name="f2" accept="image/*" capture="camera">
                <button type="submit" style="width:100%; padding:18px; background:#34C759; color:white; border:none; border-radius:15px; margin-top:25px; font-weight:800; width:100%;">GUARDAR REPORTE</button>
            </form>
        </div>
        {FOOTER}
        <script>
            function getGPS() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('gps_input').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('btn-gps').innerText = "✅ GPS LISTO";
                    document.getElementById('btn-gps').style.background = "#34C759";
                }});
            }}
        </script>
    </body>
    """)

@app.route('/descargar')
def descargar():
    if 'user_id' not in session: return redirect('/login')
    cursor = coleccion.find({{}}, {{"f_bmb": 0, "f_fachada": 0, "_id": 0}})
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Punto de Venta', 'Documento', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicacion'])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        for r in cursor:
            bmb_raw = str(r.get('bmb', '')).strip()
            estado = "POSITIVO (✅)" if bmb_raw == "-1" else "DEFICIT (❌)"
            writer.writerow([r.get('pv',''), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), estado, r.get('motivo',''), r.get('ubicacion','')])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={{"Content-Disposition":"attachment;filename=reporte_nestle.csv"}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
