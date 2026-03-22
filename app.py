from flask import Flask, render_template_string, request, redirect, Response
import csv
import io
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
# Asegúrate de que 'credenciales.json' esté en la misma carpeta que este app.py
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
    client = gspread.authorize(creds)
    # REEMPLAZA "Visitas_POC_Nestle" por el nombre exacto de tu hoja en Google Drive
    hoja_google = client.open("Visitas_POC_Nestle").sheet1 
except Exception as e:
    print(f"Error conectando a Google Sheets: {e}")
    hoja_google = None

# --- RUTA PRINCIPAL (TABLA DE VISUALIZACIÓN) ---
@app.route('/')
def index():
    # Intentamos leer los datos de Google Sheets para mostrarlos en la tabla
    registros = []
    if hoja_google:
        try:
            # Obtener todos los registros (saltando el encabezado)
            lista_datos = hoja_google.get_all_records()
            registros = lista_datos
        except:
            registros = []

    html_tabla = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; }
            .logo-nestle { width: 120px; opacity: 0.5; filter: grayscale(100%); }
            table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 20px; }
            th { background: #0056a0; color: white; padding: 10px; border: 1px solid #ddd; }
            td { padding: 8px; border: 1px solid #eee; text-align: center; }
            .btn { padding: 8px 15px; border-radius: 5px; text-decoration: none; font-weight: bold; display: inline-block; cursor: pointer; border: none; }
            .btn-new { background: #0056a0; color: white; }
            .btn-csv { background: #27ae60; color: white; margin-left: 10px; }
            .chulo { color: #27ae60; font-weight: bold; font-size: 14px; }
            .equis { color: #e74c3c; font-weight: bold; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0;">VISITAS A POC</h1>
                    <p style="margin:5px 0; color:#888;">Gestión de Puntos de Venta | 2026</p>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Nestle%CC%81_textlogo.svg/2560px-Nestle%CC%81_textlogo.svg.png" class="logo-nestle">
            </div>

            <div style="margin: 20px 0;">
                <a href="/formulario" class="btn btn-new">+ Registrar Visita</a>
                <a href="/descargar_csv" class="btn btn-csv">📥 Descargar CSV (;)</a>
            </div>

            <table>
                <tr>
                    <th>ID PV</th><th>Punto de Venta</th><th>N. Doc</th><th>Nombre</th>
                    <th>MES</th><th>Visita</th><th>Plan</th><th>Fecha</th>
                    <th>Cobertura</th><th>Estado</th><th>Motivo</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r['ID Punto de Venta'] }}</td><td>{{ r['Punto de Venta'] }}</td>
                    <td>{{ r['N. Documento'] }}</td><td>{{ r['Nombre completo'] }}</td>
                    <td>{{ r['MES'] }}</td><td>{{ r['Fecha Visita'] }}</td>
                    <td>{{ r['Plan'] }}</td><td>{{ r['Fecha'] }}</td>
                    <td>{{ r['Cobertura'] }}</td>
                    <td class="{{ 'chulo' if r['Estado'] == '-1' else 'equis' }}">
                        {{ '✅' if r['Estado'] == '-1' else '❌' }}
                    </td>
                    <td>{{ r['Motivo'] }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_tabla, registros=registros)

# --- RUTA DEL FORMULARIO ---
@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Captura de datos
        datos_fila = [
            request.form['id_pv'], request.form['pv'], request.form['doc'],
            request.form['nombre'], request.form['mes'], request.form['f_visita'],
            request.form['plan'], request.form['fecha'], request.form['cobertura'],
            request.form['estado'], request.form['motivo']
        ]
        
        # Guardar en Google Sheets si está disponible
        if hoja_google:
            hoja_google.append_row(datos_fila)
            
        return redirect('/')

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ingreso de Visita</title>
        <style>
            body { font-family: sans-serif; background: #eef2f3; display: flex; justify-content: center; padding: 20px; }
            form { background: white; padding: 25px; border-radius: 10px; width: 450px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
            input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn-save { background: #27ae60; color: white; border: none; padding: 12px; width: 100%; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <form method="POST">
            <h2 style="color:#333; text-align:center;">📝 Nueva Visita</h2>
            <input type="text" name="id_pv" placeholder="ID Punto de Venta" required>
            <input type="text" name="pv" placeholder="Punto de Venta" required>
            <input type="text" name="doc" placeholder="N. Documento">
            <input type="text" name="nombre" placeholder="Nombre completo">
            <input type="text" name="mes" placeholder="MES (Ej: MARZO)" required>
            <input type="date" name="f_visita" title="Fecha de Visita">
            <input type="text" name="plan" placeholder="Plan">
            <input type="date" name="fecha" title="Fecha">
            <input type="text" name="cobertura" placeholder="Cobertura">
            <label>Estado:</label>
            <select name="estado">
                <option value="-1">Positivo (-1 ✅)</option>
                <option value="0">Déficit (Vacío ❌)</option>
            </select>
            <textarea name="motivo" placeholder="Motivo"></textarea>
            <button type="submit" class="btn-save">GUARDAR EN GOOGLE SHEETS</button>
            <p style="text-align:center;"><a href="/" style="color:#888; font-size:12px;">Cancelar y volver</a></p>
        </form>
    </body>
    </html>
    """)

# --- RUTA PARA DESCARGAR CSV (;) ---
@app.route('/descargar_csv')
def descargar_csv():
    if not hoja_google: return "Error: No hay conexión a datos"
    
    lista_datos = hoja_google.get_all_values() # Trae todo incluyendo encabezados
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';') # Delimitador solicitado
    
    for fila in lista_datos:
        writer.writerow(fila)
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Visitas_A_POC.csv"}
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
