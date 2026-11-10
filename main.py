from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import mysql.connector
import os
import json
import urllib.parse as urlparse
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "clave_secura_agro_jk"

def obtener_conexion():
    try:
        # Si está en Render o hay una URL de nube configurada, usa la nube
        db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_ADDON_URI") or os.environ.get("SQLALCHEMY_DATABASE_URI")
        if db_url:
            if db_url.startswith("mysql+pymysql://"):
                db_url = db_url.replace("mysql+pymysql://", "mysql://", 1)
            elif db_url.startswith("mysql+mysqlconnector://"):
                db_url = db_url.replace("mysql+mysqlconnector://", "mysql://", 1)
            
            parsed = urlparse.urlparse(db_url)
            return mysql.connector.connect(
                host=parsed.hostname,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                port=parsed.port or 3306
            )
        
        # SI ESTÁS EN TU PC (LOCAL), SE CONECTA DIRECTO A TU XAMPP (agro_sistema)
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="agro_sistema",
            port=3306
        )
    except Exception as e:
        print("Error de conexión a la base de datos:", e)
        return None

def inicializar_base_datos():
    try:
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    proveedor VARCHAR(150) NOT NULL,
                    factura VARCHAR(50) NOT NULL,
                    fecha_hora DATETIME NOT NULL,
                    monto_total DECIMAL(10,2) NOT NULL,
                    monto_abonado DECIMAL(10,2) NOT NULL,
                    saldo_pendiente DECIMAL(10,2) NOT NULL,
                    medio_pago VARCHAR(100) NOT NULL,
                    items TEXT NOT NULL,
                    abonos TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conexion.commit()
            cursor.close()
            conexion.close()
    except Exception as e:
        print("Aviso al inicializar tablas:", e)

inicializar_base_datos()

def render_template_con_branding(template_name, **kwargs):
    html_content = render_template(template_name, **kwargs)
    soup = BeautifulSoup(html_content, 'html.parser')
    if soup.find('title'):
        soup.find('title').string = "Promotores del Agro"
    return str(soup)

@app.route('/')
def index():
    return render_template_con_branding('index.html', error=False)

@app.route('/login', methods=['POST'])
def login():
    perfil = request.form.get('perrol')
    if perfil == 'gerente':
        if request.form.get('password', '') == 'Tubandera2714':  
            session['rol'] = 'gerente'
            return redirect(url_for('dashboard'))
        return render_template_con_branding('index.html', error=True)
    else:
        session['rol'] = 'empleado'
        return redirect(url_for('ventas'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('dashboard.html')

# --- API COMPRAS LISTAR (Mapeo exacto para la interfaz) ---
@app.route('/api/compras/listar', methods=['GET'])
def api_listar_compras():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify([])
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, proveedor, factura, 
                   DATE_FORMAT(fecha_hora, '%Y-%m-%d') AS fecha, 
                   monto_total AS montoTotal, 
                   monto_abonado AS amortizado, 
                   saldo_pendiente AS saldo, 
                   medio_pago AS medio, 
                   items, abonos 
            FROM compras ORDER BY id DESC
        """)
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        for r in res:
            r['items'] = json.loads(r['items']) if r.get('items') else []
            r['abonos'] = json.loads(r['abonos']) if r.get('abonos') else []
        return jsonify(res)
    except Exception as e:
        print("Error en api_listar_compras:", e)
        return jsonify([])

@app.route('/api/compras/guardar', methods=['POST'])
def api_guardar_compra():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        c_id = data.get('id')
        items = json.dumps(data.get('items', []))
        abonos = json.dumps(data.get('abonos', []))
        
        if c_id:
            cursor.execute("""UPDATE compras SET proveedor=%s, factura=%s, fecha_hora=%s, monto_total=%s, monto_abonado=%s, saldo_pendiente=%s, medio_pago=%s, items=%s, abonos=%s WHERE id=%s""",
                           (data.get('proveedor'), data.get('factura'), data.get('fecha'), float(data.get('montoTotal',0)), float(data.get('amortizado',0)), float(data.get('saldo',0)), data.get('medio'), items, abonos, c_id))
        else:
            cursor.execute("""INSERT INTO compras (proveedor, factura, fecha_hora, monto_total, monto_abonado, saldo_pendiente, medio_pago, items, abonos) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                           (data.get('proveedor'), data.get('factura'), data.get('fecha'), float(data.get('montoTotal',0)), float(data.get('amortizado',0)), float(data.get('saldo',0)), data.get('medio'), items, abonos))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/compras/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_compra(id):
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM compras WHERE id = %s", (id,))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/compras')
def compras():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('compras.html')

@app.route('/ventas')
def ventas():
    if 'rol' not in session: return redirect(url_for('index'))
    return render_template_con_branding('ventas.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)