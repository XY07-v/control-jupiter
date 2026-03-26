from flask import Flask, render_template_string
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- CONEXIÓN MONGODB ---
MONGO_URI = "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['NestleDB']
puntos_col = db['puntos_venta']

@app.route('/')
def ver_puntos():
    try:
        # Traemos todos los puntos de venta
        puntos = list(puntos_col.find())
        
        if not puntos:
            return "<h1>No se encontraron datos en la colección 'puntos_venta'</h1>"

        # Obtenemos los nombres de las columnas (llaves del primer diccionario)
        columnas = puntos[0].keys()

        # Construcción de la tabla plana
        html = "<h1>Lista de Puntos de Venta</h1>"
        html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
        
        # Encabezado
        html += "<tr style='background-color: #eee;'>"
        for col in columnas:
            html += f"<th>{col}</th>"
        html += "</tr>"

        # Filas de datos
        for p in puntos:
            html += "<tr>"
            for col in columnas:
                # Convertimos a string por si hay objetos de Mongo o números
                html += f"<td>{p.get(col, '')}</td>"
            html += "</tr>"
        
        html += "</table>"
        return render_template_string(html)

    except Exception as e:
        return f"<h1>Error al conectar: {str(e)}</h1>"

if __name__ == '__main__':
    # Puerto 10000 para Render
    app.run(host='0.0.0.0', port=10000)
