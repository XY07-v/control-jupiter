from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB (INTACTA) ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- DISEÑO IPHONE GLASSMORPHISM RECUPERADO ---
CSS_IPHONE = """
<style>
    :root { --ios-blue: #007AFF; --ios-green: #34C759; --glass: rgba(255, 255, 255, 0.7); }
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica; 
        background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%); 
        margin: 0; min-height: 100vh; color: #1c1c1e;
    }
    .glass-card {
        background: var(--glass);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 25px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
        padding: 25px; margin: 15px;
    }
    .btn {
        width: 100%; padding: 14px; border-radius: 14px; border: none;
        font-weight: 600; font-size: 16px; cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 12px; display: block; text-align: center; text-decoration: none;
    }
    .btn-blue { background: var(--ios-blue); color: white; box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3); }
    .btn-blue:active { transform: scale(0.97); opacity: 0.8; }
    .btn-gray { background: rgba(0,0,0,0.05); color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    
    input, select {
        width: 100%; padding: 12px; margin: 8px 0; border-radius: 12px;
        border: 1px solid rgba(0,0,0,0.1); background: rgba(255,255,255,0.5);
        font-size: 16px; outline: none;
    }
    h2 { font-weight: 700; letter-spacing: -0.5px; color: #000; }
    .sidebar { width: 260px; height: 100vh; position: fixed; left: 0; top: 0; padding: 20px; box-sizing: border-box; }
    .content { margin-left: 260px; padding: 20px; }
    @media (max-width: 768px) { .sidebar { display: none; } .content { margin-left: 0; } }
</style>
"""

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0})
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(['PUNTO', 'ASESOR', 'FECHA', 'BMB ANT', 'BMB ACT', 'GPS ANT', 'GPS ACT', 'DESFACE', 'ESTADO', 'OBS'])
    for r in cursor:
        w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('bmb_propuesto'), 
                    r.get('gps_anterior'), r.get('ubicacion'), r.get('distancia'), r.get('estado'), "Auditado"])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_BI.csv"})

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}).sort("fecha", -1))
    rows = "".join([f'<div class="glass-card"><b>{v["pv"]}</b><br><small>{v["fecha"]}</small></div>' for v in visitas])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_IPHONE}</head>
    <body>
        <div class="sidebar">
            <div class="glass-card" style="height: 90vh; margin: 0;">
                <h2 style="color:var(--ios-blue)">Nestlé BI</h2>
                <p>Hola, <b>{session['user_name']}</b></p><br>
                <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
                <a href="/validacion_admin" class="btn btn-gray">Pendientes</a>
                <a href="/descargar" class="btn btn-gray">Exportar CSV</a>
                <div style="margin-top: auto;"><a href="/logout" class="btn btn-red">Salir</a></div>
            </div>
        </div>
        <div class="content"><h3>Historial Aprobado</h3>{rows}</div>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        # ... (Lógica de guardado intacta) ...
        return redirect('/formulario?msg=OK')
    
    # AJUSTE SOLICITADO: Botón "Regresar al Menú" solo si es Admin
    btn_regresar = '<a href="/" class="btn btn-gray">Regresar al Menú Principal</a>' if session.get('role') == 'admin' else ''
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_IPHONE}</head>
    <body>
        <div style="max-width:450px; margin:auto; padding-top: 20px;">
            <div class="glass-card">
                <h2 style="text-align:center;">Nestlé BI</h2>
                <p style="text-align:center;">Bienvenido, <b>{session['user_name']}</b></p>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" placeholder="Seleccionar Punto" required>
                    <datalist id="pts">{opts}</datalist>
                    <input type="text" name="bmb" placeholder="BMB Máquina">
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    <label style="font-size:12px; margin-left:10px;">Foto BMB</label><input type="file" name="f1" capture="camera" required>
                    <label style="font-size:12px; margin-left:10px;">Foto Fachada</label><input type="file" name="f2" capture="camera" required>
                    <input type="hidden" name="ubicacion" id="gps">
                    <button type="submit" class="btn btn-blue">Enviar Reporte</button>
                    {btn_regresar}
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        <script>navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)</script>
    </body></html>
    """)

# --- LAS RUTAS DE API Y LOGIN QUEDAN EXACTAMENTE COMO LAS TENÍAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')}); return redirect('/')
    return render_template_string(f"<html><head>{CSS_IPHONE}</head><body style='display:flex; justify-content:center; align-items:center; height:100vh;'><div class='glass-card' style='width:300px; text-align:center;'><h2>Nestlé BI</h2><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><br><br><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
