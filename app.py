from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv, math, json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "nestle_bi_nueva_era_2026_ytmei"
app.permanent_session_lifetime = timedelta(days=1)

# ======================================================
# 1. CONEXIÓN AL NUEVO CLÚSTER (Reemplaza <db_password>)
# ======================================================
MONGO_URI = "mongodb+srv://control-jupiter:<db_password>@cluster0.ytmei.mongodb.net/NestleDB?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CREAR USUARIO INICIAL SI EL CLÚSTER ESTÁ VACÍO ---
if usuarios_col.count_documents({}) == 0:
    usuarios_col.insert_one({
        "nombre_completo": "Administrador Sistema",
        "usuario": "admin",
        "password": "123",  # <--- USA ESTO PARA TU PRIMER LOGIN
        "rol": "admin"
    })
    print(">>> NUEVO CLÚSTER DETECTADO: Usuario 'admin' creado exitosamente.")

# --- FUNCIONES DE APOYO ---
def calcular_distancia(pos1, pos2):
    if not pos1 or not pos2 or pos1 == "0,0" or pos2 == "0,0": return 0
    try:
        lat1, lon1 = map(float, str(pos1).split(','))
        lat2, lon2 = map(float, str(pos2).split(','))
        R = 6371000 
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)
    except: return 0

CSS_FIXED = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; --sidebar-w: 250px; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; display: flex; color: #1c1c1e; }
    .sidebar { width: var(--sidebar-w); background: white; height: 100vh; position: fixed; border-right: 0.5px solid #d1d1d6; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 1000; }
    .main-content { margin-left: var(--sidebar-w); flex: 1; padding: 20px; width: calc(100% - var(--sidebar-w)); min-height: 100vh; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 0.5px solid rgba(0,0,0,0.1); }
    .btn { width: 100%; padding: 12px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-bottom: 10px; font-size: 14px; text-align: center; display: block; box-sizing: border-box; text-decoration: none; transition: 0.2s; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; }
    .btn-red { background: #FF3B30; color: white; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-content { background: white; margin: 5% auto; width: 90%; max-width: 600px; border-radius: 25px; padding: 25px; max-height: 85vh; overflow-y: auto; position: relative; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #F2F2F7; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; }
    @media (max-width: 768px) { .sidebar { width: 0; padding: 0; display:none; } .main-content { margin-left: 0; width: 100%; } }
</style>
"""

# ... [MANTENER AQUÍ TODAS LAS RUTAS: index, formulario, validacion_admin, etc.] ...
# Nota: Las rutas de tu código original son correctas y funcionarán con este nuevo clúster.

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session.get('role') == 'asesor': return redirect('/formulario')
    visitas = list(visitas_col.find({"estado": {"$ne": "Pendiente"}}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(50))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v["pv"]}</b><br><small>{v["fecha"]} - {v["n_documento"]}</small></div>' for v in visitas])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />{CSS_FIXED}</head>
    <body>
        <div class="sidebar">
            <h2 style="font-size:18px; color:var(--ios-blue);">Nestlé BI</h2>
            <p style="font-size:13px; font-weight:bold;">{session.get('user_name')}</p>
            <hr style="width:100%; border:0.5px solid #eee; margin:15px 0;">
            <a href="/formulario" class="btn btn-blue">Nuevo Reporte</a>
            <a href="/validacion_admin" class="btn btn-light" style="color:#FF9500;">Pendientes</a>
            <button class="btn btn-light" onclick="openM('m_puntos')">Puntos de Venta</button>
            <button class="btn btn-light" onclick="openM('m_users')">Usuarios</button>
            <button class="btn btn-light" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-light">Exportar Datos</a>
            <div style="margin-top:auto;"><a href="/logout" class="btn btn-red">Cerrar Sesión</a></div>
        </div>
        <div class="main-content"><h3>Historial de Visitas (Nuevos Datos)</h3>{rows or '<p>No hay visitas registradas en este clúster.</p>'}</div>
        <div id="m_puntos" class="modal"><div class="modal-content" id="cont_p_modal"></div></div>
        <div id="m_users" class="modal"><div class="modal-content" id="cont_u_modal"></div></div>
        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-light" onclick="closeM()" style="width:100px; float:right;">Cerrar</button>
            <h3>Carga Masiva de Puntos</h3>
            <p style="font-size:11px;">Sube el CSV de tu Drive para alimentar el nuevo clúster.</p>
            <input type="file" id="f_csv" accept=".csv"><button class="btn btn-blue" onclick="subirCSV()">Procesar CSV</button>
        </div></div>
        <div id="m_det" class="modal"><div class="modal-content" id="det_body"></div></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // ... [Mantener scripts de JavaScript originales aquí] ...
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargaP(); if(id=='m_users') cargaU(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}
            async function subirCSV() {{
                const f = document.getElementById('f_csv').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); location.reload();
            }}
            async function verVisita(id) {{
                openM('m_det'); const res = await fetch('/get_img/'+id); const d = await res.json();
                document.getElementById('det_body').innerHTML = `<button class="btn btn-light" onclick="closeM()">Cerrar</button><div id="map" style="height:200px; border-radius:15px; margin:10px 0;"></div><img src="${{d.f1}}" style="width:100%; margin-bottom:10px;"><img src="${{d.f2}}" style="width:100%;">`;
                if(d.gps) {{
                   const c = d.gps.split(','); const m = L.map('map').setView(c, 15); L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(m); L.marker(c).addTo(m);
                }}
            }}
        </script>
    </body></html>
    """)

# ... [PEGAR AQUÍ EL RESTO DE TUS RUTAS ORIGINALES: /login, /api/puntos, etc.] ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
