from flask import Flask, render_template_string, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Ruta donde Render guarda los "Secret Files"
        ruta_secreta = "/etc/secrets/creds.json"
        
        # Si no existe (local), intenta con el nombre del archivo en la carpeta
        if not os.path.exists(ruta_secreta):
            ruta_secreta = "credenciales.json.json"

        creds = ServiceAccountCredentials.from_json_keyfile_name(ruta_secreta, scope)
        client = gspread.authorize(creds)
        
        # Conexión directa a la hoja compartida
        return client.open("Visitas_POC_Nestle").worksheet("Visitas")
    except Exception as e:
        return f"Error de conexión: {str(e)}"

@app.route('/')
def index():
    hoja = conectar_google()
    if isinstance(hoja, str):
        return f"<h2 style='color:red'>❌ Error</h2><p>{hoja}</p>"
    
    try:
        # Los días se cuentan de lunes a sábado [cite: 2026-03-11]
        registros = hoja.get_all_records()
    except Exception as e:
        return f"Error al leer datos: {e}"

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Nestlé Visitas</title></head>
    <body style="font-family:sans-serif; padding:20px; background:#f0f2f5;">
        <div style="max-width:900px; margin:auto; background:white; padding:20px; border-radius:8px;">
            <h1>Visitas POC Nestlé</h1>
            <a href="/formulario" style="padding:10px 20px; background:#0056a0; color:white; text-decoration:none; border-radius:5px;">+ Nuevo Registro</a>
            <table border="1" style="width:100%; margin-top:20px; border-collapse:collapse;">
                <tr style="background:#0056a0; color:white;">
                    <th>ID PV</th><th>Punto de Venta</th><th>Nombre</th><th>Estado</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td style="padding:8px; text-align:center;">{{ r['ID Punto de Venta'] }}</td>
                    <td style="padding:8px;">{{ r['Punto de Venta'] }}</td>
                    <td style="padding:8px;">{{ r['Nombre completo'] }}</td>
                    <td style="padding:8px; text-align:center;">
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
            # Columnas: ID PV, PV, N.Doc, Nombre, MES, F.Visita, Plan, Fecha, Cobertura, Estado, Motivo
            # MES está en formato texto [cite: 2026-02-22]
            datos = [
                request.form.get('id_pv'), request.form.get('pv'), "", 
                request.form.get('nombre'), request.form.get('mes'), "", 
                "", "", "", request.form.get('estado'), ""
            ]
            hoja.append_row(datos)
        return redirect('/')
    
    return render_template_string("""
    <div style="max-width:400px; margin:auto; padding:20px; font-family:sans-serif; background:white; border-radius:10px;">
        <h2>Nueva Visita</h2>
        <form method="POST">
            <input type="text" name="id_pv" placeholder="ID PV" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="pv" placeholder="Nombre Punto Venta" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="mes" placeholder="Mes (Ej: MARZO)" required style="width:100%; margin-bottom:10px; padding:10px;">
            <select name="estado" style="width:100%; margin-bottom:10px; padding:10px;">
                <option value="-1">Positivo (-1 ✅)</option>
                <option value="">Déficit (Vacío ❌)</option>
            </select>
            <button type="submit" style="width:100%; background:green; color:white; padding:12px; border:none; cursor:pointer;">GUARDAR</button>
        </form>
    </div>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
