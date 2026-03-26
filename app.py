from flask import Flask, render_template_string, request, redirect, jsonify, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64, io, math, json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nestle_bi_solo_form_2026"

# --- CONEXIÓN MONGODB ---
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']
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

CSS = """
<style>
    :root { --ios-blue: #007AFF; --bg: #F2F2F7; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: #1c1c1e; }
    .card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .btn { width: 100%; padding: 14px; border-radius: 12px; border: none; font-weight: 600; cursor: pointer; margin-top: 10px; font-size: 15px; }
    .btn-blue { background: var(--ios-blue); color: white; }
    .btn-light { background: #E5E5EA; color: #1c1c1e; text-decoration: none; display: block; text-align: center; }
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 14px; }
    .historial-item { border-bottom: 0.5px solid #eee; padding: 10px 0; cursor: pointer; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); z-index: 1000; }
    .modal-content { background: white; margin: 10% auto; width: 90%; max-width: 500px; border-radius: 25px; padding: 20px; max-height: 80vh; overflow-y: auto; }
</style>
"""

@app.route('/')
def index():
    # Solo traemos texto del historial (pv, fecha, estado) para que cargue instantáneo
    visitas = list(visitas_col.find({}, {"f_bmb":0, "f_fachada":0}).sort("fecha", -1).limit(20))
    
    rows = ""
    for v in visitas:
        color = "green" if v.get('estado') == "Aprobado" else "orange"
        rows += f'''<div class="historial-item" onclick="verDetalle('{str(v['_id'])}')">
            <b>{v.get('pv')}</b> <br>
            <small>{v.get('fecha')} - <span style="color:{color}">{v.get('estado')}</span></small>
        </div>'''

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body>
        <div style="max-width:500px; margin:auto;">
            <h2 style="text-align:center; color:var(--ios-blue);">Nestlé BI - Reportes</h2>
            
            <a href="/formulario" class="btn btn-blue" style="text-decoration:none;">+ Nuevo Reporte</a>
            
            <div class="card" style="margin-top:20px;">
                <h3>Últimas Visitas</h3>
                {rows or '<p>No hay registros aún.</p>'}
            </div>
        </div>

        <div id="modalDetalle" class="modal">
            <div class="modal-content" id="detCont">Cargando...</div>
        </div>

        <script>
            async function verDetalle(id) {{
                document.getElementById('modalDetalle').style.display = 'block';
                const r = await fetch('/get_visita/'+id);
                const d = await r.json();
                document.getElementById('detCont').innerHTML = `
                    <button class="btn btn-light" onclick="document.getElementById('modalDetalle').style.display='none'">Cerrar</button>
                    <h4>${{d.pv}}</h4>
                    <p>Estado: ${{d.estado}}</p>
                    <img src="${{d.f1}}" style="width:100%; border-radius:10px; margin-bottom:10px;">
                    <img src="${{d.f2}}" style="width:100%; border-radius:10px;">
                `;
            }}
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        def b64(f): return f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode()}" if f and f.filename else ""
        
        pv_in = request.form.get('pv')
        bmb_in = request.form.get('bmb')
        gps = request.form.get('ubicacion')
        
        # Lógica de validación simplificada
        pnt = puntos_col.find_one({"Punto de Venta": pv_in})
        dist = calcular_distancia(gps, pnt.get('Ruta')) if pnt else 0
        
        # Si coincide BMB y distancia < 100m, queda Aprobado, si no Pendiente
        estado_v = "Aprobado" if (pnt and bmb_in == pnt.get('BMB') and dist < 100) else "Pendiente"

        visitas_col.insert_one({
            "pv": pv_in,
            "fecha": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "bmb_propuesto": bmb_in,
            "ubicacion": gps,
            "distancia": round(dist, 1),
            "estado": estado_v,
            "f_bmb": b64(request.files.get('f1')),
            "f_fachada": b64(request.files.get('f2'))
        })
        
        # Si es aprobado, actualizamos la ubicación del punto automáticamente
        if estado_v == "Aprobado":
            puntos_col.update_one({"Punto de Venta": pv_in}, {"$set": {"Ruta": gps}})
            
        return redirect('/')

    # Traer puntos para el buscador (datalist)
    puntos = list(puntos_col.find({}, {"Punto de Venta": 1, "_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}"> ' for p in puntos])

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div style="max-width:500px; margin:auto;">
            <div class="card">
                <h3 style="margin-top:0;">Nuevo Reporte de Visita</h3>
                <form method="POST" enctype="multipart/form-data" onsubmit="this.querySelector('button').innerHTML='Enviando...';">
                    <label>Punto de Venta</label>
                    <input list="pts" name="pv" required placeholder="Escriba nombre del punto">
                    <datalist id="pts">{opts}</datalist>
                    
                    <label>Código BMB</label>
                    <input type="text" name="bmb" required placeholder="Ingrese código de máquina">
                    
                    <label>Foto de la Máquina</label>
                    <input type="file" name="f1" accept="image/*" capture="camera" required>
                    
                    <label>Foto de la Fachada</label>
                    <input type="file" name="f2" accept="image/*" capture="camera" required>
                    
                    <input type="hidden" name="ubicacion" id="gps">
                    
                    <button type="submit" class="btn btn-blue">Enviar a Nestlé BI</button>
                    <a href="/" class="btn btn-light" style="margin-top:10px;">Cancelar</a>
                </form>
            </div>
        </div>
    </body></html>
    """)

@app.route('/get_visita/<id>')
def get_visita(id):
    v = visitas_col.find_one({"_id": ObjectId(id)})
    return jsonify({
        "pv": v.get('pv'),
        "estado": v.get('estado'),
        "f1": v.get('f_bmb'),
        "f2": v.get('f_fachada')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
