from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import mysql.connector
import os
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "clave_secura_agro_jk"

def obtener_conexion():
    try:
        conexion = mysql.connector.connect(
            host="bbdxmfpaqjvnaoqv46uu-mysql.services.clever-cloud.com",
            user="ukq046fffz9ikj3j",
            password="SEP21cGpyJ2X5lW8FEIM",          
            database="bbdxmfpaqjvnaoqv46uu",
            port=3306
        )
        return conexion
    except Exception as e:
        print("Aviso de conexión a la base de datos en la nube:", e)
        return None

# Función para inyectar automáticamente el título, limpiar iconos y forzar la actualización en Chrome
def render_template_con_branding(template_name, **kwargs):
    html_content = render_template(template_name, **kwargs)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Cambiar el título de la pestaña a "Promotores del Agro"
    if soup.find('title'):
        soup.find('title').string = "Promotores del Agro"
    else:
        if soup.head:
            new_title = soup.new_tag('title')
            new_title.string = "Promotores del Agro"
            soup.head.append(new_title)
            
    # 2. Agregar etiqueta descriptiva para el navegador
    if soup.head:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.new_tag('meta', attrs={'name': 'description', 'content': 'Promotores del Agro - Sistema de Gestión y Ventas'})
            soup.head.append(meta_desc)

    # 3. Limpiar iconos anteriores y agregar favicon con control de versión (?v=2) para evitar caché
    for existing_icon in soup.find_all('link', rel=lambda x: x and 'icon' in x.lower()):
        existing_icon.decompose()
        
    if soup.head:
        new_favicon = soup.new_tag('link', rel='icon', type='image/png', href=url_for('static', filename='favicon_simbolo.png') + '?v=2')
        soup.head.append(new_favicon)
        
    return str(soup)

# Ruta automática para el archivo físico del símbolo en la pestaña del navegador
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon_simbolo.png', mimetype='image/png')

# Página principal limpia sin errores
@app.route('/')
def index():
    return render_template_con_branding('index.html', error=False)

@app.route('/login', methods=['POST'])
def login():
    perfil = request.form.get('perrol')
    
    if perfil == 'gerente':
        password = request.form.get('password', '')
        if password == 'Tubandera2714':  
            session['rol'] = 'gerente'
            return redirect(url_for('dashboard'))
        else:
            return render_template_con_branding('index.html', error=True)
    else:
        session['rol'] = 'empleado'
        return redirect(url_for('ventas'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if session.get('rol') != 'gerente':
        return redirect(url_for('ventas'))
    return render_template_con_branding('dashboard.html')

# API para obtener el resumen financiero del Dashboard directamente desde MySQL de forma limpia
@app.route('/api/dashboard/resumen')
def api_dashboard_resumen():
    if session.get('rol') != 'gerente':
        return jsonify({'error': 'No autorizado'}), 403
    
    try:
        conexion = obtener_conexion()
        if not conexion:
            return jsonify({'ventas_dia': 0.0, 'ventas_mes': 0.0, 'deudas_cobrar': 0.0})
            
        cursor = conexion.cursor(dictionary=True)
        
        # Si la tabla está vaciada, estas consultas devolverán 0.0 de forma automática y limpia
        cursor.execute("SELECT IFNULL(SUM(total), 0) as total_ventas_hoy FROM ventas WHERE DATE(fecha) = CURDATE()")
        res_hoy = cursor.fetchone()
        ventas_hoy = res_hoy['total_ventas_hoy'] if res_hoy and res_hoy['total_ventas_hoy'] else 0.0
        
        cursor.execute("SELECT IFNULL(SUM(total), 0) as total_ventas_mes FROM ventas WHERE MONTH(fecha) = MONTH(CURDATE()) AND YEAR(fecha) = YEAR(CURDATE())")
        res_mes = cursor.fetchone()
        ventas_mes = res_mes['total_ventas_mes'] if res_mes and res_mes['total_ventas_mes'] else 0.0
        
        cursor.execute("SELECT IFNULL(SUM(saldo_pendiente), 0) as total_deudas FROM ventas WHERE saldo_pendiente > 0")
        res_deudas = cursor.fetchone()
        deudas = res_deudas['total_deudas'] if res_deudas and res_deudas['total_deudas'] else 0.0
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'ventas_dia': float(ventas_hoy),
            'ventas_mes': float(ventas_mes),
            'deudas_cobrar': float(deudas)
        })
    except Exception as e:
        return jsonify({
            'ventas_dia': 0.0,
            'ventas_mes': 0.0,
            'deudas_cobrar': 0.0
        })

@app.route('/ventas')
def ventas():
    if 'rol' not in session:
        return redirect(url_for('index'))
    return render_template_con_branding('ventas.html')

@app.route('/amortizaciones')
def amortizaciones():
    if 'rol' not in session:
        return redirect(url_for('index'))
    return render_template_con_branding('amortizaciones.html')

@app.route('/gastos')
def gastos():
    if session.get('rol') != 'gerente':
        return redirect(url_for('ventas'))
    return render_template_con_branding('gastos.html')

@app.route('/compras')
def compras():
    if session.get('rol') != 'gerente':
        return redirect(url_for('ventas'))
    return render_template_con_branding('compras.html')

@app.route('/stock')
def stock():
    if session.get('rol') != 'gerente':
        return redirect(url_for('ventas'))
    return render_template_con_branding('stock.html')

@app.route('/configuracion')
def configuracion():
    if session.get('rol') != 'gerente':
        return redirect(url_for('ventas'))
    return render_template_con_branding('configuracion.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)