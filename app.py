from flask import Flask, render_template_string
import os

app = Flask(__name__)

@app.route('/')
def index():
    mes_nombre = "MARZO"
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    valores = [-1, 0, -1, -1, 0, -1] 

    registros = []
    for dia, val in zip(dias, valores):
        registros.append({
            "dia": dia,
            "valor": val,
            "simbolo": "✅" if val == -1 else "❌"
        })

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Control Júpiter</title>
        <style>
            body { font-family: sans-serif; background-color: #f4f4f9; text-align: center; padding: 20px; }
            .card { background: white; max-width: 500px; margin: auto; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; border-bottom: 1px solid #eee; }
            th { background-color: #2c3e50; color: white; }
            .pos { color: #27ae60; }
            .neg { color: #e74c3c; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 Control: {{ mes }}</h1>
            <table>
                <tr><th>Día</th><th>Estado</th></tr>
                {% for r in registros %}
                <tr>
                    <td>{{ r.dia }}</td>
                    <td class="{{ 'pos' if r.valor == -1 else 'neg' }}">{{ r.simbolo }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, mes=mes_nombre, registros=registros)

if __name__ == '__main__':
    # Render asigna un puerto automáticamente, por eso usamos os.environ
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
