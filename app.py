from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- CONEXIÓN MONGODB ---
# Recuerda tener dnspython en tu requirements.txt
MONGO_URI = "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
puntos_col = db['puntos_venta']

# Interfaz HTML plana y rápida
HTML_BASE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consulta Nestle BI</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f4f4f9; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input { width: 70%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #007AFF; color: white; border: none; border-radius: 5px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
        th, td { border: 1px solid #eee; padding: 10px; text-align: left; }
        th { background: #f8f8f8; }
        .loading { display: none; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Buscador de Puntos de Venta</h2>
        <p><small>La base de datos solo se consultará al presionar buscar.</small></p>
        
        <input type="text" id="busqueda" placeholder="Nombre del punto o BMB...">
        <button onclick="buscar()">Buscar</button>
        
        <div id="cargando" class="loading">Consultando base de datos en tiempo real...</div>
        <div id="resultado"></div>
    </div>

    <script>
        async function buscar() {
            const query = document.getElementById('busqueda').value;
            const resDiv = document.getElementById('resultado');
            const loader = document.getElementById('cargando');

            if(!query) { alert("Escribe algo para buscar"); return; }

            // Mostrar cargando y limpiar tabla anterior
            loader.style.display = 'block';
            resDiv.innerHTML = "";

            try {
                const response = await fetch('/api/buscar?q=' + query);
                const datos = await response.json();
                
                loader.style.display = 'none';

                if(datos.length === 0) {
                    resDiv.innerHTML = "<p>No se encontraron resultados.</p>";
                    return;
                }

                let tabla = "<table><tr><th>Punto de Venta</th><th>BMB</th><th>Ruta</th></tr>";
                datos.forEach(p => {
                    tabla += `<tr>
                        <td>${p['Punto de Venta'] || 'N/A'}</td>
                        <td>${p['BMB'] || 'N/A'}</td>
                        <td>${p['Ruta'] || 'N/A'}</td>
                    </tr>`;
                });
                tabla += "</table>";
                resDiv.innerHTML = tabla;

            } catch (error) {
                loader.style.display = 'none';
                resDiv.innerHTML = "<p style='color:red;'>Error al conectar con el servidor.</p>";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Solo carga el HTML, NO hace consultas a Mongo aquí.
    return render_template_string(HTML_BASE)

@app.route('/api/buscar')
def api_buscar():
    query_texto = request.args.get('q', '')
    
    # Solo aquí se activa la conexión a la BD
    # Buscamos coincidencias parciales (regex) en Punto de Venta o BMB
    filtro = {
        "$or": [
            {"Punto de Venta": {"$regex": query_texto, "$options": "i"}},
            {"BMB": {"$regex": query_texto, "$options": "i"}}
        ]
    }
    
    try:
        # Traemos solo lo necesario y limitamos a 50 resultados para no saturar Render
        resultados = list(puntos_col.find(filtro, {"_id": 0}).limit(50))
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
