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
        
        # Cargamos el JSON y limpiamos la clave privada para evitar errores de firma (JWT)
        with open('credenciales.json') as f:
            info_llave = json.load(f)
        
        # Corrección técnica para la firma digital
        info_llave['private_key'] = info_llave['private_key'].replace('\\n', '\n')
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llave, scope)
        client = gspread.authorize(creds)
        
        # Conexión al libro y hoja específicos
        libro = client.open("Visitas_POC_Nestle")
        hoja = libro.worksheet("Visitas")
        return hoja
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {e}")
        return str(e)

@app.route('/')
def index():
    hoja = conectar_google()
    
    # Si la conexión falla, mostramos el error técnico en pantalla
    if isinstance(hoja, str):
        return f"<h1>Error de Configuración</h1><p>Detalle: {hoja}</p><p>Revisa que el archivo se llame credenciales.json y el libro Visitas_POC_Nestle exista.</p>"
    
    registros = []
    try:
        # Trae los datos usando los encabezados de la Fila 1
        registros = hoja.get_all_records()
    except Exception as e:
        print(f"Error al leer registros: {e}")
        registros = []

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f8f9fa; padding: 20px; margin: 0; }
            .container { max-width: 1100px; margin: auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }
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
                    <h1 style="margin:0; color:#333;">VISITAS A POC</h1>
                    <p style="margin:5px 0; color:#666;">Control de Gestión | Nestlé</p>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Nestle%CC%81_textlogo.svg/2560px-Nestle%CC%81_textlogo.svg.png" class="logo-nestle">
            </div>

            <div style="margin-bottom: 25px;">
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
            # El orden de los datos debe coincidir con las columnas de la A a la K
            datos = [
                request.form.get('id_pv'), request.form.get('pv'), 
                request.form.get('doc'), request.form.get('nombre'),
                request.form.get('mes'), request.form.get('f_visita'),
                request.form.get('plan'), request.form.get('fecha'),
                request.form.get('cobertura'), request.form.get('estado'),
                request.form.get('motivo')
            ]
            hoja.append_row(datos)
        return redirect('/')

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nueva Visita</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
            form { background: white; padding: 30px; border-radius: 12px; width: 450px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
            h2 { text-align: center; color: #333; margin-bottom: 20px; }
            input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
            .btn-save { background: #27ae60; color: white; border: none; padding: 14px; width: 100%; cursor: pointer; font-weight: bold; border-radius: 6px; font-size: 16px; }
            label { font-size: 13px; color: #666; font-weight: bold; }
        </style>
    </head>
    <body>
        <form method="POST">
            <h2>📝 Ingresar Visita</h2>
            <input type="text" name="id_pv" placeholder="ID Punto de Venta" required>
            <input type="text" name="pv" placeholder="Punto de Venta" required>
            <input type="text" name="doc" placeholder="N. Documento">
            <input type="text" name="nombre" placeholder="Nombre completo">
            <input type="text" name="mes" placeholder="MES (Texto)" required>
            <label>Fecha Visita:</label><input type="date" name="f_visita">
            <input type="text" name="plan" placeholder="Plan">
            <label>Fecha:</label><input type="date" name="fecha">
            <input type="text" name="cobertura" placeholder="Cobertura">
            <label>Estado del Punto:</label>
            <select name="estado">
                <option value="-1">Positivo (Chulo ✅)</option>
                <option value="">Déficit (X ❌)</option>
            </select>
            <textarea name="motivo" placeholder="Motivo o comentario adicional"></textarea>
            <button type="submit" class="btn-save">ENVIAR A GOOGLE SHEETS</button>
            <p style="text-align:center;"><a href="/" style="color:#999; text-decoration:none; font-size:12px;">← Volver al listado</a></p>
        </form>
    </body>
    </html>
    """)

@app.route('/descargar_csv')
def descargar_csv():
    hoja = conectar_google()
    if isinstance(hoja, str): return "Error de conexión"
    
    valores = hoja.get_all_values()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';') # CSV delimitado por ; solicitado
    writer.writerows(valores)
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Visitas_A_POC.csv"}
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
