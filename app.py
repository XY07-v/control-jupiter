from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

# Base de datos temporal (en memoria)
base_datos = []

@app.route('/')
def index():
    # Renderiza la tabla con los datos guardados
    html_tabla = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Plataforma Júpiter</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
            .container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 10px; shadow: 0 2px 10px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #2c3e50; color: white; }
            .btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            .chulo { color: green; font-weight: bold; }
            .equis { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Panel de Control Júpiter</h1>
            <a href="/formulario" class="btn">+ Nuevo Registro</a>
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

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Capturamos los datos del formulario
        nuevo_registro = {
            "id_pv": request.form['id_pv'],
            "pv": request.form['pv'],
            "doc": request.form['doc'],
            "nombre": request.form['nombre'],
            "mes": request.form['mes'], # Regla: Formato Texto
            "f_visita": request.form['f_visita'],
            "plan": request.form['plan'],
            "fecha": request.form['fecha'],
            "cobertura": request.form['cobertura'],
            "estado": request.form['estado'], # -1 es Positivo, "" es Déficit
            "motivo": request.form['motivo']
        }
        base_datos.append(nuevo_registro)
        return redirect('/')

    # Diseño del Formulario
    html_form = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nuevo Registro</title>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
            form { background: white; padding: 20px; border-radius: 10px; width: 400px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
            input, select, textarea { width: 100%; padding: 8px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
            button { width: 100%; background: #27ae60; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <form method="POST">
            <h2>📝 Ingresar Datos</h2>
            <input type="text" name="id_pv" placeholder="ID Punto de Venta" required>
            <input type="text" name="pv" placeholder="Punto de Venta" required>
            <input type="text" name="doc" placeholder="N. Documento">
            <input type="text" name="nombre" placeholder="Nombre Completo">
            <input type="text" name="mes" placeholder="MES (Ej: MARZO)" required>
            <input type="date" name="f_visita" placeholder="Fecha Visita">
            <input type="text" name="plan" placeholder="Plan">
            <input type="date" name="fecha" placeholder="Fecha">
            <input type="text" name="cobertura" placeholder="Cobertura">
            
            <label>Estado:</label>
            <select name="estado">
                <option value="-1">Positivo (Chulo ✅)</option>
                <option value="0">Déficit (X ❌)</option>
            </select>
            
            <textarea name="motivo" placeholder="Motivo"></textarea>
            <button type="submit">Guardar Registro</button>
            <br><br>
            <a href="/">Volver al listado</a>
        </form>
    </body>
    </html>
    """
    return render_template_string(html_form)

if __name__ == '__main__':
    app.run(debug=True)
