from flask import Flask, render_template_string, request, redirect, jsonify, Response, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_ultra_2026"

# --- CONFIGURACIÓN DE MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta'] # Nueva colección de referencia

# --- ESTILOS SISTEMA BI (FUTURISTA) ---
CSS_PRO = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F8FAFC; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 15px; transition: 0.3s; }
    .container { width: 100%; max-width: 1200px; margin: auto; }
    .card { background: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    .btn { padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; display: inline-block; border: none; cursor: pointer; text-align: center; transition: 0.2s; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-outline { background: white; color: var(--primary); border: 1px solid var(--primary); width: 100%; }
    .btn-admin { background: #10B981; color: white; } /* Verde para carga masiva */

    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1px solid #E2E8F0; border-radius: 10px; box-sizing: border-box; font-size: 16px; }
    input[readonly] { background: #F1F5F9; color: #64748B; border-style: dashed; }
    
    .list-item { background: white; padding: 20px; border-radius: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 5px solid var(--primary); }

    /* Modal Futurista con Blur */
    #modal { 
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0, 44, 95, 0.2); backdrop-filter: blur(12px); 
        z-index: 1000; align-items: center; justify-content: center; padding: 20px; 
    }
    .modal-content { 
        background: white; width: 100%; max-width: 900px; max-height: 90vh; 
        border-radius: 24px; padding: 35px; overflow-y: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.15); 
    }
    
    #map { height: 350px; width: 100%; border-radius: 15px; margin: 15px 0; display: none; }
    .img-tech { width: 100%; border-radius: 15px; margin-top: 15px; display: none; border: 1px solid #E2E8F0; }
    .photo-label { font-size: 13px; font-weight: 800; color: var(--dark); margin-top: 15px; display: block; text-transform: uppercase; }
</style>
"""

def check_auth(): return 'user_id' in session

# --- RUTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('nombre_completo', u)
            session['role'] = user.get('rol', 'asesor') # 'admin' o 'asesor'
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_PRO}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh; background:var(--dark);'><div class='card' style='width:320px; text-align:center;'><h2>BI Login</h2><form method='POST'><input type='text' name='usuario' placeholder='ID Usuario' required><input type='password' name='password' placeholder='Contraseña' required><button class='btn btn-primary'>Entrar al Sistema</button></form></div></body></html>")

@app.route('/')
def index():
    if not check_auth(): return redirect('/login')
    # Si es ASESOR, va directo al formulario
    if session.get('role') == 'asesor': return redirect('/formulario')
    
    # Si es ADMIN, ve la lista de registros
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = ""
    for r in cursor:
        rows += f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:var(--primary);">{r.get("bmb")}</div></div>'

    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_PRO}</head>
    <body>
        <div class="container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="color:var(--dark);">Consola Administrativa</h2>
                <div style="font-size:12px;">👤 {session['user_name']} (Admin) | <a href="/logout" style="color:red;">Salir</a></div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; margin-bottom:30px;">
                <a href="/formulario" class="btn btn-primary">＋ Nueva Visita</a>
                <a href="/descargar" class="btn btn-outline">📊 Excel</a>
                <button onclick="document.getElementById('modal_upload').style.display='flex'" class="btn btn-admin">📁 Carga Masiva PDV</button>
            </div>
            {rows}
        </div>

        <div id="modal" onclick="this.style.display='none'">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div id="det"></div>
                <button onclick="document.getElementById('modal').style.display='none'" class="btn btn-outline" style="margin-top:20px; color:red; border-color:red;">Cerrar Panel</button>
            </div>
        </div>

        <div id="modal_upload" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:2000; align-items:center; justify-content:center;">
            <div class="card" style="width:90%; max-width:400px;">
                <h3>Actualizar Puntos de Venta</h3>
                <p style="font-size:12px; color:gray;">Al subir, se borrarán todos los puntos anteriores.</p>
                <form action="/carga_masiva_puntos" method="POST" enctype="multipart/form-data">
                    <input type="file" name="file_csv" accept=".csv" required>
                    <button type="submit" class="btn btn-primary">Iniciar Carga</button>
                    <button type="button" onclick="document.getElementById('modal_upload').style.display='none'" class="btn btn-outline" style="margin-top:10px;">Cancelar</button>
                </form>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let mapObj = null;
            function verDetalle(id, pv, f, doc, mot, gps, bmb) {{
                document.getElementById('det').innerHTML = `
                    <h2 style="color:var(--dark); margin:0;">${{pv}}</h2>
                    <p><b>Registrado por:</b> ${{doc}}<br><b>Fecha:</b> ${{f}}<br><b>BMB:</b> ${{bmb}}<br><b>Motivo:</b> ${{mot}}</p>
                    <button id="btn_img" class="btn btn-primary" onclick="loadMedia('${{id}}','${{gps}}')">Ver Mapa y Fotos</button>
                    <div id="map"></div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <div><span class="photo-label" id="t1" style="display:none;">Foto BMB</span><img id="i1" class="img-tech"></div>
                        <div><span class="photo-label" id="t2" style="display:none;">Foto Fachada</span><img id="i2" class="img-tech"></div>
                    </div>`;
                document.getElementById('modal').style.display='flex';
            }}
            async function loadMedia(id, gps) {{
                document.getElementById('btn_img').innerText = "Procesando...";
                const res = await fetch('/get_img/'+id);
                const d = await res.json();
                if(d.f1) {{ document.getElementById('i1').src=d.f1; document.getElementById('i1').style.display='block'; document.getElementById('t1').style.display='block'; }}
                if(d.f2) {{ document.getElementById('i2').src=d.f2; document.getElementById('i2').style.display='block'; document.getElementById('t2').style.display='block'; }}
                if(gps) {{
                    document.getElementById('map').style.display='block';
                    const l = gps.split(',').map(Number);
                    if(mapObj) mapObj.remove();
                    mapObj = L.map('map').setView(l, 17);
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(mapObj);
                    L.marker(l).addTo(mapObj);
                    setTimeout(() => mapObj.invalidateSize(), 300);
                }}
                document.getElementById('btn_img').style.display='none';
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if not check_auth(): return redirect('/login')
    
    if request.method == 'POST':
        def b64(file):
            if file and file.filename != '':
                return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode()}"
            return ""
        f = request.form.get('fecha')
        visitas_col.insert_one({
            "pv": request.form.get('pv'), "n_documento": session['user_name'],
            "fecha": f, "mes": f[:7], "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'), "ubicacion": request.form.get('ubicacion'),
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        # Si es ASESOR, vuelve a abrir el formulario vacío
        if session.get('role') == 'asesor': return redirect('/formulario?success=true')
        return redirect('/')

    # Obtener lista de puntos para el buscador (Datalist)
    puntos_lista = puntos_col.find({}, {"Punto de Venta": 1})
    options = "".join([f'<option value="{p["Punto de Venta"]}">' for p in puntos_lista])
    
    today = datetime.now().strftime('%Y-%m-%d')
    success_msg = '<div style="background:#DCFCE7; color:#166534; padding:15px; border-radius:10px; margin-bottom:15px; font-weight:bold;">✅ Reporte Guardado. Iniciando nuevo...</div>' if request.args.get('success') else ""

    return render_template_string(f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_PRO}</head>
    <body onload="getGPS()">
        <div class="container" style="max-width:600px;">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                    {f'<a href="/" class="btn btn-outline" style="width:auto; padding:8px 15px;">← Volver</a>' if session.get('role')=='admin' else ''}
                    <h3 style="margin:0;">Registro de Visita</h3>
                    <a href="/logout" style="color:red; font-size:12px; text-decoration:none;">Cerrar Sesión</a>
                </div>
                {success_msg}
                <form method="POST" enctype="multipart/form-data">
                    <label style="font-size:12px; font-weight:bold;">Busca el Punto de Venta</label>
                    <input list="lista_puntos" name="pv" placeholder="Escribe el nombre del PDV..." required autocomplete="off">
                    <datalist id="lista_puntos">{options}</datalist>
                    
                    <label style="font-size:12px; font-weight:bold;">Asesor Responsable</label>
                    <input type="text" value="{session['user_name']}" readonly>
                    
                    <label style="font-size:12px; font-weight:bold;">Fecha Sistema</label>
                    <input type="date" name="fecha" value="{today}" required>
                    
                    <label style="font-size:12px; font-weight:bold;">Estado BMB</label>
                    <input type="text" name="bmb" placeholder="Dato BMB observado" required>
                    
                    <label style="font-size:12px; font-weight:bold;">Motivo</label>
                    <select name="motivo" required>
                        <option value="">Seleccione...</option><option>Máquina Retirada</option><option>Punto Cerrado</option><option>Fuera de Rango</option>
                    </select>
                    
                    <input type="hidden" name="ubicacion" id="gps_val" required>
                    <div id="gps_status" style="font-size:12px; color:orange; margin-bottom:15px;">📍 Sincronizando GPS...</div>
                    
                    <label class="photo-label">📸 Foto BMB (Obligatoria)</label>
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    
                    <label class="photo-label">📸 Foto Fachada (Obligatoria)</label>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    
                    <button type="submit" class="btn btn-primary" style="margin-top:30px; font-size:18px;">Enviar Reporte</button>
                </form>
            </div>
        </div>
        <script>
            function getGPS() {{
                navigator.geolocation.getCurrentPosition(p => {{
                    document.getElementById('gps_val').value = p.coords.latitude + "," + p.coords.longitude;
                    document.getElementById('gps_status').innerText = "✅ GPS Vinculado";
                    document.getElementById('gps_status').style.color = "green";
                }}, () => {{ alert("Activa el GPS para reportar."); }}, {{enableHighAccuracy: true}});
            }}
        </script>
    </body>
    </html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga_masiva_puntos():
    if not check_auth() or session.get('role') != 'admin': return redirect('/')
    file = request.files.get('file_csv')
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        # ELIMINAR DATOS ANTERIORES
        puntos_col.delete_many({})
        
        # INSERTAR NUEVOS
        puntos_col.insert_many(list(reader))
    return redirect('/')

@app.route('/get_img/<id>')
def get_img(id):
    d = visitas_col.find_one({"_id": ObjectId(id)}, {"f_bmb": 1, "f_fachada": 1})
    return jsonify({"f1": d.get('f_bmb'), "f2": d.get('f_fachada')})

@app.route('/descargar')
def descargar():
    if not check_auth() or session.get('role') != 'admin': return redirect('/')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    def gen():
        si = io.StringIO(); w = csv.writer(si)
        w.writerow(['Punto de Venta', 'Asesor', 'Fecha', 'Mes', 'BMB', 'Motivo', 'Ubicación'])
        yield si.getvalue(); si.seek(0); si.truncate(0)
        for r in cursor:
            w.writerow([r.get('pv',''), r.get('n_documento',''), r.get('fecha',''), r.get('mes',''), r.get('bmb',''), r.get('motivo',''), r.get('ubicacion','')])
            yield si.getvalue(); si.seek(0); si.truncate(0)
    return Response(gen(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_Visitas.csv"})

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
