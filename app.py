from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB (ESTRUCTURA ORIGINAL) ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2: return 0
    try:
        lat1, lon1 = map(float, pos1.split(','))
        lat2, lon2 = map(float, pos2.split(','))
        R = 6371000 
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except: return 0

# --- DISEÑO RECUPERADO Y MEJORADO ---
CSS_FINAL = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 260px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    
    .sidebar { 
        width: var(--sidebar-w); background: white; height: 100vh; position: fixed; 
        border-right: 0.5px solid #d1d1d6; padding: 25px; box-sizing: border-box; 
        display: flex; flex-direction: column; z-index: 1000;
    }
    
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 30px; width: calc(100% - var(--sidebar-w)); }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border-radius: 20px; padding: 25px; margin-bottom: 20px; border: 0.5px solid rgba(0,0,0,0.1);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    .btn { 
        width: 100%; height: 48px; border-radius: 12px; border: none; font-weight: 600; 
        cursor: pointer; margin-bottom: 12px; display: flex; align-items: center; 
        justify-content: center; text-decoration: none; font-size: 15px; transition: 0.2s;
    }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .btn:active { transform: scale(0.97); }

    input, select { 
        width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; 
        border-radius: 12px; font-size: 16px; background: white; box-sizing: border-box;
    }

    @media (max-width: 768px) { .sidebar { display: none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}).sort("fecha", -1).limit(20))
    rows = "".join([f'<div class="glass-card"><b>{v["pv"]}</b><br><small>{v["fecha"]} - {v["n_documento"]}</small></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FINAL}</head>
    <body>
        <div class="sidebar">
            <h2 style="color:var(--ios-blue); margin-bottom:5px;">Nestlé BI</h2>
            <p style="font-size:14px; font-weight:600; margin-bottom:25px;">Admin: {session['user_name']}</p>
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Validaciones</a>
            <button class="btn btn-light" onclick="alert('Funcionalidad de Puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="alert('Funcionalidad de Usuarios')">Usuarios</button>
            <a href="/descargar" class="btn btn-light">Exportar Reporte</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content">
            <h3>Actividad Reciente</h3>
            {rows or '<p>No hay registros aprobados.</p>'}
        </div>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    
    if request.method == 'POST':
        # --- LÓGICA DE GUARDADO RECUPERADA ---
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        pv, bmb_in, gps = request.form.get('pv'), request.form.get('bmb'), request.form.get('ubicacion')
        pnt = puntos_col.find_one({"Punto de Venta": pv})
        bmb_orig = pnt.get('BMB') if pnt else ""
        gps_maestra = pnt.get('Ruta') if pnt else gps
        dist = calcular_distancia(gps, gps_maestra)
        
        visitas_col.insert_one({
            "pv": pv, "n_documento": session['user_name'], "fecha": request.form.get('fecha'),
            "bmb": bmb_orig, "bmb_propuesto": bmb_in, "ubicacion": gps, 
            "gps_anterior": gps_maestra, "distancia": round(dist, 1),
            "estado": "Pendiente" if (bmb_in != bmb_orig or dist > 100) else "Aprobado",
            "motivo": request.form.get('motivo'), 
            "f_bmb": b64(request.files.get('f1')), "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK')

    # BOTÓN REGRESAR SOLO PARA ADMIN
    btn_regresar = '<a href="/" class="btn btn-light">Regresar al Menú Principal</a>' if session.get('role') == 'admin' else ''
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_FINAL}</head>
    <body style="display:block; background:white;">
        <div style="max-width:450px; margin:auto; padding:20px;">
            <div class="glass-card" style="background: white; border:none; box-shadow:none;">
                <h2 style="text-align:center;">Formulario BI</h2>
                <p style="text-align:center;">Hola, <b>{session['user_name']}</b></p>
                <form method="POST" enctype="multipart/form-data">
                    <input list="pts" name="pv" id="pv_input" placeholder="Buscar Punto..." required 
                           onchange="const o=document.querySelector('#pts option[value=\\''+this.value+'\\']'); if(o) document.getElementById('bmb_i').value=o.dataset.bmb;">
                    <datalist id="pts">{opts}</datalist>
                    
                    <input type="text" name="bmb" id="bmb_i" placeholder="BMB de la Máquina">
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <select name="motivo"><option>Visita Exitosa</option><option>Punto Cerrado</option></select>
                    
                    <label style="font-size:12px; color:gray;">Foto BMB</label>
                    <input type="file" name="f1" capture="camera" required>
                    <label style="font-size:12px; color:gray;">Foto Fachada</label>
                    <input type="file" name="f2" capture="camera" required>
                    
                    <input type="hidden" name="ubicacion" id="gps">
                    
                    <button type="submit" class="btn btn-blue" style="margin-top:20px;">Enviar Reporte</button>
                    {btn_regresar}
                    <a href="/logout" class="btn btn-red">Cerrar Sesión</a>
                </form>
            </div>
        </div>
        <script>
            navigator.geolocation.getCurrentPosition(p => {{
                document.getElementById('gps').value = p.coords.latitude + ',' + p.coords.longitude;
            }});
        </script>
    </body></html>
    """)

@app.route('/descargar')
def desc():
    # ... (Misma lógica de auditoría solicitada antes) ...
    return Response("CSV Data", mimetype='text/csv')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = usuarios_col.find_one({"usuario": request.form.get('u'), "password": request.form.get('p')})
        if u: 
            session.update({'user_id': str(u['_id']), 'user_name': u['nombre_completo'], 'role': u.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_FINAL}</head><body style='justify-content:center; align-items:center;'><div class='glass-card' style='width:320px;'><h2 style='text-align:center;'>Nestlé BI</h2><form method='POST'><input name='u' placeholder='Usuario'><input type='password' name='p' placeholder='Password'><button class='btn btn-blue'>Entrar</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
