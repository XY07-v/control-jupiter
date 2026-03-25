from flask import Flask, render_template_string, request, redirect, jsonify, Response, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_poc_2026_v14_final"

# --- CONEXIÓN MONGODB (TU LÓGICA ORIGINAL) ---
MONGO_URI = "mongodb+srv://control-jupiter:control-jupiter1234@cluster0.dtureen.mongodb.net/NestleDB?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
usuarios_col = db['usuarios']
puntos_col = db['puntos_venta']

# --- DISEÑO iOS 26 CLEAN LIGHT ---
CSS_CLEAN = """
<style>
    :root { 
        --ios-blue: #007AFF; 
        --bg: #F2F2f7; 
        --glass: rgba(255, 255, 255, 0.8);
        --border: rgba(0, 0, 0, 0.05);
    }
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; 
        background-color: var(--bg); margin: 0; color: #1c1c1e; line-height: 1.4;
    }
    .header-bar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 15px 20px; background: var(--glass); backdrop-filter: blur(20px);
        position: sticky; top: 0; z-index: 1000; border-bottom: 1px solid var(--border);
    }
    .container { padding: 20px; max-width: 100%; box-sizing: border-box; }
    .card { 
        background: white; border-radius: 20px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); border: 1px solid var(--border);
    }
    .btn { 
        padding: 12px 20px; border-radius: 12px; border: none; font-weight: 600; 
        cursor: pointer; transition: 0.2s; font-size: 14px; text-decoration: none; display: inline-block;
    }
    .btn-primary { background: var(--ios-blue); color: white; }
    .btn-secondary { background: #E5E5EA; color: #1c1c1e; }
    .btn-danger { background: #FF3B30; color: white; }
    
    input, select, textarea { 
        width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; 
        border-radius: 10px; background: #FFF; font-size: 16px; box-sizing: border-box;
    }
    .modal {
        display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.2); backdrop-filter: blur(10px); z-index: 2000;
    }
    .modal-content {
        background: white; margin: 5% auto; width: 90%; max-width: 500px;
        border-radius: 30px; padding: 25px; position: relative; max-height: 80vh; overflow-y: auto;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
    th { text-align: left; padding: 10px; color: #8E8E93; font-weight: 400; border-bottom: 1px solid var(--border); }
    td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
    .overlay-nav { display:none; } /* Eliminamos sidebars complejos para evitar sobreposición */
</style>
"""

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    if session['role'] == 'asesor': return redirect('/formulario')
    
    visitas = list(visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0}).sort("fecha", -1))
    rows = "".join([f'<div class="card" onclick="verVisita(\'{v["_id"]}\')"><b>{v.get("pv")}</b><br><span style="color:#8e8e93; font-size:12px;">{v.get("fecha")} · {v.get("n_documento")}</span></div>' for v in visitas])
    
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_CLEAN}</head>
    <body>
        <div class="header-bar">
            <h2 style="margin:0; font-size:20px;">Nestlé BI</h2>
            <div>
                <button class="btn btn-secondary" onclick="openM('m_admin')">Menú</button>
            </div>
        </div>
        <div class="container">
            <h3>Historial de Visitas</h3>
            {rows}
        </div>

        <div id="m_admin" class="modal"><div class="modal-content">
            <button class="btn btn-secondary" onclick="closeM()" style="float:right;">X</button>
            <h3>Administración</h3>
            <a href="/formulario" class="btn btn-primary" style="width:100%; margin-bottom:10px;">Nueva Visita</a>
            <button class="btn btn-secondary" style="width:100%; margin-bottom:10px;" onclick="openM('m_puntos')">Gestionar Puntos</button>
            <button class="btn btn-secondary" style="width:100%; margin-bottom:10px;" onclick="openM('m_users')">Gestionar Usuarios</button>
            <button class="btn btn-secondary" style="width:100%; margin-bottom:10px;" onclick="openM('m_csv')">Carga Masiva</button>
            <a href="/descargar" class="btn btn-primary" style="width:100%; margin-bottom:10px; background:#34C759;">Descargar CSV</a>
            <a href="/logout" class="btn btn-danger" style="width:100%;">Cerrar Sesión</a>
        </div></div>

        <div id="m_puntos" class="modal"><div class="modal-content" style="max-width:800px;">
            <button class="btn btn-secondary" onclick="closeM()" style="margin-bottom:10px;">← Regresar</button>
            <h3>Puntos de Venta</h3>
            <div id="lista_puntos" style="overflow-x:auto;"></div>
        </div></div>

        <div id="m_users" class="modal"><div class="modal-content">
            <button class="btn btn-secondary" onclick="closeM()" style="margin-bottom:10px;">← Regresar</button>
            <h3>Usuarios</h3>
            <button class="btn btn-primary" onclick="editU()" style="width:100%; margin-bottom:15px;">+ Nuevo Usuario</button>
            <div id="lista_usuarios"></div>
        </div></div>

        <div id="m_csv" class="modal"><div class="modal-content">
            <button class="btn btn-secondary" onclick="closeM()" style="margin-bottom:10px;">← Regresar</button>
            <h3>Carga Masiva</h3>
            <input type="file" id="file_csv_input" accept=".csv">
            <button class="btn btn-primary" onclick="subirCSV()" style="width:100%;">Procesar CSV</button>
        </div></div>

        <script>
            function openM(id) {{ document.getElementById(id).style.display='block'; if(id=='m_puntos') cargarP(); if(id=='m_users') cargarU(); }}
            function closeM() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargarP() {{
                const res = await fetch('/api/puntos'); const data = await res.json();
                let h = '<table><tr><th>Punto</th><th>BMB</th><th>Acción</th></tr>';
                data.forEach(p => {{ h += `<tr><td>${{p['Punto de Venta']}}</td><td>${{p['BMB']}}</td><td><button class="btn btn-secondary" onclick='editP(${{JSON.stringify(p)}})'>Edit</button></td></tr>`; }});
                document.getElementById('lista_puntos').innerHTML = h + '</table>';
            }}

            async function cargarU() {{
                const res = await fetch('/api/usuarios'); const data = await res.json();
                let h = '<table><tr><th>Nombre</th><th>Acción</th></tr>';
                data.forEach(u => {{ h += `<tr><td>${{u.nombre_completo}}</td><td><button class="btn btn-secondary" onclick='editU(${{JSON.stringify(u)}})'>Edit</button></td></tr>`; }});
                document.getElementById('lista_usuarios').innerHTML = h + '</table>';
            }}

            function editP(p) {{
                let form = '<h3>Editar Punto</h3>';
                Object.keys(p).forEach(k => {{ if(k!='_id') form += `<label>${{k}}</label><input type="text" id="ed_${{k}}" value="${{p[k]}}">`; }});
                form += `<button class="btn btn-primary" onclick="saveP('${{p._id}}')">Guardar</button>`;
                document.getElementById('m_puntos').querySelector('.modal-content').innerHTML = '<button class="btn btn-secondary" onclick="cargarP()">← Volver</button>' + form;
            }}

            async function saveP(id) {{
                let d = {{}}; document.querySelectorAll('[id^="ed_"]').forEach(i => d[i.id.replace('ed_','')] = i.value);
                await fetch('/api/actualizar_punto', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:id, datos:d}})}});
                cargarP();
            }}

            function editU(u={{}}) {{
                let form = `<h3>${{u._id?'Editar':'Nuevo'}} Usuario</h3>
                <input type="text" id="un" placeholder="Nombre" value="${{u.nombre_completo||''}}">
                <input type="text" id="uu" placeholder="Usuario" value="${{u.usuario||''}}">
                <input type="text" id="up" placeholder="Password" value="${{u.password||''}}">
                <select id="ur"><option value="asesor" ${{u.rol=='asesor'?'selected':''}}>Asesor</option><option value="admin" ${{u.rol=='admin'?'selected':''}}>Admin</option></select>
                <button class="btn btn-primary" onclick="saveU('${{u._id||''}}')">Guardar</button>`;
                document.getElementById('m_users').querySelector('.modal-content').innerHTML = '<button class="btn btn-secondary" onclick="cargarU()">← Volver</button>' + form;
            }}

            async function saveU(id) {{
                const d = {{id:id, nom:document.getElementById('un').value, usr:document.getElementById('uu').value, pas:document.getElementById('up').value, rol:document.getElementById('ur').value}};
                await fetch('/api/actualizar_usuario', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(d)}});
                cargarU();
            }}

            async function subirCSV() {{
                const f = document.getElementById('file_csv_input').files[0]; if(!f) return;
                const fd = new FormData(); fd.append('file_csv', f);
                const r = await fetch('/carga_masiva_puntos', {{method:'POST', body:fd}});
                const res = await r.json(); alert("Cargados: " + res.count); closeM();
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    
    if request.method == 'POST':
        # LÓGICA DE ENVÍO ORIGINAL RESTAURADA
        def to_b64(file):
            if not file: return ""
            return f"data:{file.content_type};base64,{base64.b64encode(file.read()).decode()}"
        
        visitas_col.insert_one({
            "pv": request.form.get('pv'),
            "n_documento": session['user_name'],
            "fecha": request.form.get('fecha'),
            "bmb": request.form.get('bmb'),
            "motivo": request.form.get('motivo'),
            "Nota": request.form.get('nota'),
            "f_bmb": to_b64(request.files.get('f_bmb')),
            "f_fachada": to_b64(request.files.get('f_fachada'))
        })
        return redirect('/formulario?msg=OK')

    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1}))
    options = "".join([f'<option value="{p["Punto de Venta"]}" data-bmb="{p.get("BMB","")}"> ' for p in puntos])
    
    btn_regresar = '<a href="/" class="btn btn-secondary" style="margin-bottom:15px;">← Panel Control</a>' if session['role'] == 'admin' else ''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_CLEAN}</head>
    <body>
        <div class="container" style="max-width:500px; margin:auto;">
            {btn_regresar}
            <div class="card">
                <h2 style="color:var(--ios-blue); text-align:center;">Nueva Visita</h2>
                <form method="POST" enctype="multipart/form-data">
                    <label>Punto de Venta</label>
                    <input list="pts" name="pv" id="pv_sel" onchange="setBMB()" required>
                    <datalist id="pts">{options}</datalist>
                    
                    <label>BMB Máquina</label>
                    <input type="text" name="bmb" id="bmb_val" required>
                    
                    <label>Fecha</label>
                    <input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}" required>
                    
                    <label>Motivo</label>
                    <select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option><option>No permite ingreso</option></select>
                    
                    <label>Observaciones</label>
                    <textarea name="nota" rows="3"></textarea>
                    
                    <div style="margin:15px 0;">
                        <label style="font-size:12px; color:#8e8e93;">Foto BMB / Máquina</label>
                        <input type="file" name="f_bmb" accept="image/*" capture="camera" required>
                    </div>
                    
                    <div style="margin:15px 0;">
                        <label style="font-size:12px; color:#8e8e93;">Foto Fachada</label>
                        <input type="file" name="f_fachada" accept="image/*" capture="camera" required>
                    </div>
                    
                    <button class="btn btn-primary" style="width:100%; font-size:18px; padding:15px;">Enviar Reporte</button>
                </form>
            </div>
            <a href="/logout" style="display:block; text-align:center; color:#FF3B30; text-decoration:none; margin-top:10px;">Cerrar Sesión</a>
        </div>
        <script>
            function setBMB() {{
                const val = document.getElementById('pv_sel').value;
                const opt = document.querySelector('#pts option[value="'+val+'"]');
                if(opt) document.getElementById('bmb_val').value = opt.dataset.bmb;
            }}
        </script>
    </body></html>
    """)

# --- APIS RESTAURADAS DEL ARCHIVO ORIGINAL ---
@app.route('/api/puntos')
def api_puntos():
    p = list(puntos_col.find()); [x.update({"_id": str(x["_id"])}) for x in p]; return jsonify(p)

@app.route('/api/usuarios')
def api_users():
    u = list(usuarios_col.find()); [x.update({"_id": str(x["_id"])}) for x in u]; return jsonify(u)

@app.route('/api/actualizar_punto', methods=['POST'])
def up_p(): 
    d = request.json
    puntos_col.update_one({"_id": ObjectId(d['id'])}, {"$set": d['datos']})
    return jsonify({"s": "ok"})

@app.route('/api/actualizar_usuario', methods=['POST'])
def up_u(): 
    d = request.json
    if d['id']:
        usuarios_col.update_one({"_id": ObjectId(d['id'])}, {"$set": {"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']}})
    else:
        usuarios_col.insert_one({"nombre_completo": d['nom'], "usuario": d['usr'], "password": d['pas'], "rol": d['rol']})
    return jsonify({"s": "ok"})

@app.route('/carga_masiva_puntos', methods=['POST'])
def carga():
    f = request.files.get('file_csv')
    if f:
        content = f.stream.read().decode("utf-8-sig", errors="ignore")
        dialect = ';' if content.count(';') > content.count(',') else ','
        reader = csv.DictReader(io.StringIO(content), delimiter=dialect)
        lista = [{k.strip(): v.strip() for k, v in r.items() if k} for r in reader]
        if lista:
            puntos_col.delete_many({})
            puntos_col.insert_many(lista)
        return jsonify({"count": len(lista)})
    return jsonify({"error": "No file"}), 400

@app.route('/descargar')
def desc():
    cursor = visitas_col.find({}, {"f_bmb": 0, "f_fachada": 0, "_id": 0})
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['Punto', 'Asesor', 'Fecha', 'BMB', 'Motivo', 'Nota'])
    for r in cursor: w.writerow([r.get('pv'), r.get('n_documento'), r.get('fecha'), r.get('bmb'), r.get('motivo'), r.get('Nota')])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment;filename=Reporte_Visitas.csv"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        user = usuarios_col.find_one({"usuario": u, "password": p})
        if user:
            session.update({'user_id': str(user['_id']), 'user_name': user['nombre_completo'], 'role': user.get('rol', 'asesor')})
            return redirect('/')
    return render_template_string(f"""<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_CLEAN}</head><body style="display:flex; align-items:center; justify-content:center; height:100vh;"><div class="card" style="width:300px; text-align:center;"><h2>Nestlé BI</h2><form method="POST"><input type="text" name="u" placeholder="Usuario"><input type="password" name="p" placeholder="Password"><button class="btn btn-primary" style="width:100%;">Entrar</button></form></div></body></html>""")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
