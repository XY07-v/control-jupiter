from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv

app = Flask(__name__)
app.secret_key = "nestle_futuristic_control_2026"

# --- CONFIGURACIÓN DE MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
coleccion = db['visitas']
usuarios_col = db['usuarios']

# --- ESTILOS COMUNES (CSS FUTURISTA) ---
CSS_PRO = """
<style>
    :root {
        --primary: #005596; /* Azul Manpower */
        --dark: #002C5F;
        --bg: #F8FAFC;
        --glass: rgba(255, 255, 255, 0.9);
        --accent: #00A9E0;
    }
    body { 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
        background: var(--bg); 
        margin: 0; 
        color: #1E293B;
        line-height: 1.6;
    }
    .container { 
        width: 100%; 
        max-width: 1200px; 
        margin: auto; 
        padding: 20px; 
        box-sizing: border-box; 
    }
    .card { 
        background: var(--glass); 
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 16px; 
        padding: 25px; 
        box-shadow: 0 4px 15px rgba(0, 44, 95, 0.05);
        margin-bottom: 20px;
    }
    .btn { 
        padding: 14px 20px; 
        border-radius: 12px; 
        text-decoration: none; 
        font-weight: 600; 
        text-align: center; 
        display: inline-block;
        transition: all 0.3s ease;
        border: none;
        cursor: pointer;
    }
    .btn-primary { background: var(--primary); color: white; box-shadow: 0 4px 10px rgba(0, 85, 150, 0.3); }
    .btn-primary:hover { transform: translateY(-2px); background: var(--dark); }
    
    .btn-outline { background: white; color: var(--primary); border: 1px solid var(--primary); }
    
    input, select { 
        width: 100%; 
        padding: 14px; 
        margin: 10px 0; 
        border: 1px solid #E2E8F0; 
        border-radius: 10px; 
        background: white;
        font-size: 16px;
        box-sizing: border-box;
    }
    input:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 3px rgba(0, 85, 150, 0.1); }
    
    .header-main { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
    .title-pro { font-size: 24px; font-weight: 800; color: var(--dark); margin: 0; text-transform: capitalize; }
    
    .list-container { display: grid; gap: 15px; width: 100%; }
    .list-item { 
        background: white; 
        padding: 20px; 
        border-radius: 14px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-left: 5px solid var(--primary);
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        cursor: pointer;
        transition: 0.2s;
    }
    .list-item:hover { transform: scale(1.01); box-shadow: 0 5px 15px rgba(0,0,0,0.05); }

    .user-tag { background: var(--dark); color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; }
    
    #map { height: 250px; width: 100%; border-radius: 15px; margin: 15px 0; border: 1px solid #ddd; }
    .img-tech { width: 100%; border-radius: 12px; margin-top: 15px; border: 2px solid #F1F5F9; display: none; }
</style>
"""

# --- FUNCIONES ---
def format_cap(text):
    return str(text).title() if text else ""

def check_auth():
    if 'user_id' not in session: return False
    return True

# --- RUTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session['user_id'], session['user_name'] = str(user['_id']), user.get('nombre_completo', u)
            return redirect('/')
        error = "Credenciales no reconocidas por el sistema."

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {CSS_PRO}
    </head>
    <body style="display:flex; align-items:center; justify-content:center; height:100vh; background: linear-gradient(135deg, #002C5F 0%, #005596 100%);">
        <div class="card" style="width: 320px; text-align: center;">
            <h2 style="color: var(--dark); margin-bottom:30px;">Sistema Inteligente</h2>
            <form method="POST">
                <input type="text" name="usuario" placeholder="Identificador de Usuario" required>
                <input type="password" name="password" placeholder="Código de Acceso" required>
                <p style="color: #E11D48; font-size: 13px;">{error}</p>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Sincronizar Acceso</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/')
def index():
    if not check_auth(): return redirect('/login')
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    
    rows = ""
    for r in cursor:
        val = str(r.get('bmb', '')).strip()
        icon = "✅" if val == "-1" else "❌"
        rows += f"""
        <div class="list-item" onclick='verDetalle({jsonify(str(r["_id"]))}, "{format_cap(r.get("pv"))}", "{r.get("fecha")}", "{r.get("mes")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}")'>
            <div>
                <div style="font-weight:700; color:var(--dark);">{format_cap(r.get('pv'))}</div>
                <div style="font-size:12px; color:#64748B;">{r.get('fecha')} | {r.get('mes')}</div>
            </div>
            <div style="font-size:22px;">{icon}</div>
        </div>
        """

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        {CSS_PRO}
    </head>
    <body>
        <div class="container">
            <div class="header-main">
                <h1 class="title-pro">Panel De Control</h1>
                <div class="user-tag">👤 {session['user_name']}</div>
            </div>

            <div style="display:flex; gap:15px; margin-bottom:30px;">
                <a href="/formulario" class="btn btn-primary" style="flex:1;">Nuevo Registro</a>
                <a href="/descargar" class="btn btn-outline" style="flex:1;">Exportar Datos</a>
            </div>

            <div class="list-container">{rows}</div>
        </div>

        <div id="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,44,95,0.4); z-index:1000; align-items:center; justify-content:center; padding:20px; box-sizing:border-box;">
            <div class="card" style="width:100%; max-width:500px; margin:0; position:relative;">
                <div id="detail_content"></div>
                <button onclick="document.getElementById('modal').style.display='none'" class="btn btn-outline" style="width:100%; margin-top:20px; color:#E11D48; border-color:#E11D48;">Cerrar Vista</button>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapObj = null;
            function verDetalle(id, pv, fecha, mes, doc, motivo, coords) {{
                document.getElementById('detail_content').innerHTML = `
                    <h2 style="color:var(--dark); margin-top:0;">${{pv}}</h2>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:14px; color:#475569;">
                        <div><b>Fecha:</b><br>${{fecha}}</div>
                        <div><b>Mes:</b><br>${{mes}}</div>
                        <div><b>Documento:</b><br>${{doc}}</div>
                        <div><b>Motivo:</b><br>${{motivo}}</div>
                    </div>
                    <button id="ld" onclick="getMedia('${{id}}','${{coords}}')" class="btn btn-primary" style="width:100%; margin-top:20px; font-size:13px;">Cargar Inteligencia Visual</button>
                    <div id="map"></div>
                    <img id="im1" class="img-tech"><img id="im2" class="img-tech">
                `;
                document.getElementById('modal').style.display='flex';
            }}

            async function getMedia(id, coords) {{
                document.getElementById('ld').innerText = "Procesando imágenes...";
                const r = await fetch('/get_img/' + id);
                const d = await r.json();
                if(d.f1) {{ document.getElementById('im1').src=d.f1; document.getElementById('im1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('im2').src=d.f2; document.getElementById('im2').style.display='block'; }}
                if(coords) {{
                    document.getElementById('map').style.display='block';
                    const loc = coords.split(',').map(Number);
                    if(mapObj) mapObj.remove();
                    mapObj = L.map('map').setView(loc, 16);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapObj);
                    L.marker(loc).addTo(mapObj);
                    setTimeout(() => mapObj.invalidateSize(), 400);
                }}
                document.getElementById('ld').style.display='none';
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/get_img/<id>')
def get_img(id):
    if not check_auth(): return jsonify({})
    d = coleccion.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if not check_auth(): return redirect('/login')
    if request.method == 'POST':
        def b64(file):
            if file and file.filename != '':
                return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode()}"
            return ""
        f = request.form.get('fecha')
        coleccion.insert_one({
            "pv": request.form.get('pv'), "n_documento": request.form.get('n_documento'),
            "fecha": f, "mes": f[:7] if f else "", "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/')

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_PRO}</head>
    <body>
        <div class="container" style="max-width:500px;">
            <div class="card">
                <a href="/" style="color:var(--primary); font-size:14px; text-decoration:none;">✕ Cancelar</a>
                <h2 style="color:var(--dark); margin:20px 0;">Nueva Visita</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="pv" placeholder="Punto De Venta" required>
                    <input type="text" name="n_documento" placeholder="Número De Documento" required>
                    <input type="date" name="fecha" required>
                    <input type="text" name="bmb" placeholder="Bmb">
                    <select name="motivo">
                        <option>Máquina Retirada</option><option>Fuera De Rango</option><option>Punto Cerrado</option>
                    </select>
                    <button type="button" onclick="geo()" id="gb" class="btn btn-outline" style="width:100%; margin:10px 0;">📍 Vincular Gps</button>
                    <input type="hidden" name="ubicacion" id="ui">
                    <p style="font-size:12px; color:#64748B; margin-bottom:5px;">Registro Fotográfico Bmb</p>
                    <input type="file" name="f1" accept="image/*" capture="camera">
                    <p style="font-size:12px; color:#64748B; margin:10px 0 5px;">Registro Fotográfico Fachada</p>
                    <input type="file" name="f2" accept="image/*" capture="camera">
                    <button type="submit" class="btn btn-primary" style="width:100%; margin-top:20px; padding:18px;">Finalizar Reporte</button>
                </form>
            </div>
        </div>
        <script>
            function geo() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('ui').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gb').innerText = "✅ Ubicación Vinculada";
                    document.getElementById('gb').style.background = "#F1F5F9";
                }});
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/descargar')
def descargar():
    if not check_auth(): return redirect('/login')
    cursor = coleccion.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    def gen():
        si = io.StringIO(); w = csv.writer(si)
        w.writerow(['Punto De Venta', 'Documento', 'Fecha', 'Mes', 'Bmb', 'Motivo', 'Ubicación'])
        yield si.getvalue(); si.seek(0); si.truncate(0)
        for r in cursor:
            b = str(r.get('bmb','')).strip()
            st = "Positivo (✅)" if b == "-1" else "Déficit (❌)"
            w.writerow([format_cap(r.get('pv','')), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), st, r.get('motivo',''), r.get('ubicacion','')])
            yield si.getvalue(); si.seek(0); si.truncate(0)
    return Response(gen(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_Inteligente.csv"})

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
