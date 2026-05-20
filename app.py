"""
Ferretería Super Jimmy — Backend de Vacantes + Productos + Admin
Flask REST API — Versión extendida (sin modificar lógica original)
"""

from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import os

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vacantes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── NUEVA CONFIG: sesiones y uploads ───────────────────────────────────────────
app.config['SECRET_KEY'] = 'superjimmy-admin-secret-2026'
app.config['UPLOAD_FOLDER'] = 'uploads_cv'
app.config['PRODUCT_IMG_FOLDER'] = 'uploads_productos'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
ALLOWED_CV = {'pdf', 'doc', 'docx'}
ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', 'pbkdf2:sha256:260000$superjimmy2026$f5fe419041ca547667a0566be33ff01523eff306be5b8e8b8a550243d1f3416a')  # Clave validada con hash

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PRODUCT_IMG_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ── HELPERS ────────────────────────────────────────────────────────────────────
def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated

# ── RUTAS ESTÁTICAS (ORIGINALES sin modificar) ────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/vacantes')
def vacantes_page():
    return send_from_directory('.', 'vacantes.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

@app.route('/admin/productos')
def admin_productos_page():
    return send_from_directory('.', 'admin.html')

@app.route('/productos')
def productos_page():
    return send_from_directory('.', 'productos.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# ── MODELOS ORIGINALES (sin modificar) ────────────────────────────────────────
class Vacante(db.Model):
    __tablename__ = 'vacantes'
    id          = db.Column(db.Integer, primary_key=True)
    titulo      = db.Column(db.String(100), nullable=False)
    tipo        = db.Column(db.String(50), default='Tiempo completo')
    modalidad   = db.Column(db.String(50), default='Presencial')
    descripcion = db.Column(db.Text)
    activa      = db.Column(db.Boolean, default=True)
    creada_en   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'titulo': self.titulo,
            'tipo': self.tipo, 'modalidad': self.modalidad,
            'descripcion': self.descripcion, 'activa': self.activa,
            'creada_en': self.creada_en.isoformat(),
        }


class Aplicacion(db.Model):
    __tablename__ = 'aplicaciones'
    id         = db.Column(db.Integer, primary_key=True)
    vacante_id = db.Column(db.Integer, db.ForeignKey('vacantes.id'), nullable=False)
    nombre     = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    telefono   = db.Column(db.String(20))
    mensaje    = db.Column(db.Text)
    cv_filename = db.Column(db.String(200))          # ← NUEVO campo para CV
    enviado_en = db.Column(db.DateTime, default=datetime.utcnow)
    vacante    = db.relationship('Vacante', backref='aplicaciones')

    def to_dict(self):
        return {
            'id': self.id, 'vacante_id': self.vacante_id,
            'vacante': self.vacante.titulo,
            'nombre': self.nombre, 'email': self.email,
            'telefono': self.telefono, 'mensaje': self.mensaje,
            'cv_filename': self.cv_filename,
            'enviado_en': self.enviado_en.isoformat(),
        }


# ── NUEVOS MODELOS ─────────────────────────────────────────────────────────────
class Producto(db.Model):
    __tablename__ = 'productos'
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(150), nullable=False)
    marca       = db.Column(db.String(100))
    precio      = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text)
    imagen      = db.Column(db.String(300))
    categoria   = db.Column(db.String(80), default='General')
    en_oferta   = db.Column(db.Boolean, default=False)
    precio_oferta = db.Column(db.Float)
    activo      = db.Column(db.Boolean, default=True)
    creado_en   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'nombre': self.nombre, 'marca': self.marca,
            'precio': self.precio, 'descripcion': self.descripcion,
            'imagen': self.imagen, 'categoria': self.categoria,
            'en_oferta': self.en_oferta, 'precio_oferta': self.precio_oferta,
            'activo': self.activo, 'creado_en': self.creado_en.isoformat(),
        }


# ── RUTAS ORIGINALES: VACANTES (sin modificar) ────────────────────────────────
@app.route('/api/vacantes', methods=['GET'])
def listar_vacantes():
    vacantes = Vacante.query.filter_by(activa=True).order_by(Vacante.creada_en.desc()).all()
    return jsonify([v.to_dict() for v in vacantes])

@app.route('/api/vacantes/<int:vid>', methods=['GET'])
def obtener_vacante(vid):
    return jsonify(Vacante.query.get_or_404(vid).to_dict())

@app.route('/api/vacantes', methods=['POST'])
def crear_vacante():
    data = request.get_json()
    if not data or not data.get('titulo'):
        return jsonify({'error': 'El campo titulo es requerido'}), 400
    v = Vacante(**{k: data[k] for k in ('titulo', 'tipo', 'modalidad', 'descripcion') if k in data})
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201

@app.route('/api/vacantes/<int:vid>', methods=['PUT'])
def actualizar_vacante(vid):
    vacante = Vacante.query.get_or_404(vid)
    data = request.get_json()
    for campo in ('titulo', 'tipo', 'modalidad', 'descripcion', 'activa'):
        if campo in data:
            setattr(vacante, campo, bool(data[campo]) if campo == 'activa' else data[campo])
    db.session.commit()
    return jsonify(vacante.to_dict())

@app.route('/api/vacantes/<int:vid>', methods=['DELETE'])
def eliminar_vacante(vid):
    vacante = Vacante.query.get_or_404(vid)
    vacante.activa = False
    db.session.commit()
    return jsonify({'mensaje': 'Vacante desactivada correctamente'})

@app.route('/api/vacantes/<int:vid>/aplicar', methods=['POST'])
def aplicar_vacante(vid):
    Vacante.query.get_or_404(vid)
    nombre = request.form.get('nombre', '').strip()
    email  = request.form.get('email', '').strip()
    if not nombre or not email:
        return jsonify({'error': 'nombre y email son requeridos'}), 400

    cv_filename = None
    if 'cv' in request.files:
        cv_file = request.files['cv']
        if cv_file and cv_file.filename and allowed_file(cv_file.filename, ALLOWED_CV):
            safe = secure_filename(cv_file.filename)
            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cv_filename = f"{ts}_{safe}"
            cv_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cv_filename))

    a = Aplicacion(
        vacante_id=vid,
        nombre=nombre, email=email,
        telefono=request.form.get('telefono'),
        mensaje=request.form.get('mensaje'),
        cv_filename=cv_filename,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({'mensaje': '¡Aplicación enviada correctamente!', 'id': a.id}), 201

@app.route('/api/aplicaciones', methods=['GET'])
def listar_aplicaciones():
    return jsonify([a.to_dict() for a in Aplicacion.query.order_by(Aplicacion.enviado_en.desc()).all()])

@app.route('/api/vacantes/<int:vid>/aplicaciones', methods=['GET'])
def aplicaciones_por_vacante(vid):
    Vacante.query.get_or_404(vid)
    return jsonify([a.to_dict() for a in Aplicacion.query.filter_by(vacante_id=vid).all()])


# ── NUEVAS RUTAS: AUTENTICACIÓN ADMIN ─────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if data and check_password_hash(ADMIN_PASSWORD_HASH, data.get('password', '')):
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Contraseña incorrecta'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'ok': True})

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    return jsonify({'admin': bool(session.get('admin'))})


# ── NUEVAS RUTAS: CRUD PRODUCTOS ───────────────────────────────────────────────
@app.route('/api/productos', methods=['GET'])
def listar_productos():
    cat = request.args.get('categoria')
    oferta = request.args.get('oferta')
    q = Producto.query.filter_by(activo=True)
    if cat:
        q = q.filter_by(categoria=cat)
    if oferta:
        q = q.filter_by(en_oferta=True)
    return jsonify([p.to_dict() for p in q.order_by(Producto.creado_en.desc()).all()])

@app.route('/api/productos/<int:pid>', methods=['GET'])
def obtener_producto(pid):
    return jsonify(Producto.query.get_or_404(pid).to_dict())

@app.route('/api/productos', methods=['POST'])
@admin_required
def crear_producto():
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'nombre es requerido'}), 400
    try:
        precio = float(request.form.get('precio', 0))
    except ValueError:
        return jsonify({'error': 'precio inválido'}), 400

    imagen_filename = None
    if 'imagen' in request.files:
        img = request.files['imagen']
        if img and img.filename and allowed_file(img.filename, ALLOWED_IMG):
            safe = secure_filename(img.filename)
            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            imagen_filename = f"{ts}_{safe}"
            img.save(os.path.join(app.config['PRODUCT_IMG_FOLDER'], imagen_filename))

    precio_oferta = None
    if request.form.get('precio_oferta'):
        try:
            precio_oferta = float(request.form['precio_oferta'])
        except ValueError:
            pass

    p = Producto(
        nombre=nombre,
        marca=request.form.get('marca'),
        precio=precio,
        descripcion=request.form.get('descripcion'),
        imagen=imagen_filename,
        categoria=request.form.get('categoria', 'General'),
        en_oferta=request.form.get('en_oferta') == 'true',
        precio_oferta=precio_oferta,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201

@app.route('/api/productos/<int:pid>', methods=['PUT'])
@admin_required
def actualizar_producto(pid):
    producto = Producto.query.get_or_404(pid)

    if 'imagen' in request.files:
        img = request.files['imagen']
        if img and img.filename and allowed_file(img.filename, ALLOWED_IMG):
            safe = secure_filename(img.filename)
            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            fn = f"{ts}_{safe}"
            img.save(os.path.join(app.config['PRODUCT_IMG_FOLDER'], fn))
            producto.imagen = fn

    for campo in ('nombre', 'marca', 'descripcion', 'categoria'):
        val = request.form.get(campo)
        if val is not None:
            setattr(producto, campo, val)

    if request.form.get('precio'):
        try:
            producto.precio = float(request.form['precio'])
        except ValueError:
            pass
    if request.form.get('precio_oferta'):
        try:
            producto.precio_oferta = float(request.form['precio_oferta'])
        except ValueError:
            pass
    if request.form.get('en_oferta') is not None:
        producto.en_oferta = request.form.get('en_oferta') == 'true'

    db.session.commit()
    return jsonify(producto.to_dict())

@app.route('/api/productos/<int:pid>', methods=['DELETE'])
@admin_required
def eliminar_producto(pid):
    producto = Producto.query.get_or_404(pid)
    producto.activo = False
    db.session.commit()
    return jsonify({'mensaje': 'Producto desactivado'})

# Sirve imágenes de productos
@app.route('/uploads_productos/<filename>')
def producto_imagen(filename):
    return send_from_directory(app.config['PRODUCT_IMG_FOLDER'], filename)

# Sirve CVs subidos (solo admin)
@app.route('/uploads_cv/<filename>')
@admin_required
def descargar_cv(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/categorias', methods=['GET'])
def listar_categorias():
    cats = db.session.query(Producto.categoria).filter_by(activo=True).distinct().all()
    return jsonify([c[0] for c in cats])


# ── DATOS DE EJEMPLO ───────────────────────────────────────────────────────────
def poblar_db():
    if Vacante.query.count() > 0:
        return
    vacantes_ejemplo = [
        Vacante(titulo='Vendedor/a de Mostrador', tipo='Tiempo completo', modalidad='Presencial',
                descripcion='Atención al cliente, manejo de caja y punto de venta.'),
        Vacante(titulo='Técnico Electricista', tipo='Tiempo completo', modalidad='Presencial',
                descripcion='Instalaciones eléctricas residenciales y comerciales.'),
        Vacante(titulo='Repartidor / Mensajero', tipo='Tiempo completo', modalidad='Presencial',
                descripcion='Entrega de pedidos en la zona metropolitana.'),
        Vacante(titulo='Asistente Administrativo', tipo='Medio tiempo', modalidad='Presencial',
                descripcion='Apoyo en facturación, inventario y atención telefónica.'),
    ]
    db.session.add_all(vacantes_ejemplo)

    if Producto.query.count() == 0:
        productos_ejemplo = [
            Producto(nombre='Pintura Interior Blanca 1 Galón', marca='Premium', precio=850,
                     descripcion='Alta cobertura para interiores.', categoria='Pinturas',
                     en_oferta=True, precio_oferta=595),
            Producto(nombre='Cable Eléctrico 12 AWG (Rollo 100m)', marca='TechWire', precio=1500,
                     descripcion='Cable certificado para instalaciones.', categoria='Electricidad',
                     en_oferta=True, precio_oferta=1125),
            Producto(nombre='Set de Plomería Completo', marca='HidroPlus', precio=2400,
                     descripcion='Tuberías PVC + accesorios.', categoria='Plomería',
                     en_oferta=True, precio_oferta=1920),
            Producto(nombre='Taladro Percutor 750W', marca='PowerTool', precio=3200,
                     descripcion='Ideal para concreto y madera.', categoria='Herramientas'),
            Producto(nombre='Cemento Portland 50kg', marca='CementoRD', precio=680,
                     descripcion='Para construcción general.', categoria='Construcción'),
            Producto(nombre='Lavamanos Cerámico Blanco', marca='CeraStyle', precio=1850,
                     descripcion='Moderno y resistente.', categoria='Cerámicas'),
            Producto(nombre='Silla de Madera Tapizada', marca='MuebleCraft', precio=2200,
                     descripcion='Confort y durabilidad.', categoria='Muebles'),
            Producto(nombre='Ventilador de Techo 52"', marca='AirMax', precio=4500,
                     descripcion='3 velocidades, silencioso.', categoria='Electrodomésticos'),
        ]
        db.session.add_all(productos_ejemplo)

    db.session.commit()
    print('✅  Datos de ejemplo creados.')


with app.app_context():
    db.create_all()
    poblar_db()

if __name__ == '__main__':
    app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
