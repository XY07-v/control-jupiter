from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_final_v5"

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- CSS INTEGRADO (SIN CAMBIOS) ---
CSS_BI = """
<style>
    :root { --primary: #005596; --dark: #002C5F; --bg: #F1F5F9; --sidebar-w: 280px; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; }
    .sidebar { position: fixed; left: -280px; top: 0; width: var(--sidebar-w); height: 100%; background: var(--dark); color: white; transition: 0.3s; z-index: 2100; padding: 25px; box-sizing: border-box; }
    .sidebar.active { left: 0; }
    .nav-link { display: block; color: #E2E8F0; text-decoration: none; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; border: none; background: transparent; width: 100%; text-align: left; font-size: 16px; }
    .nav-link:hover { background: rgba(255,255,255,0.1); color: white; }
    .profile-badge { position: absolute; top: 20px; right: 20px; background: white; padding: 8px 15px; border-radius: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: flex; flex-direction: column; align-items: flex-end; z-index: 1000; }
    .profile-badge b { color: var(--dark); font-size: 14px; }
    .profile-badge small { color: var(--primary); font-size: 11px; text-transform: uppercase; font-weight: bold; }
    .main-content { width: 100%; padding: 20px; transition: 0.3s; position: relative; }
    .header-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; margin-top: 10px; }
    .menu-toggle { background: var(--primary); color: white; border: none; padding: 12px 18px; border-radius: 10px; cursor: pointer; font-size: 20px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.3); backdrop-filter: blur(10px); z-index: 2000; }
    .modal-box { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 700px; z-index: 2500; background: white; border-radius: 24px; padding: 30px; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 40px rgba(0,0,0,0.2); box-sizing: border-box; }
    .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); box-sizing: border-box; width: 100%; }
    .btn { width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s; text-decoration: none; display: inline-block; font-size: 14px; box-sizing: border-box; margin-top: 10px; text-align: center; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-gray { background: #64748B; color: white; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1.5px solid #E2E8F0; border-radius: 10px; box-sizing: border-box; font-family: inherit; }
    .list-item { background: white; padding: 18px; border-radius: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-left: 5px solid var(--primary); }
    .debug-box { background: #1e1e1e; color: #adff2f; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 11px; margin-top: 15px; display: none; white-space: pre; }
</style>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('usuario'), request.form.get('password')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user.get('nombre_completo'), 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"<html><head>{CSS_BI}</head><body style='justify-content:center; align-items:center; background:var(--dark); display:flex; height:100vh;'><div class='card' style='width:340px; text-align:center;'><h2>VISITAS A POC</h2><form method='POST'><input type='text' name='usuario' placeholder='Usuario'><input type='password' name='password' placeholder='Password'><button class='btn btn-primary'>Entrar</button></form></div></body></html>")

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1)
    rows = "".join([f'<div class="list-item" onclick=\'verDetalle("{r["_id"]}", "{r.get("pv")}", "{r.get("fecha")}", "{r.get("n_documento")}", "{r.get("motivo")}", "{r.get("ubicacion")}", "{r.get("bmb")}", "{r.get("Nota","")}")\'><div><b>{r.get("pv")}</b><br><small>{r.get("fecha")}</small></div><div style="color:var(--primary); font-weight:bold;">{r.get("bmb")}</div></div>' for r in cursor])
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body>
        <div id="overlay" class="overlay" onclick="closeAll()"></div>
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div id="sidebar" class="sidebar">
            <h3 style="color:#FFF;">Andres BI</h3>
            <a href="/formulario" class="nav-link">📝 Nuevo Reporte</a>
            <div class="nav-link" onclick="openModal('modal_csv')">⚙️ Carga Puntos PDV</div>
            <a href="/logout" class="nav-link" style="color:#F87171; margin-top:40px;">🚪 Cerrar Sesión</a>
        </div>
        <div class="main-content">
            <div class="header-bar"><button class="menu-toggle" onclick="toggleMenu()">☰</button><h2 style="margin:0;">Bienvenido, {session['user_name']}</h2></div>
            <div id="lista">{rows}</div>
        </div>
        <div id="modal_detalle" class="modal-box"><div id="det_body"></div><button onclick="closeModal('modal_detalle')" class="btn btn-gray">Regresar</button></div>
        <div id="modal_csv" class="modal-box">
            <h3>Carga Masiva</h3>
            <input type="file" id="fileCsv" accept=".csv"><div id="debug" class="debug-box"></div>
            <button type="button" onclick="subirCsv()" class="btn btn-primary">Actualizar Base</button>
            <button onclick="closeModal('modal_csv')" class="btn btn-gray">Cerrar</button>
        </div>
        <script>
            function toggleMenu() {{ document.getElementById('sidebar').classList.toggle('active'); document.getElementById('overlay').style.display = document.getElementById('sidebar').classList.contains('active') ? 'block' : 'none'; }}
            function openModal(id) {{ closeAll(); document.getElementById('overlay').style.display = 'block'; document.getElementById(id).style.display = 'block'; }}
            function closeModal(id) {{ document.getElementById(id).style.display = 'none'; document.getElementById('overlay').style.display = 'none'; }}
            function closeAll() {{ document.querySelectorAll('.modal-box').forEach(m => m.style.display = 'none'); document.getElementById('sidebar').classList.remove('active'); document.getElementById('overlay').style.display = 'none'; }}
            function verDetalle(id, pv, f, doc, mot, gps, bmb, nota) {{ 
                document.getElementById('det_body').innerHTML = `<h3>${{pv}}</h3><p><b>BMB:</b> ${{bmb}}</p><p><b>Nota:</b> ${{nota}}</p><p><b>Asesor:</b> ${{doc}}</p>`; 
                openModal('modal_detalle'); 
            }}
            async function subirCsv() {{
                const formData = new FormData(); formData.append('file_csv', document.getElementById('fileCsv').files[0]);
                const res = await fetch('/carga_masiva_puntos', {{ method: 'POST', body: formData }});
                const data = await res.json();
                document.getElementById('debug').style.display = 'block'; document.getElementById('debug').innerText = data.preview;
                if(res.ok) alert("Cargado correctamente");
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f else ""
        f_val = request.form.get('fecha')
        visitas_col.insert_one({
            "pv": request.form.get('pv'), 
            "n_documento": session['user_name'], 
            "fecha": f_val, 
            "mes": f_val[:7], 
            "bmb": request.form.get('bmb'), 
            "motivo": request.form.get('motivo'), 
            "ubicacion": request.form.get('ubicacion'), 
            "Nota": request.form.get('nota'),  # NUEVO CAMPO NOTA
            "f_bmb": b64(request.files.get('f1')), 
            "f_fachada": b64(request.files.get('f2'))
        })
        return redirect('/formulario?msg=OK') if session['role'] == 'asesor' else redirect('/')
    
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_BI}</head>
    <body onload="getGPS()" style="justify-content:center; align-items:center; display:flex; min-height:100vh; padding:20px; box-sizing:border-box;">
        <div class="profile-badge"><b>{session['user_name']}</b><small>{session['role']}</small></div>
        <div class="card" style="max-width:480px;">
            <h2 style="text-align:center; color:var(--dark);">Registro Visita</h2>
            <form method="POST" enctype="multipart/form-data">
                <label style="font-size:12px;">Punto de Venta</label>
                <input list="p" name="pv" id="pv_input" placeholder="Buscar PDV..." onchange="updateBMB()" required>
                <datalist id="p">{options}</datalist>
                
                <label style="font-size:12px;">Dato BMB (Auto)</label>
                <input type="text" name="bmb" id="bmb_input" placeholder="BMB del punto" readonly style="background:#f8f9fa; font-weight:bold; color:var(--primary);">
                
                <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                
                <select name="motivo"><option>Máquina Retirada</option><option>Punto Cerrado</option></select>
                
                <label style="font-size:12px;">Observaciones (Nota)</label>
                <textarea name="nota" rows="3" placeholder="Escribe aquí cualquier observación..."></textarea>
                
                <input type="hidden" name="ubicacion" id="g">
                <label style="font-size:12px;">Foto BMB</label><input type="file" name="f1" accept="image/*" capture="camera" required>
                <label style="font-size:12px;">Foto Fachada</label><input type="file" name="f2" accept="image/*" capture="camera" required>
                
                <button class="btn btn-primary">Enviar Registro</button>
                {f'<a href="/" class="btn btn-gray">Volver</a>' if session['role']=='admin' else ''}
                <a href="/logout" style="color:red; display:block; text-align:center; margin-top:15px; font-size:12px; text-decoration:none;">Cerrar Sesión</a>
            </form>
        </div>
        <script>
            function getGPS(){{navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('g').value=p.coords.latitude+','+p.coords.longitude;}},null,{{enableHighAccuracy:true}});}}
            
            function updateBMB() {{
                const val = document.getElementById('pv_input').value;
                const opts = document.getElementById('p').childNodes;
                for (let i = 0; i < opts.length; i++) {{
                    if (opts[i].value === val) {{
                        document.getElementById('bmb_input').value = opts[i].getAttribute('data-bmb') || 'No definido';
                        break;
                    }}
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        try:
            content = f.stream.read().decode("utf-8-sig", errors="ignore")
            lines = content.splitlines(); preview = "\\n".join(lines[:4])
            d = ';' if content.count(';') > content.count(',') else ','
            reader = csv.DictReader(io.StringIO(content), delimiter=d)
            lista = []
            for r in reader:
                clean = {str(k).strip(): str(v).strip() for k, v in r.items() if k}
                if clean: lista.append(clean)
            if lista:
                puntos_col.delete_many({}); puntos_col.insert_many(lista)
                return jsonify({"preview": preview, "count": len(lista)}), 200
        except Exception as e: return jsonify({"preview": "Error", "msg": str(e)}), 500
    return jsonify({"preview": "No file"}), 400

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
