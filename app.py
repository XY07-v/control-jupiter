from flask import Flask, render_template_string, request, redirect, Response
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import csv
import io

app = Flask(__name__)

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Leemos el archivo cargado
        with open('credenciales.json.json', 'r') as f:
            info_llave = json.load(f)
        
        # REPARACIÓN CRÍTICA: Limpia los saltos de línea mal formateados
        # Esto soluciona el error 'Invalid JWT Signature'
        info_llave['private_key'] = info_llave['private_key'].replace('\\n', '\n')
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llave, scope)
        client = gspread.authorize(creds)
        
        # Conexión al libro y hoja configurados
        libro = client.open("Visitas_POC_Nestle")
        hoja = libro.worksheet("Visitas")
        return hoja
    except Exception as e:
        print(f"ERROR TÉCNICO: {e}")
        return str(e)

@app.route('/')
def index():
    hoja = conectar_google()
    
    if isinstance(hoja, str):
        return f"<h1>Error de Conexión</h1><p>Detalle: {hoja}</p><p>Verifica que el robot tenga acceso a la hoja.</p>"
    
    registros = []
    try:
        # Trae los registros basados en los encabezados de la Fila 1
        registros = hoja.get_all_records()
    except Exception as e:
        print(f"Error de lectura: {e}")
        registros = []

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f8f9fa; padding: 20px; }
            .container { max-width: 1100px; margin: auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; margin-bottom: 20px; }
            .logo-nestle { width: 100px; opacity: 0.4; filter: grayscale(100%); }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th { background: #0056a0; color: white; padding: 12px; border: 1px solid #ddd; }
            td { padding: 10px; border: 1px solid #eee; text-align: center; }
            .btn { padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; border: none; font-size: 13px; }
            .btn-blue { background: #0056a0; color: white; }
            .btn-green { background: #27ae60; color: white; margin-left: 10px; }
            .chulo { color: #27ae60; font-weight: bold; }
            .equis { color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0;">VISITAS A POC</h1>
                    <p style="margin:5px 0; color:#666;">Nestlé - Control de Gestión</p>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Nestle%CC%81_textlogo.svg/2560px-Nestle%CC%81_textlogo.svg.png" class="logo-nestle">
            </div>

            <div style="margin-bottom: 20px;">
                <a href="/formulario" class="btn btn-blue">+ Registrar Visita</a>
                <a href="/descargar_csv" class="btn btn-green">📥 Descargar CSV (;)</a>
            </div>

            <table>
                <tr>
                    <th>ID PV</th><th>Punto de Venta</th><th>N. Documento</th><th>Nombre completo</th>
                    <th>MES</th><th>Visita</th><th>Plan</th><th>Fecha</th><th>Cobertura</th><th>Estado</th><th>Motivo</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r['ID Punto de Venta'] }}</td>
                    <td>{{ r['Punto de Venta'] }}</td>
                    <td>{{ r['N. Documento'] }}</td>
                    <td>{{ r['Nombre completo'] }}</td>
                    <td>{{ r['MES'] }}</td>
                    <td>{{ r['Fecha Visita'] }}</td>
                    <td>{{ r['Plan'] }}</td>
                    <td>{{ r['Fecha'] }}</td>
                    <td>{{ r['Cobertura'] }}</td>
                    <td class="{{ 'chulo' if r['Estado'] == '-1' or r['Estado'] == -1 else 'equis' }}">
                        {{ '✅' if r['Estado'] == '-1' or r['Estado'] == -1 else '❌' }}
                    </td>
                    <td>{{ r['Motivo'] }}</td>
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
            datos = [
                request.form.get('id_pv'), request.form.get('pv'), 
                request.form.get('doc'), request.form.get('nombre'),
                request.form.get('mes'), request.form.get('f_visita'),
                request.form.get('plan'), request.form.get('fecha'),
                request.form.get('cobertura'), request.form.get('estado'),
                request.form.get('motivo')
            ]
            # Guarda la nueva fila en Google Sheets
            hoja.append_row(datos)
        return redirect('/')

    return render_template_string("""
    <form method="POST" style="max-width:400px; margin:auto; padding:20px; font-family:sans-serif;">
        <h2>📝 Nueva Visita</h2>
        <input type="text" name="id_pv" placeholder="ID PV" required style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="pv" placeholder="Punto de Venta" required style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="doc" placeholder="N. Documento" style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="mes" placeholder="MES (Texto)" required style="width:100%; margin:5px 0; padding:10px;">
        <label>Fecha Visita:</label><input type="date" name="f_visita" style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="plan" placeholder="Plan" style="width:100%; margin:5px 0; padding:10px;">
        <label>Fecha Actual:</label><input type="date" name="fecha" style="width:100%; margin:5px 0; padding:10px;">
        <input type="text" name="cobertura" placeholder="Cobertura" style="width:100%; margin:5px 0; padding:10px;">
        <select name="estado" style="width:100%; margin:5px 0; padding:10px;">
            <option value="-1">Positivo (-1 ✅)</option>
            <option value="">Déficit (Vacío ❌)</option>
        </select>
        <textarea name="motivo" placeholder="Motivo" style="width:100%; margin:5px 0; padding:10px;"></textarea>
        <button type="submit" style="width:100%; background:#27ae60; color:white; padding:15px; border:none; cursor:pointer;">GUARDAR EN GOOGLE</button>
    </form>
    """)

@app.route('/descargar_csv')
def descargar_csv():
    hoja = conectar_google()
    if isinstance(hoja, str): return "Error"
    valores = hoja.get_all_values()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerows(valores)
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=Visitas_A_POC.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
