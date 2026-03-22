from flask import Flask, render_template_string, request, redirect, Response
import csv
import io

app = Flask(__name__)

# Base de datos temporal (Hasta que conectes el JSON de Google)
base_datos = []

@app.route('/')
def index():
    html_tabla = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISITAS A POC</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f8f9fa; margin: 0; padding: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .logo-nestle { width: 100px; opacity: 0.6; filter: grayscale(100%); } /* Logo sutil */
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
            table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 20px; }
            th { background: #0056a0; color: white; padding: 12px; border: 1px solid #ddd; }
            td { padding: 10px; border: 1px solid #eee; text-align: center; }
            .btn { padding: 10px 15px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 13px; display: inline-block; }
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
                    <h1 style="margin:0; color: #333;">VISITAS A POC</h1>
                    <p style="color: #666; margin: 5px 0;">Control de Gestión - Marzo 2026</p>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Nestle%CC%81_textlogo.svg/2560px-Nestle%CC%81_textlogo.svg.png" class="logo-nestle" alt="Nestle">
            </div>

            <div style="margin-bottom: 20px;">
                <a href="/formulario" class="btn btn-blue">+ Nuevo Registro</a>
                <a href="/descargar_csv" class="btn btn-green">📥 Descargar CSV (Excel)</a>
            </div>

            <table>
                <tr>
                    <th>ID PV</th><th>Punto de Venta</th><th>N. Doc</th><th>Nombre</th>
                    <th>MES</th><th>Fecha Visita</th><th>Plan</th><th>Fecha</th>
                    <th>Cobertura</th><th>Estado</th><th>Motivo</th>
                </tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r.id_pv }}</td><td>{{ r.pv }}</td><td>{{ r.doc }}</td><td>{{ r.nombre }}</td>
                    <td>{{ r.mes }}</td><td>{{ r.f_visita }}</td><td>{{ r.plan }}</td><td>{{ r.fecha }}</td>
                    <td>{{ r.cobertura }}</td>
                    <td class="{{ 'chulo' if r.estado == '-1' else 'equis' }}">
                        {{ '✅' if r.estado == '-1' else '❌' }}
                    </td>
                    <td>{{ r.motivo }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_tabla, registros=base_datos)

@app.route('/descargar_csv')
def descargar_csv():
    # Generar CSV delimitado por ;
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Encabezados
    writer.writerow(['ID Punto de Venta', 'Punto de Venta', 'N. Documento', 'Nombre completo', 'MES', 'Fecha Visita', 'Plan', 'Fecha', 'Cobertura', 'Estado', 'Motivo'])
    
    for r in base_datos:
        writer.writerow([r['id_pv'], r['pv'], r['doc'], r['nombre'], r['mes'], r['f_visita'], r['plan'], r['fecha'], r['cobertura'], r['estado'], r['motivo']])
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Visitas_A_POC.csv"}
    )

# ... (Mantén aquí tu ruta de /formulario que hicimos antes) ...

if __name__ == '__main__':
    app.run(debug=True)
