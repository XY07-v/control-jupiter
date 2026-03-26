# Reemplaza la sección del script en tu HTML_SISTEMA con esta lógica mejorada

HTML_SISTEMA = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nestlé BI</title>
    <style>
        :root { --blue: #007AFF; --green: #34C759; --bg: #F2F2F7; }
        body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 10px; }
        
        /* Estilos de las pestañas y formularios se mantienen igual... */
        .content { display: none; background: white; padding: 20px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .content.active { display: block; }
        input, select, textarea { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #D1D1D6; border-radius: 12px; box-sizing: border-box; font-size: 16px; }
        button.primary { width: 100%; padding: 16px; background: var(--blue); color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; }

        /* NUEVA PANTALLA DE ÉXITO PARA MÓVIL */
        #success-card { 
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: white; z-index: 2000; justify-content: center; align-items: center; 
            text-align: center; flex-direction: column; padding: 20px; box-sizing: border-box;
        }
        .check-icon { font-size: 80px; color: var(--green); margin-bottom: 20px; }
        
        /* Overlay de carga */
        #overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.9); z-index:1500; justify-content:center; align-items:center; flex-direction:column; font-weight:bold; }
    </style>
</head>
<body>

    <div id="success-card">
        <div class="check-icon">✓</div>
        <h2 style="margin:0;">¡Registro Guardado!</h2>
        <p style="color:gray;">Los datos se sincronizaron correctamente con Nestlé BI.</p>
        <button class="primary" onclick="cerrarExito()" style="background:var(--green); margin-top:30px;">Hacer otra visita</button>
    </div>

    <div id="overlay">
        <div style="border: 4px solid #f3f3f3; border-top: 4px solid var(--blue); border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite;"></div>
        <p>Subiendo Reporte...</p>
    </div>

    <div class="tabs">
        <button class="tab-btn active" id="btn-t1" onclick="switchTab('tab-buscar')">🔍 Buscar</button>
        <button class="tab-btn" id="btn-t2" onclick="switchTab('tab-registro')">📝 Reporte</button>
    </div>

    <div id="tab-buscar" class="content active">
        <input type="text" id="q_puntos" placeholder="Nombre o BMB...">
        <button class="primary" onclick="buscarPuntos()">Consultar</button>
        <div id="res_puntos"></div>
    </div>

    <div id="tab-registro" class="content">
        <form id="form-visita">
            <input type="text" id="f_pv" placeholder="Punto de Venta" readonly style="background:#F9F9F9">
            <input type="text" id="f_bmb" placeholder="BMB" readonly style="background:#F9F9F9">
            <select id="f_estado">
                <option value="Visita Exitosa">Visita Exitosa</option>
                <option value="Cerrado">Punto Cerrado</option>
                <option value="Dañado">Equipo Dañado</option>
            </select>
            <input type="file" accept="image/*" capture="camera" onchange="preview(this, 'p1')">
            <img id="p1" class="img-preview" style="width:100%; border-radius:10px; display:none;">
            <input type="file" accept="image/*" capture="camera" onchange="preview(this, 'p2')">
            <img id="p2" class="img-preview" style="width:100%; border-radius:10px; display:none;">
            <textarea id="f_obs" placeholder="Notas..."></textarea>
            <input type="hidden" id="f_gps">
            <button type="button" class="primary" onclick="enviarVisita()">Guardar Reporte</button>
        </form>
    </div>

    <script>
        // ... (Funciones switchTab, buscarPuntos y preview se mantienen igual) ...

        async function enviarVisita() {
            const f1 = document.getElementById('p1').src;
            const f2 = document.getElementById('p2').src;
            if(!document.getElementById('f_pv').value || !f1 || !f2) return alert("Faltan datos o fotos");

            document.getElementById('overlay').style.display = 'flex';

            const payload = {
                pv: document.getElementById('f_pv').value,
                bmb: document.getElementById('f_bmb').value,
                estado: document.getElementById('f_estado').value,
                obs: document.getElementById('f_obs').value,
                gps: document.getElementById('f_gps').value,
                f1: f1, f2: f2
            };

            try {
                const r = await fetch('/api/guardar_visita', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                
                if(r.ok) {
                    // OCULTAR CARGA Y MOSTRAR PANTALLA DE ÉXITO
                    document.getElementById('overlay').style.display = 'none';
                    document.getElementById('success-card').style.display = 'flex';
                }
            } catch(e) {
                alert("Error al enviar");
                document.getElementById('overlay').style.display = 'none';
            }
        }

        function cerrarExito() {
            // Limpiar y volver al buscador
            document.getElementById('form-visita').reset();
            document.getElementById('p1').style.display = 'none';
            document.getElementById('p2').style.display = 'none';
            document.getElementById('success-card').style.display = 'none';
            switchTab('tab-buscar');
        }

        navigator.geolocation.getCurrentPosition(p => {
            document.getElementById('f_gps').value = p.coords.latitude + ',' + p.coords.longitude;
        });
    </script>
    <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
</body>
</html>
"""
