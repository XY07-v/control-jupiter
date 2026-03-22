from flask import Flask, render_template_string, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

def conectar():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Verifica que el archivo se llame exactamente así en tu carpeta
        creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        client = gspread.authorize(creds)
        # Nombre exacto del libro y la hoja
        return client.open("Visitas_POC_Nestle").worksheet("Visitas")
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {e}")
        return str(e)

@app.route('/')
def index():
    hoja = conectar()
    if isinstance(hoja, str):
        return f"<h1>Error de Configuración</h1><p>{hoja}</p><p>Revisa el nombre del archivo y permisos.</p>"
    
    try:
        # Leemos los datos para la tabla
        registros = hoja.get_all_records()
    except:
        registros = []

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f4f4f4; }
            .container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
            th { background: #0056a0; color: white; }
            .btn { background: #0056a0; color: white; padding: 10px; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>VISITAS A POC (Nestlé)</h1>
            <a href="/formulario" class="btn">+ Nuevo Registro</a>
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
                    <td>{{ '✅' if r['Estado'] == '-1' or r['Estado'] == -1 else '❌' }}</td>
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
        hoja = conectar()
        # Recolectamos datos del formulario
        datos = [
            request.form.get('id_pv'), request.form.get('pv'), 
            request.form.get('doc'), request.form.get('nombre'),
            request.form.get('mes'), request.form.get('f_visita'),
            request.form.get('plan'), request.form.get('fecha'),
            request.form.get('cobertura'), request.form.get('estado'),
            request.form.get('motivo')
        ]
        try:
            hoja.append_row(datos)
            return redirect('/')
        except Exception as e:
            return f"<h1>Error al guardar</h1><p>{e}</p>"

    return render_template_string("""
    <form method="POST" style="max-width:400px; margin:auto; padding:20px; border:1px solid #ccc;">
        <h2>Nueva Visita</h2>
        ID PV: <input type="text" name="id_pv" required><br><br>
        Punto Venta: <input type="text" name="pv" required><br><br>
        N. Doc: <input type="text" name="doc"><br><br>
        Nombre: <input type="text" name="nombre"><br><br>
        MES: <input type="text" name="mes" value="MARZO"><br><br>
        Fecha Visita: <input type="date" name="f_visita"><br><br>
        Plan: <input type="text" name="plan"><br><br>
        Fecha: <input type="date" name="fecha"><br><br>
        Cobertura: <input type="text" name="cobertura"><br><br>
        Estado: 
        <select name="estado">
            <option value="-1">Positivo (-1)</option>
            <option value="">Déficit (Vacío)</option>
        </select><br><br>
        Motivo: <textarea name="motivo"></textarea><br><br>
        <button type="submit">GUARDAR EN GOOGLE</button>
    </form>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
