from flask import Flask, render_template_string, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# --- RECONSTRUCCIÓN MANUAL DE LA LLAVE ---
# Esto evita que los caracteres \n se rompan al subir el código
pk_parts = [
    "-----BEGIN PRIVATE KEY-----",
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCyaP+mEwcJorvZ",
    "f/fRUTkH5eTaB/MOgShGChwRZfQxt2KPxiI/5EI3rLavWkCeEJ1Ad4N/Mn5jZ/yj",
    "s8HywpipBWCnJf+juPo5Vw3n3KaP0lhC/td7CFgBQpHhSXwm/dLBSNKwjVAkmlQJ",
    "yRc9MLta8Tsg8YcP3bkLEchsNivxtC5PQ8ic0X0Bw1fyI/8f1qqhRoqw710lSXFg",
    "VL6fuY4hvmY2TRVQKFqaLWymAziJw6gimdAshInP9ArYTzN0Oc38uUdS5gtV9+F3",
    "QwhYHBIT2oC1KXVf8uKjB6x4qusvqRLbd+utE6sJvcmXtBxjX3edacAI+uxRVvf1",
    "XznL8p+JAgMBAAECggEAIjF2gc1WxXV/fD2G8QKYpBdfB5yLbGW7osTQQVNhfF/R",
    "z41hRg6I1GPRNYVeKg00HkVpmejDCWlGJdfPXagHGynRLufc+XN73Z5+J0iGUb02",
    "NkziXo2oVEF+dQeg+FYgXPQIkVbcG8/KOH/maM9csR7XvsYbpSJREzqKx5aQUIfu",
    "fH9Q6k41DOzrsmm93nxSEEVjVym2hc6afYiYnpm9kbsZXrDG2nsi0mLpxoTfn0d1",
    "GQbornKo4SVw6qHcWuDbo6a3eeyBLRpKV968APSiSMAKamlYGcIHxhX1dxDUWwtf",
    "j3N/skW/oqSu0M2gAVNkdrt3v/w4AL8eALYIqOxtCwKBgQDciXM4yNnzC2mYI/bJ",
    "slz6dWU2xQZoL2w1822GzO1/EnHQk3kgVhn4B5ZdZ9f41s+JdFqavJvNm24zW4dY",
    "u4XOkQlsXV2EAisi/aph3NO3GI4e/Pab7ldnIVPaw2xPZ4KBVgXpbKyCB8QLp3pm",
    "+VKywKvpSG5a3QgZL2MNO4Uf7wKBgQDPGV9A43bnqbJn18RsIwIZfXz1IxIvQCwK",
    "b59R2K4TC36eYkmTq8LtVq86gO9qnnqZOU8KchKh8AO51MBLDGet7PVnceaWJxA6",
    "UarqIjP/7iftIQO/cf3vFkHi6MsO24dWRByZBGGJbIXVgnu1FtMf5zqqMw/3jjCh",
    "H49zzt1ABwKBgQCcOvcYJBlaNxx//gJHUobRmzavfRYT2nyDH8bYdvZMTem5A7AM",
    "O1K8Rcu8seLq0mpFitrgwXpyRojj8xRHxNh+xHpzfRTRfqPGbwMzvrdw/wE3bKbb",
    "QhZC5fY8hLKG8eIe86zOdwEiQJQeWW+54Sg3n4xpf7lFv02MYeh+qEqfmwKBgFe2",
    "ikZkUJ8Lm3kpxJJ8PU5ofL0ibng+uKhu4E589DUywBz6yejWbYeyGCMyKrTAjHJK",
    "+HQXHlch3aIePpdKmLrsSn/WmO/teY0Ju9bQR6/UwWpIelriP8e8aIlfSWlwhyB9",
    "VpNkbJ8UrJZiXlyzXxX7DDi7yb5ypZwITuygp8qPAoGAToc4wBn0DkKjdHETfdd+",
    "NEsoU7gpYMiNv6rKNWY/3MUX+iFcrc7oWvPCZqr3iCuQY38DE+EbYhJne8iG8Ekr",
    "0ey7TqvLKSuHxlaatrbPsUjtRv2TDFbO1XquUwkvILSl48qoUWkbzIfpxr0ATeeF",
    "T/bRHOBL8kLrpeg6ARzpr+g=",
    "-----END PRIVATE KEY-----"
]
# Unimos las partes con saltos de línea reales (\n)
private_key_clean = "\n".join(pk_parts)

info_llave = {
    "type": "service_account",
    "project_id": "steel-time-331710",
    "private_key_id": "262e240b07b546512b457ec41f2a418a36aa53ec",
    "private_key": private_key_clean,
    "client_email": "robot-jupiter@steel-time-331710.iam.gserviceaccount.com",
    "client_id": "114862181437476661415",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robot-jupiter%40steel-time-331710.iam.gserviceaccount.com"
}

def conectar():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llave, scope)
        client = gspread.authorize(creds)
        return client.open("Visitas_POC_Nestle").worksheet("Visitas")
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    hoja = conectar()
    if isinstance(hoja, str):
        return f"<h2 style='color:red'>Error de Firma JWT:</h2><p>{hoja}</p><p>Reintenta subiendo el código de nuevo.</p>"
    
    try:
        registros = hoja.get_all_records()
    except:
        registros = []

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>VISITAS POC</title></head>
    <body style="font-family:sans-serif; padding:20px;">
        <h1>Control de Visitas Nestlé</h1>
        <a href="/formulario" style="padding:10px; background:blue; color:white; text-decoration:none;">+ Nuevo Registro</a>
        <table border="1" style="width:100%; margin-top:20px; border-collapse:collapse;">
            <tr style="background:#eee;">
                <th>ID PV</th><th>Punto de Venta</th><th>Nombre</th><th>Estado</th>
            </tr>
            {% for r in registros %}
            <tr>
                <td>{{ r['ID Punto de Venta'] }}</td>
                <td>{{ r['Punto de Venta'] }}</td>
                <td>{{ r['Nombre completo'] }}</td>
                <td>{{ '✅' if r['Estado'] == '-1' or r['Estado'] == -1 else '❌' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, registros=registros)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        hoja = conectar()
        datos = [
            request.form.get('id_pv'), request.form.get('pv'), 
            "", request.form.get('nombre'), request.form.get('mes'), 
            "", "", "", "", request.form.get('estado'), ""
        ]
        if not isinstance(hoja, str):
            hoja.append_row(datos)
        return redirect('/')
    
    return render_template_string("""
    <form method="POST" style="max-width:300px; margin:auto;">
        <h2>Registro</h2>
        ID: <input type="text" name="id_pv" required style="width:100%;"><br><br>
        PV: <input type="text" name="pv" required style="width:100%;"><br><br>
        Nombre: <input type="text" name="nombre" style="width:100%;"><br><br>
        MES: <input type="text" name="mes" value="MARZO" style="width:100%;"><br><br>
        Estado: <select name="estado" style="width:100%;">
            <option value="-1">Positivo (-1 ✅)</option>
            <option value="">Déficit (Vacío ❌)</option>
        </select><br><br>
        <button type="submit" style="width:100%; padding:10px; background:green; color:white;">GUARDAR</button>
    </form>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
