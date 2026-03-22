from flask import Flask, render_template_string, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)

def conectar_google():
    try:
        # Los días se cuentan de lunes a sábado [cite: 2026-03-11]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        ruta_creds = "/etc/secrets/creds.json"
        
        if not os.path.exists(ruta_creds):
            return f"Archivo no encontrado en {ruta_creds}. Verifica el vínculo del Environment Group."

        # LEER Y REPARAR EL JSON MANUALMENTE
        with open(ruta_creds, 'r') as f:
            creds_data = json.load(f)
        
        # Limpieza crítica de la firma JWT:
        # Esto elimina cualquier error de formato en la llave privada
        if 'private_key' in creds_data:
            creds_data['private_key'] = creds_data['private_key'].replace('\\n', '\n').strip()

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
        client = gspread.authorize(creds)
        
        # Apertura de la hoja específica
        return client.open("Visitas_POC_Nestle").worksheet("Visitas")
    except Exception as e:
        return f"Error de firma JWT: {str(e)}"

@app.route('/')
def index():
    hoja = conectar_google()
    if isinstance(hoja, str):
        return f"<div style='color:red; font-family:sans-serif;'><h2>⚠️ Error de Autenticación</h2><p>{hoja}</p></div>"
    
    try:
        registros = hoja.get_all_records()
    except Exception as e:
        return f"<h2>Error al leer datos</h2><p>{e}</p>"

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Control Nestlé</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f8f9fa; }
            .container { max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th { background: #0056a0; color: white; padding: 10px; }
            td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            .btn { background: #0056a0; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visitas POC Nestlé</h1>
            <a href="/formulario" class="btn">+ Nueva Visita</a>
            <table>
                <tr>
                    <th>ID PV</th><th>Punto de Venta</th><th>Nombre</th><th>MES</th><th>Estado</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r['ID Punto de Venta'] }}</td>
                    <td>{{ r['Punto de Venta'] }}</td>
                    <td>{{ r['Nombre completo'] }}</td>
                    <td>{{ r['MES'] }}</td>
                    <td>
                        {# -1 es positivo (chulo) y vacío es déficit (x) [cite: 2026-03-09] #}
                        {{ '✅' if r['Estado'] == '-1' or r['Estado'] == -1 else '❌' }}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        hoja = conectar_google()
        if not isinstance(hoja, str):
            # MES está en formato texto [cite: 2026-02-22]
            datos = [
                request.form.get('id_pv'), request.form.get('pv'), "", 
                request.form.get('nombre'), request.form.get('mes'), "", 
                "", "", "", request.form.get('estado'), ""
            ]
            hoja.append_row(datos)
        return redirect('/')
    
    return render_template_string("""
    <div style="max-width:400px; margin:auto; background:white; padding:25px; border-radius:10px; font-family:sans-serif;">
        <h2>Registrar Visita</h2>
        <form method="POST">
            <input type="text" name="id_pv" placeholder="ID PV" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="mes" placeholder="Mes (Texto)" required style="width:100%; margin-bottom:10px; padding:10px;">
            <select name="estado" style="width:100%; margin-bottom:10px; padding:10px;">
                <option value="-1">Positivo (-1 ✅)</option>
                <option value="">Déficit (Vacío ❌)</option>
            </select>
            <button type="submit" style="width:100%; background:green; color:white; padding:12px; border:none; border-radius:5px; cursor:pointer;">GUARDAR</button>
        </form>
    </div>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
