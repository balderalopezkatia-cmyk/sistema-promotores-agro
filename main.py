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
        
        host = os.environ.get("MYSQL_ADDON_HOST", "bbdxmfpaqjvnaoqv46uu-mysql.services.clever-cloud.com")
        user = os.environ.get("MYSQL_ADDON_USER", "ukq046fffz9ikj3j")
        password = os.environ.get("MYSQL_ADDON_PASSWORD", "SEP21cGpyJ2X5lW8FEIM")
        database = os.environ.get("MYSQL_ADDON_DB", "bbdxmfpaqjvnaoqv46uu")
        port = int(os.environ.get("MYSQL_ADDON_PORT", 3306))

        return mysql.connector.connect(
            host=host, user=user, password=password, database=database, port=port
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
                CREATE TABLE IF NOT EXISTS ventas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    comprobante VARCHAR(50) NOT NULL,
                    cliente VARCHAR(150) NOT NULL,
                    doc VARCHAR(50),
                    fecha DATE NOT NULL,
                    medio VARCHAR(100) NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    abonado DECIMAL(10,2) NOT NULL,
                    saldo DECIMAL(10,2) NOT NULL,
                    items TEXT NOT NULL,
                    amortizaciones TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATE NOT NULL,
                    recibo VARCHAR(50) NOT NULL,
                    categoria VARCHAR(150) NOT NULL,
                    mes VARCHAR(50),
                    detalle TEXT,
                    monto_total DECIMAL(10,2) NOT NULL,
                    amortizado DECIMAL(10,2) NOT NULL,
                    saldo DECIMAL(10,2) NOT NULL,
                    medio VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tesoreria (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATE NOT NULL,
                    tipo VARCHAR(100) NOT NULL,
                    concepto VARCHAR(200) NOT NULL,
                    monto DECIMAL(10,2) NOT NULL,
                    destino VARCHAR(150) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creditos_manuales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tipo_credito VARCHAR(50) NOT NULL,
                    comprobante VARCHAR(50) NOT NULL,
                    persona VARCHAR(150) NOT NULL,
                    fecha DATE NOT NULL,
                    items TEXT NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    medio VARCHAR(100) NOT NULL,
                    fecha_amort DATE,
                    abonado DECIMAL(10,2) NOT NULL,
                    amortizaciones TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imagenes_productos (
                    producto VARCHAR(150) PRIMARY KEY,
                    url_imagen LONGTEXT NOT NULL
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

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon_simbolo.png', mimetype='image/png')

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

# --- APIS GENERALES PARA VENTAS ---
@app.route('/api/ventas/listar', methods=['GET'])
def api_listar_ventas():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify([])
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        for r in res:
            r['items'] = json.loads(r['items']) if r.get('items') else []
            r['amortizaciones'] = json.loads(r['amortizaciones']) if r.get('amortizaciones') else []
        return jsonify(res)
    except Exception as e:
        print("Error en api_listar_ventas:", e)
        return jsonify([])

@app.route('/api/ventas/guardar', methods=['POST'])
def api_guardar_venta():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        
        v_id = data.get('id')
        items = json.dumps(data.get('items', []))
        amort = json.dumps(data.get('amortizaciones', []))
        
        if v_id:
            cursor.execute("""UPDATE ventas SET comprobante=%s, cliente=%s, doc=%s, fecha=%s, medio=%s, total=%s, abonado=%s, saldo=%s, items=%s, amortizaciones=%s WHERE id=%s""",
                           (data.get('comprobante'), data.get('cliente'), data.get('doc'), data.get('fecha'), data.get('medio'), float(data.get('total',0)), float(data.get('abonado',0)), float(data.get('saldo',0)), items, amort, v_id))
        else:
            cursor.execute("""INSERT INTO ventas (comprobante, cliente, doc, fecha, medio, total, abonado, saldo, items, amortizaciones) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                           (data.get('comprobante'), data.get('cliente'), data.get('doc'), data.get('fecha'), data.get('medio'), float(data.get('total',0)), float(data.get('abonado',0)), float(data.get('saldo',0)), items, amort))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/ventas/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_venta(id):
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM ventas WHERE id = %s", (id,))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- APIS PARA COMPRAS ---
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

# --- APIS PARA GASTOS ---
@app.route('/api/gastos/listar', methods=['GET'])
def api_listar_gastos():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify([])
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM gastos ORDER BY id DESC")
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        return jsonify(res)
    except: return jsonify([])

@app.route('/api/gastos/guardar', methods=['POST'])
def api_guardar_gasto():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        g_id = data.get('id')
        if g_id:
            cursor.execute("""UPDATE gastos SET fecha=%s, recibo=%s, categoria=%s, mes=%s, detalle=%s, monto_total=%s, amortizado=%s, saldo=%s, medio=%s WHERE id=%s""",
                           (data.get('fecha'), data.get('recibo'), data.get('categoria'), data.get('mes'), data.get('detalle'), float(data.get('montoTotal',0)), float(data.get('amortizado',0)), float(data.get('saldo',0)), data.get('medio'), g_id))
        else:
            cursor.execute("""INSERT INTO gastos (fecha, recibo, categoria, mes, detalle, monto_total, amortizado, saldo, medio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                           (data.get('fecha'), data.get('recibo'), data.get('categoria'), data.get('mes'), data.get('detalle'), float(data.get('montoTotal',0)), float(data.get('amortizado',0)), float(data.get('saldo',0)), data.get('medio')))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/gastos/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_gasto(id):
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM gastos WHERE id = %s", (id,))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- APIS PARA TESORERÍA ---
@app.route('/api/tesoreria/listar', methods=['GET'])
def api_listar_tesoreria():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify([])
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tesoreria ORDER BY id DESC")
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        return jsonify(res)
    except: return jsonify([])

@app.route('/api/tesoreria/guardar', methods=['POST'])
def api_guardar_tesoreria():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        t_id = data.get('id')
        if t_id:
            cursor.execute("""UPDATE tesoreria SET fecha=%s, tipo=%s, concepto=%s, monto=%s, destino=%s WHERE id=%s""",
                           (data.get('fecha'), data.get('tipo'), data.get('concepto'), float(data.get('monto',0)), data.get('destino'), t_id))
        else:
            cursor.execute("""INSERT INTO tesoreria (fecha, tipo, concepto, monto, destino) VALUES (%s, %s, %s, %s, %s)""",
                           (data.get('fecha'), data.get('tipo'), data.get('concepto'), float(data.get('monto',0)), data.get('destino')))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/tesoreria/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_tesoreria(id):
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM tesoreria WHERE id = %s", (id,))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- APIS PARA CRÉDITOS MANUALES ---
@app.route('/api/creditos_manuales/listar', methods=['GET'])
def api_listar_creditos_manuales():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify([])
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM creditos_manuales ORDER BY id DESC")
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        for r in res:
            r['items'] = json.loads(r['items']) if r.get('items') else []
            r['amortizaciones'] = json.loads(r['amortizaciones']) if r.get('amortizaciones') else []
        return jsonify(res)
    except: return jsonify([])

@app.route('/api/creditos_manuales/guardar', methods=['POST'])
def api_guardar_credito_manual():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cm_id = data.get('id')
        items = json.dumps(data.get('items', []))
        amort = json.dumps(data.get('amortizaciones', []))
        if cm_id:
            cursor.execute("""UPDATE creditos_manuales SET tipo_credito=%s, comprobante=%s, persona=%s, fecha=%s, items=%s, total=%s, medio=%s, fecha_amort=%s, abonado=%s, amortizaciones=%s WHERE id=%s""",
                           (data.get('tipo_credito'), data.get('comprobante'), data.get('persona'), data.get('fecha'), items, float(data.get('total',0)), data.get('medio'), data.get('fecha_amort'), float(data.get('abonado',0)), amort, cm_id))
        else:
            cursor.execute("""INSERT INTO creditos_manuales (tipo_credito, comprobante, persona, fecha, items, total, medio, fecha_amort, abonado, amortizaciones) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                           (data.get('tipo_credito'), data.get('comprobante'), data.get('persona'), data.get('fecha'), items, float(data.get('total',0)), data.get('medio'), data.get('fecha_amort'), float(data.get('abonado',0)), amort))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/creditos_manuales/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_credito_manual(id):
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM creditos_manuales WHERE id = %s", (id,))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- APIS PARA IMÁGENES DE PRODUCTOS ---
@app.route('/api/imagenes/listar', methods=['GET'])
def api_listar_imagenes():
    try:
        conexion = obtener_conexion()
        if not conexion: return jsonify({})
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT producto, url_imagen FROM imagenes_productos")
        res = cursor.fetchall()
        cursor.close(); conexion.close()
        return jsonify({r['producto']: r['url_imagen'] for r in res})
    except: return jsonify({})

@app.route('/api/imagenes/guardar', methods=['POST'])
def api_guardar_imagen():
    if 'rol' not in session: return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        prod = data.get('producto', '').strip().upper()
        url_img = data.get('url_imagen', '')
        conexion = obtener_conexion()
        if not conexion: return jsonify({'error': 'Error BD'}), 500
        cursor = conexion.cursor()
        cursor.execute("""INSERT INTO imagenes_productos (producto, url_imagen) VALUES (%s, %s) ON DUPLICATE KEY UPDATE url_imagen = VALUES(url_imagen)""", (prod, url_img))
        conexion.commit(); cursor.close(); conexion.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- NAVEGACIÓN COMPLETA DE MÓDULOS ---
@app.route('/ventas')
def ventas():
    if 'rol' not in session: return redirect(url_for('index'))
    return render_template_con_branding('ventas.html')

@app.route('/amortizaciones')
def amortizaciones():
    if 'rol' not in session: return redirect(url_for('index'))
    return render_template_con_branding('amortizaciones.html')

@app.route('/creditos')
def creditos():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('creditos.html')

@app.route('/tesoreria')
def tesoreria():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('tesoreria.html')

@app.route('/gastos')
def gastos():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('gastos.html')

@app.route('/compras')
def compras():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('compras.html')

@app.route('/stock')
def stock():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('stock.html')

@app.route('/configuracion')
def configuracion():
    if session.get('rol') != 'gerente': return redirect(url_for('ventas'))
    return render_template_con_branding('configuracion.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)