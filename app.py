from flask import Flask, render_template_string, request, redirect, Response
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import csv
import io

app = Flask(__name__)

# --- CREDENCIALES INTEGRADAS ---
# Se utiliza el contenido exacto proporcionado
info_llave = {
  "type": "service_account",
  "project_id": "steel-time-331710",
  "private_key_id": "262e240b07b546512b457ec41f2a418a36aa53ec",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCyaP+mEwcJorvZ\nf/fRUTkH5eTaB/MOgShGChwRZfQxt2KPxiI/5EI3rLavWkCeEJ1Ad4N/Mn5jZ/yj\ns8HywpipBWCnJf+juPo5Vw3n3KaP0lhC/td7CFgBQpHhSXwm/dLBSNKwjVAkmlQJ\nyRc9MLta8Tsg8YcP3bkLEchsNivxtC5PQ8ic0X0Bw1fyI/8f1qqhRoqw710lSXFg\nVL6fuY4hvmY2TRVQKFqaLWymAziJw6gimdAshInP9ArYTzN0Oc38uUdS5gtV9+F3\nQwhYHBIT2oC1KXVf8uKjB6x4qusvqRLbd+utE6sJvcmXtBxjX3edacAI+uxRVvf1\nXznL8p+JAgMBAAECggEAIjF2gc1WxXV/fD2G8QKYpBdfB5yLbGW7osTQQVNhfF/R\nz41hRg6I1GPRNYVeKg00HkVpmejDCWlGJdfPXagHGynRLufc+XN73Z5+J0iGUb02\nNkziXo2oVEF+dQeg+FYgXPQIkVbcG8/KOH/maM9csR7XvsYbpSJREzqKx5aQUIfu\nfH9Q6k41DOzrsmm93nxSEEVjVym2hc6afYiYnpm9kbsZXrDG2nsi0mLpxoTfn0d1\nGQbornKo4SVw6qHcWuDbo6a3eeyBLRpKV968APSiSMAKamlYGcIHxhX1dxDUWwtf\nj3N/skW/oqSu0M2gAVNkdrt3v/w4AL8eALYIqOxtCwKBgQDciXM4yNnzC2mYI/bJ\nslz6dWU2xQZoL2w1822GzO1/EnHQk3kgVhn4B5ZdZ9f41s+JdFqavJvNm24zW4dY\nu4XOkQlsXV2EAisi/aph3NO3GI4e/Pab7ldnIVPaw2xPZ4KBVgXpbKyCB8QLp3pm\n+VKywKvpSG5a3QgZL2MNO4Uf7wKBgQDPGV9A43bnqbJn18RsIwIZfXz1IxIvQCwK\nb59R2K4TC36eYkmTq8LtVq86gO9qnnqZOU8KchKh8AO51MBLDGet7PVnceaWJxA6\nUarqIjP/7iftIQO/cf3vFkHi6MsO24dWRByZBGGJbIXVgnu1FtMf5zqqMw/3jjCh\nH49zzt1ABwKBgQCcOvcYJBlaNxx//gJHUobRmzavfRYT2nyDH8bYdvZMTem5A7AM\nO1K8Rcu8seLq0mpFitrgwXpyRojj8xRHxNh+xHpzfRTRfqPGbwMzvrdw/wE3bKbb\nQhZC5fY8hLKG8eIe86zOdwEiQJQeWW+54Sg3n4xpf7lFv02MYeh+qEqfmwKBgFe2\nikZkUJ8Lm3kpxJJ8PU5ofL0ibng+uKhu4E589DUywBz6yejWbYeyGCMyKrTAjHJK\n+HQXHlch3aIePpdKmLrsSn/WmO/teY0Ju9bQR6/UwWpIelriP8e8aIlfSWlwhyB9\nVpNkbJ8UrJZiXlyzXxX7DDi7yb5ypZwITuygp8qPAoGAToc4wBn0DkKjdHETfdd+\nNEsoU7gpYMiNv6rKNWY/3MUX+iFcrc7oWvPCZqr3iCuQY38DE+EbYhJne8iG8Ekr\n0ey7TqvLKSuHxlaatrbPsUjtRv2TDFbO1XquUwkvILSl48qoUWkbzIfpxr0ATeeF\nT/bRHOBL8kLrpeg6ARzpr+g=\n-----END PRIVATE KEY-----\n",
  "client_email": "robot-jupiter@steel-time-331710.iam.gserviceaccount.com",
  "client_id": "114862181437476661415",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robot-jupiter%40steel-time-331710.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # PROCESO DE REPARACIÓN DE CLAVE (JWT FIX)
        # Se asegura que los caracteres \n se interpreten como saltos de línea reales
        cred_dict = info_llave.copy()
        cred_dict["private_key"] = cred_dict["private_key"].replace('\\n', '\n')
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
        client = gspread.authorize(creds)
        
        # Conexión al libro compartido
        libro = client.open("Visitas_POC_Nestle")
        hoja = libro.worksheet("Visitas")
        return hoja
    except Exception as e:
        return f"Error de autenticación: {str(e)}"

@app.route('/')
def index():
    hoja = conectar_google()
    if isinstance(hoja, str):
        return f"<h2 style='color:red'>Estado: Desconectado</h2><p>{hoja}</p>"
    
    registros = []
    try:
        # Los días se cuentan de lunes a sábado [cite: 2026-03-11]
        registros = hoja.get_all_records()
    except:
        registros = []

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: sans-serif; background: #f4f7f6; padding: 20px; }
            .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th { background: #0056a0; color: white; padding: 12px; text-align: center; }
            td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            .btn { background: #0056a0; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
            .chulo { color: #27ae60; font-weight: bold; }
            .equis { color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Visitas POC Nestlé</h1>
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
                    <td class="{{ 'chulo' if r['Estado'] == '-1' or r['Estado'] == -1 else 'equis' }}">
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
            # El -1 es positivo (chulo) y el vacío es déficit (x) [cite: 2026-03-09]
            # La columna MES debe estar en formato texto [cite: 2026-02-22]
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
    <div style="max-width:400px; margin:auto; font-family:sans-serif; padding:20px; background:white; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
        <h2 style="text-align:center">Registrar Visita</h2>
        <form method="POST">
            <input type="text" name="id_pv" placeholder="ID Punto de Venta" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="pv" placeholder="Nombre Punto Venta" required style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin-bottom:10px; padding:10px;">
            <input type="text" name="mes" placeholder="MES (Texto)" required style="width:100%; margin-bottom:10px; padding:10px;">
            <label style="font-size:12px;">Estado:</label>
            <select name="estado" style="width:100%; margin-bottom:10px; padding:10px;">
                <option value="-1">Positivo (-1 ✅)</option>
                <option value="">Déficit (Vacío ❌)</option>
            </select>
            <button type="submit" style="width:100%; background:#27ae60; color:white; padding:12px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">GUARDAR EN GOOGLE</button>
        </form>
        <p style="text-align:center"><a href="/" style="color:#999; text-decoration:none; font-size:12px;">Volver</a></p>
    </div>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
