from flask import Flask, render_template_string, request, redirect, Response
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import csv
import io

app = Flask(__name__)

# --- CONFIGURACIÓN DIRECTA ---
# Pegamos los datos de tu archivo credenciales.json.json aquí para evitar errores de firma JWT
info_llave = {
  "type": "service_account",
  "project_id": "steel-time-331710",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCyaP+mEwcJorvZ\nf/fRUTkH5eTaB/MOgShGChwRZfQxt2KPxiI/5EI3rLavWkCeEJ1Ad4N/Mn5jZ/yj\ns8HywpipBWCnJf+juPo5Vw3n3KaP0lhC/td7CFgBQpHhSXwm/dLBSNKwjVAkmlQJ\nyRc9MLta8Tsg8YcP3bkLEchsNivxtC5PQ8ic0X0Bw1fyI/8f1qqhRoqw710lSXFg\nVL6fuY4hvmY2TRVQKFqaLWymAziJw6gimdAshInP9ArYTzN0Oc38uUdS5gtV9+F3\nQwhYHBIT2oC1KXVf8uKjB6x4qusvqRLbd+utE6sJvcmXtBxjX3edacAI+uxRVvf1\nXznL8p+JAgMBAAECggEAIjF2gc1WxXV/fD2G8QKYpBdfB5yLbGW7osTQQVNhfF/R\nz41hRg6I1GPRNYVeKg00HkVpmejDCWlGJdfPXagHGynRLufc+XN73Z5+J0iGUb02\nNkziXo2oVEF+dQeg+FYgXPQIkVbcG8/KOH/maM9csR7XvsYbpSJREzqKx5aQUIfu\nfH9Q6k41DOzrsmm93nxSEEVjVym2hc6afYiYnpm9kbsZXrDG2nsi0mLpxoTfn0d1\nGQbornKo4SVw6qHcWuDbo6a3eeyBLRpKV968APSiSMAKamlYGcIHxhX1dxDUWwtf\nj3N/skW/oqSu0M2gAVNkdrt3v/w4AL8eALYIqOxtCwKBgQDciXM4yNnzC2mYI/bJ\nslz6dWU2xQZoL2w1822GzO1/EnHQk3kgVhn4B5ZdZ9f41s+JdFqavJvNm24zW4dY\nu4XOkQlsXV2EAisi/aph3NO3GI4e/Pab7ldnIVPaw2xPZ4KBVgXpbKyCB8QLp3pm\n+VKywKvpSG5a3QgZL2MNO4Uf7wKBgQDPGV9A43bnqbJn18RsIwIZfXz1IxIvQCwK\nb59R2K4TC36eYkmTq8LtVq86gO9qnnqZOU8KchKh8AO51MBLDGet7PVnceaWJxA6\nUarqIjP/7iftIQO/cf3vFkHi6MsO24dWRByZBGGJbIXVgnu1FtMf5zqqMw/3jjCh\nH49zzt1ABwKBgQCcOvcYJBlaNxx//gJHUobRmzavfRYT2nyDH8bYdvZMTem5A7AM\nO1K8Rcu8seLq0mpFitrgwXpyRojj8xRHxNh+xHpzfRTRfqPGbwMzvrdw/wE3bKbb\nQhZC5fY8hLKG8eIe86zOdwEiQJQeWW+54Sg3n4xpf7lFv02MYeh+qEqfmwKBgFe2\nikZkUJ8Lm3kpxJJ8PU5ofL0ibng+uKhu4E589DUywBz6yejWbYeyGCMyKrTAjHJK\n+HQXHlch3aIePpdKmLrsSn/WmO/teY0Ju9bQR6/UwWpIelriP8e8aIlfSWlwhyB9\nVpNkbJ8UrJZiXlyzXxX7DDi7yb5ypZwITuygp8qPAoGAToc4wBn0DkKjdHETfdd+\nNEsoU7gpYMiNv6rKNWY/3MUX+iFcrc7oWvPCZqr3iCuQY38DE+EbYhJne8iG8Ekr\n0ey7TqvLKSuHxlaatrbPsUjtRv2TDFbO1XquUwkvILSl48qoUWkbzIfpxr0ATeeF\nT/bRHOBL8kLrpeg6ARzpr+g=\n-----END PRIVATE KEY-----\n",
  "client_email": "robot-jupiter@steel-time-331710.iam.gserviceaccount.com",
  "token_uri": "https://oauth2.googleapis.com/token",
}

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Usamos la configuración directa que ya tiene los saltos de línea corregidos
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llave, scope)
        client = gspread.authorize(creds)
        # Accedemos al libro y hoja indicados
        return client.open("Visitas_POC_Nestle").worksheet("Visitas")
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    hoja = conectar_google()
    if isinstance(hoja, str):
        return f"<h2 style='color:red'>Error de Conexión Técnica</h2><p>{hoja}</p>"
    
    registros = []
    try:
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
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th { background: #0056a0; color: white; padding: 10px; }
            td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            .btn { background: #0056a0; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>VISITAS A POC - Nestlé</h1>
            <div style="margin-bottom:20px;">
                <a href="/formulario" class="btn">+ Nuevo Registro</a>
            </div>
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
            hoja.append_row(datos)
        return redirect('/')

    return render_template_string("""
    <form method="POST" style="max-width:400px; margin:auto; font-family:sans-serif; background:white; padding:30px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.2);">
        <h2 style="text-align:center">Nueva Visita</h2>
        <input type="text" name="id_pv" placeholder="ID Punto Venta" required style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="pv" placeholder="Nombre Punto Venta" required style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="doc" placeholder="N. Documento" style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="nombre" placeholder="Nombre completo" style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="mes" placeholder="MES (Texto)" required style="width:100%; margin:8px 0; padding:10px;">
        <label>Fecha Visita:</label><input type="date" name="f_visita" style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="plan" placeholder="Plan" style="width:100%; margin:8px 0; padding:10px;">
        <label>Fecha Registro:</label><input type="date" name="fecha" style="width:100%; margin:8px 0; padding:10px;">
        <input type="text" name="cobertura" placeholder="Cobertura" style="width:100%; margin:8px 0; padding:10px;">
        <select name="estado" style="width:100%; margin:8px 0; padding:10px;">
            <option value="-1">Positivo (-1 ✅)</option>
            <option value="">Déficit (Vacío ❌)</option>
        </select>
        <textarea name="motivo" placeholder="Motivo" style="width:100%; margin:8px 0; padding:10px;"></textarea>
        <button type="submit" style="width:100%; background:#27ae60; color:white; padding:15px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">GUARDAR EN GOOGLE</button>
    </form>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)s
  
