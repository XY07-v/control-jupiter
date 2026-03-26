# ... (Mantener importaciones, conexión MongoDB, calcular_distancia y CSS_GERENCIAL igual) ...

@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    # Si es asesor, ahora lo mandamos a un menú principal o directamente al formulario
    # Para mantenerlo simple, si es asesor lo dejamos entrar al Dash pero con interfaz limitada
    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body>
        <header>
            <div style="font-weight: 800; font-size: 20px; color: var(--nestle-blue);">Nestlé BI <span style="font-weight: 300;">Dash</span></div>
            <div style="font-size: 13px;">{session.get('user_name')} <a href="/logout" style="margin-left:10px; color:red; text-decoration:none;">Salir</a></div>
        </header>
        
        <div class="container">
            <div class="action-bar">
                <a href="/formulario" class="btn-g btn-primary">➕ Nuevo Reporte</a>
                <button class="btn-g btn-outline" onclick="cargar('puntos')">📍 Consultar Puntos</button>
                {" ".join([
                    '<button class="btn-g btn-outline" onclick="cargar(\'validaciones\')">⚠️ Validaciones</button>',
                    '<button class="btn-g btn-outline" onclick="cargar(\'visitas\')">📋 Historial</button>',
                    '<button class="btn-g btn-outline" onclick="openModal(\'m_csv\')">📥 Importar</button>'
                ]) if session.get('role') == 'admin' else ''}
            </div>

            <div id="grid_data" class="grid-cards">
                <p style="text-align:center; color:gray; grid-column: 1/-1;">Seleccione una opción arriba para comenzar.</p>
            </div>
        </div>

        <div id="m_global" class="modal"><div class="modal-content" id="m_body"></div></div>
        
        <div id="m_csv" class="modal"><div class="modal-content">
            <h3>Carga Masiva de Puntos</h3>
            <input type="file" id="f_csv" accept=".csv">
            <button class="btn-g btn-primary" style="width:100%" onclick="subirCSV()">Procesar</button>
            <button class="btn-g btn-outline" style="width:100%; margin-top:10px;" onclick="closeModal()">Cerrar</button>
        </div></div>

        <script>
            const userRole = "{session.get('role')}";
            function openModal(id) {{ document.getElementById(id).style.display='block'; }}
            function closeModal() {{ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); }}

            async function cargar(tipo) {{
                const grid = document.getElementById('grid_data');
                grid.innerHTML = 'Cargando...';
                const r = await fetch('/api/get/' + tipo);
                const data = await r.json();
                
                let html = '';
                data.forEach(d => {{
                    if(tipo === 'puntos') {{
                        html += `<div class="card-mini">
                            <div style="margin-bottom:10px;"><b>${{d['Punto de Venta']}}</b><br><small>BMB: ${{d.BMB || 'N/A'}}</small></div>
                            ${{userRole === 'admin' ? `<button class="btn-g btn-outline" style="width:100%; padding:6px;" onclick="formEdit('puntos', '${{d._id}}')">Editar</button>` : ''}}
                        </div>`;
                    } else if(tipo === 'validaciones') {{
                         html += `<div class="card-mini" style="border-left: 5px solid #FF9500;">
                            <span class="badge badge-warn">Pendiente</span>
                            <div style="margin: 10px 0;"><b>${{d.pv}}</b><br><small>${{d.fecha}}</small></div>
                            <button class="btn-g btn-primary" style="width:100%; padding:6px;" onclick="verDetalleValidar('${{d._id}}')">Revisar</button>
                        </div>`;
                    }}
                    // ... (resto de condiciones de validación/usuarios/visitas se mantienen igual)
                }});
                grid.innerHTML = html || '<p>No hay registros.</p>';
            }}
            // ... (Resto de funciones JS: verDetalleValidar, formEdit, guardarEdicion, etc., se mantienen igual)
        </script>
    </body></html>
    """)

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if 'user_id' not in session: return redirect('/login')
    if request.method == 'POST':
        # ... (Mantener lógica de guardado de visitas exactamente igual) ...
        return redirect('/formulario?msg=OK')

    pts = list(puntos_col.find({}, {"Punto de Venta": 1, "BMB": 1, "_id": 0}))
    opts = "".join([f'<option value="{p["Punto de Venta"]}">' for p in pts])
    
    # Cambio solicitado: Botón Volver -> Cerrar Sesión (para Asesor)
    btn_footer = '<a href="/logout" class="btn-g btn-danger" style="margin-top:10px; justify-content:center;">Cerrar Sesión</a>'
    if session.get('role') == 'admin':
        btn_footer = '<a href="/" class="btn-g btn-outline" style="margin-top:10px; justify-content:center;">Volver al Panel</a>'

    return render_template_string(f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS_GERENCIAL}</head>
    <body onload="navigator.geolocation.getCurrentPosition(p=>document.getElementById('gps').value=p.coords.latitude+','+p.coords.longitude)">
        <div class="container" style="max-width:450px;">
            <div class="card-mini" style="padding:25px;">
                <h2 style="color:var(--nestle-blue); text-align:center; margin-top:0;">Nuevo Reporte</h2>
                <form method="POST" enctype="multipart/form-data">
                    <label>Punto de Venta</label>
                    <input list="pts" name="pv" id="pv_i" oninput="vincular(this.value)" required>
                    <datalist id="pts">{opts}</datalist>
                    <label>BMB Detectado</label><input type="text" name="bmb" id="bmb_i" required>
                    <label>Motivo</label><select name="motivo"><option>Visita Exitosa</option><option>Cerrado</option></select>
                    <label>Fecha</label><input type="date" name="fecha" value="{datetime.now().strftime('%Y-%m-%d')}">
                    <label>Fotos</label>
                    <input type="file" name="f1" accept="image/*" capture="camera" style="font-size:12px;">
                    <input type="file" name="f2" accept="image/*" capture="camera" style="font-size:12px;">
                    <input type="hidden" name="gps" id="gps">
                    <button class="btn-g btn-primary" style="width:100%; margin-top:15px; justify-content:center;">Enviar Reporte</button>
                    {btn_footer}
                </form>
            </div>
        </div>
        <script>
            const pts = {json.dumps(pts)};
            function vincular(val) {{
                const p = pts.find(x => x['Punto de Venta'] === val);
                if(p) document.getElementById('bmb_i').value = p.BMB || '';
            }}
        </script>
    </body></html>
    """)

# ... (Mantener el resto de APIs, login y main igual) ...
