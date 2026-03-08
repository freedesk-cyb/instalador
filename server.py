from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import datetime

app = Flask(__name__)

# Configuración de Base de Datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "assets.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS devices
                     (hostname TEXT PRIMARY KEY,
                      ip_address TEXT,
                      os_version TEXT,
                      cpu TEXT,
                      ram TEXT,
                      disk TEXT,
                      last_seen TEXT,
                      description TEXT DEFAULT '')''')
        
        # Verificar nuevamente por si la tabla existía pero sin la columna
        c.execute("PRAGMA table_info(devices)")
        columns = [column[1] for column in c.fetchall()]
        if 'description' not in columns:
            c.execute("ALTER TABLE devices ADD COLUMN description TEXT DEFAULT ''")
            
        conn.commit()
    except Exception as e:
        print(f"Error inicializando DB: {e}")
    finally:
        if conn: conn.close()

# Inicializar la base de datos
init_db()

@app.route('/api/report', methods=['POST'])
def report():
    data = request.json
    if not data or 'computer_name' not in data:
        return jsonify({"error": "Datos inválidos"}), 400

    hostname = str(data['computer_name']).upper()
    ip_address = data.get('ip_address', request.remote_addr)
    os_version = data.get('os_version', 'Desconocido')
    cpu = data.get('cpu', 'Desconocido')
    ram = data.get('ram', 'Desconocido')
    disk = data.get('disk', 'Desconocido')
    last_seen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Usar INSERT OR IGNORE para asegurar que la fila exista
        c.execute('''INSERT OR IGNORE INTO devices (hostname, description) VALUES (?, ?)''', (hostname, ''))
        
        # Luego actualizamos los datos técnicos (así no tocamos la descripción si ya existía)
        c.execute('''UPDATE devices 
                     SET ip_address=?, os_version=?, cpu=?, ram=?, disk=?, last_seen=?
                     WHERE hostname=?''',
                  (ip_address, os_version, cpu, ram, disk, last_seen, hostname))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"status": "ok"})

@app.route('/api/update_desc', methods=['POST'])
def update_desc():
    data = request.json
    if not data or 'hostname' not in data or 'description' not in data:
        return jsonify({"error": "Datos inválidos"}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE devices SET description = ? WHERE hostname = ?", 
              (data['description'], data['hostname']))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "ok"})

# Plantilla HTML Moderno para mostrar la tabla de equipos
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control - Asset Manager</title>
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 40px 20px; background-color: #121212; color: #ffffff; }
        .card { border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); background-color: #1e1e1e; border: 1px solid #333; }
        .table-hover tbody tr:hover { background-color: #2b2b2b; }
        .header-title { color: #0dcaf0; font-weight: bold; margin-bottom: 30px; letter-spacing: 1px;}
        .table th { background-color: #0dcaf0; color: #000; border-bottom: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center header-title">🌐 Panel de Administración de Equipos</h1>
        <div class="card p-4">
            <h5 class="mb-4">Dispositivos Conectados</h5>
            <div class="table-responsive">
                <table class="table table-dark table-hover align-middle">
                    <thead>
                        <tr>
                            <th>💻 Nombre del Equipo (Host)</th>
                            <th>🌐 IP Local</th>
                            <th>🖥️ Versión de OS</th>
                            <th>🧠 Procesador</th>
                            <th>⚡ Memoria RAM</th>
                            <th>💾 Almacenamiento (Discos)</th>
                            <th>📝 Descripción</th>
                            <th>🕒 Última Conexión</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if not devices %}
                        <tr>
                            <td colspan="8" class="text-center py-4 text-muted">No hay equipos registrados todavía. Ejecuta el cliente en un equipo para verlo aquí.</td>
                        </tr>
                        {% else %}
                            {% for device in devices %}
                            <tr>
                                <td><strong>{{ device[0] }}</strong></td>
                                <td>{{ device[1] }}</td>
                                <td>{{ device[2] }}</td>
                                <td>{{ device[3] }}</td>
                                <td>{{ device[4] }}</td>
                                <td>{{ device[5] }}</td>
                                <td>
                                    <div class="input-group input-group-sm" style="min-width: 220px;">
                                        <input type="text" class="form-control bg-dark text-white border-secondary" id="desc-{{ device[0] }}" value="{{ device[7] if device[7] else '' }}" placeholder="Añadir descripción...">
                                        <button class="btn btn-outline-info" onclick="actualizarDesc('{{ device[0] }}')" title="Guardar cambios">💾</button>
                                    </div>
                                </td>
                                <td><span class="badge bg-info text-dark">{{ device[6] }}</span></td>
                            </tr>
                            {% endfor %}
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        function actualizarDesc(hostname) {
            const container = document.getElementById('desc-' + hostname).parentElement;
            const btn = container.querySelector('button');
            const desc = document.getElementById('desc-' + hostname).value;
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '⏳';
            
            fetch('/api/update_desc', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hostname: hostname, description: desc })
            })
            .then(response => response.json())
            .then(data => {
                if(data.status === 'ok') {
                    btn.innerHTML = '✅';
                    setTimeout(() => { btn.innerHTML = originalIcon; }, 2000);
                } else {
                    alert('Error al actualizar: ' + data.error);
                    btn.innerHTML = originalIcon;
                }
            })
            .catch(err => {
                alert('Error de red al actualizar.');
                btn.innerHTML = originalIcon;
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Ordenar por el último conectado
    c.execute("SELECT hostname, ip_address, os_version, cpu, ram, disk, last_seen, description FROM devices ORDER BY last_seen DESC")
    devices = c.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, devices=devices)

if __name__ == '__main__':
    init_db()
    print("Iniciando Servidor de Asset Management...")
    print("Accede al panel en: http://localhost:8000")
    # En producción cambiar 'localhost' por '0.0.0.0' para escuchar en la red
    app.run(host='0.0.0.0', port=8000)
