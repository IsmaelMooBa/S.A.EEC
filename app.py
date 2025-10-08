import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime

# Añade el directorio actual al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_aqui_2024'

# Configuración de sesión
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_aqui_2024'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600000  # 1 hora

# Importación después de configurar el path
try:
    from database import Database
    from models import Alumno, Grupo, Horario, Matricula, Usuario
    print("✅ Módulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    # Crear clases básicas para evitar errores
    class Alumno:
        @staticmethod
        def obtener_todos(): return []
        @staticmethod
        def obtener_por_id(id): return None
        @staticmethod
        def eliminar(id): return False
    
    class Grupo:
        @staticmethod
        def obtener_todos(): return []
        @staticmethod
        def obtener_por_id(id): return None
        @staticmethod
        def eliminar(id): return False
    
    class Horario:
        @staticmethod
        def obtener_por_grupo(grupo_id): return []
        @staticmethod
        def eliminar(horario_id): return False
    
    class Matricula:
        @staticmethod
        def obtener_todas(): return []
        @staticmethod
        def obtener_por_id(id): return None
        @staticmethod
        def obtener_por_alumno(alumno_id): return []
    
    class Usuario:
        @staticmethod
        def obtener_por_username(username): return None

# Variable para controlar la inicialización de la base de datos
db_initialized = False

def crear_usuario_admin():
    """Crear usuario admin automáticamente con bcrypt correcto"""
    try:
        # Verificar si ya existe el usuario admin
        admin = Usuario.obtener_por_username('admin')
        
        if admin:
            # Verificar si la contraseña es válida
            try:
                test_result = admin.verificar_password('admin123')
                if test_result:
                    print("✅ Usuario admin ya existe y contraseña es válida")
                    return
                else:
                    print("⚠️ Usuario admin existe pero contraseña no es válida, recreando...")
                    # Eliminar usuario existente
                    db = Database()
                    db.execute_query("DELETE FROM usuarios WHERE username = 'admin'")
            except Exception as e:
                print(f"⚠️ Error verificando usuario admin existente: {e}, recreando...")
                # Eliminar usuario existente
                db = Database()
                db.execute_query("DELETE FROM usuarios WHERE username = 'admin'")
        
        # Crear nuevo usuario admin
        print("🔧 Creando usuario admin por defecto...")
        
        import bcrypt
        password = 'admin123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        insert_query = """
        INSERT INTO usuarios (username, password_hash, rol, activo) 
        VALUES (%s, %s, %s, %s)
        """
        db = Database()
        resultado = db.execute_query(insert_query, ('admin', password_hash, 'admin', True))
        
        if resultado:
            print("✅ Usuario admin creado exitosamente")
            print("🔑 Credenciales: usuario: admin, contraseña: admin123")
        else:
            print("❌ Error creando usuario admin")
            
    except Exception as e:
        print(f"❌ Error creando usuario admin: {e}")

def initialize_database_once():
    """Inicializar base de datos solo una vez"""
    global db_initialized
    if not db_initialized:
        try:
            db = Database()
            db.initialize_database()
            db_initialized = True
            print("✅ Base de datos inicializada correctamente")
            
            # Crear usuario admin
            crear_usuario_admin()
            
        except Exception as e:
            print(f"❌ Error inicializando BD: {e}")

# ===== RUTAS DE AUTENTICACIÓN =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir al dashboard
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    # Inicializar BD antes del primer login si es necesario
    initialize_database_once()
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Por favor ingrese usuario y contraseña', 'error')
                return render_template('login.html')
            
            # Buscar usuario
            usuario = Usuario.obtener_por_username(username)
            
            if not usuario:
                flash('Usuario o contraseña incorrectos', 'error')
                return render_template('login.html')
            
            # Verificar contraseña
            if not usuario.verificar_password(password):
                flash('Usuario o contraseña incorrectos', 'error')
                return render_template('login.html')
            
            # Actualizar último login
            usuario.actualizar_ultimo_login()
            
            # Guardar en sesión
            session['usuario'] = {
                'id': usuario.id,
                'username': usuario.username,
                'rol': usuario.rol,
                'matricula_id': usuario.matricula_id
            }
            session.permanent = True
            
            flash(f'¡Bienvenido(a), {usuario.username}!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"❌ Error en login: {e}")
            flash('Error en el proceso de login', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Asegurar que la BD está inicializada
    initialize_database_once()
    
    usuario = session['usuario']
    
    try:
        # Calcular estadísticas para admin
        total_alumnos = len(Alumno.obtener_todos() or [])
        total_grupos = len(Grupo.obtener_todos() or [])
        total_matriculas = len(Matricula.obtener_todas() or [])
        
        # Dashboard diferente según el rol
        if usuario['rol'] == 'admin':
            return render_template('dashboard_admin.html', 
                                 usuario=usuario,
                                 total_alumnos=total_alumnos,
                                 total_grupos=total_grupos,
                                 total_matriculas=total_matriculas)
        else:
            # Obtener información completa del estudiante
            estudiante_info = obtener_info_estudiante(usuario['matricula_id'])
            return render_template('dashboard_estudiante.html', 
                                 usuario=usuario,
                                 estudiante=estudiante_info,
                                 Matricula=Matricula)
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        flash('Error cargando el dashboard', 'error')
        return render_template('dashboard_admin.html' if usuario['rol'] == 'admin' else 'dashboard_estudiante.html', 
                             usuario=usuario,
                             total_alumnos=0,
                             total_grupos=0,
                             total_matriculas=0)

def obtener_info_estudiante(matricula_id):
    """Obtener información completa del estudiante basado en la matrícula"""
    try:
        # Obtener datos de la matrícula
        matricula = Matricula.obtener_por_id(matricula_id)
        if not matricula:
            return None
        
        # Obtener datos del alumno
        alumno = Alumno.obtener_por_id(matricula['alumno_id'])
        if not alumno:
            return None
        
        # Obtener datos del grupo si existe
        grupo = None
        if matricula['grupo_id']:
            grupo = Grupo.obtener_por_id(matricula['grupo_id'])
        
        # Obtener horarios del grupo
        horarios = []
        if grupo:
            horarios = Horario.obtener_por_grupo(grupo['id']) or []
        
        # Obtener todas las matrículas del alumno
        matriculas_alumno = Matricula.obtener_por_alumno(alumno['id']) or []
        
        return {
            'alumno': alumno,
            'matricula_actual': matricula,
            'grupo': grupo,
            'horarios': horarios,
            'historial_matriculas': matriculas_alumno
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo info estudiante: {e}")
        return None

# Middleware para verificar autenticación
@app.before_request
def require_login():
    # Inicializar BD en el primer request
    initialize_database_once()
    
    # Rutas que no requieren login
    public_routes = ['login', 'logout', 'static', 'index']
    
    if request.endpoint and request.endpoint not in public_routes:
        if 'usuario' not in session:
            return redirect(url_for('login'))

# ===== RUTA INDEX ACTUALIZADA =====
@app.route('/')
def index():
    # Si el usuario está logueado, redirigir al dashboard
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    # Si no está logueado, mostrar página de inicio pública
    try:
        # Calcular los datos para el dashboard público
        total_alumnos = len(Alumno.obtener_todos() or [])
        total_grupos = len(Grupo.obtener_todos() or [])
        total_matriculas = len(Matricula.obtener_todas() or [])
        
        return render_template('index.html', 
                             total_alumnos=total_alumnos,
                             total_grupos=total_grupos,
                             total_matriculas=total_matriculas)
    except Exception as e:
        print(f"Error en index: {e}")
        return render_template('index.html', 
                             total_alumnos=0, 
                             total_grupos=0, 
                             total_matriculas=0)

# ===== RUTAS PARA ALUMNOS =====
@app.route('/alumnos')
def alumnos():
    try:
        # Obtener parámetros de búsqueda
        search = request.args.get('search', '').strip()
        letra_apellido = request.args.get('letra_apellido', '')
        orden = request.args.get('orden', 'apellido')
        
        # Obtener todos los alumnos
        alumnos = Alumno.obtener_todos() or []
        
        # Aplicar filtros
        if search:
            alumnos = [a for a in alumnos if 
                      search.lower() in f"{a['nombre']} {a['apellido']} {a['email']}".lower()]
        
        if letra_apellido:
            alumnos = [a for a in alumnos if 
                      a['apellido'] and a['apellido'].upper().startswith(letra_apellido.upper())]
        
        # Aplicar ordenamiento
        if orden == 'apellido':
            alumnos.sort(key=lambda x: (x['apellido'] or '', x['nombre'] or ''))
        elif orden == 'apellido_desc':
            alumnos.sort(key=lambda x: (x['apellido'] or '', x['nombre'] or ''), reverse=True)
        elif orden == 'nombre':
            alumnos.sort(key=lambda x: (x['nombre'] or '', x['apellido'] or ''))
        elif orden == 'fecha_nacimiento':
            alumnos.sort(key=lambda x: x['fecha_nacimiento'] or '')
        elif orden == 'id':
            alumnos.sort(key=lambda x: x['id'])
        
        return render_template('alumnos.html', alumnos=alumnos)
    except Exception as e:
        flash(f'Error cargando alumnos: {e}', 'error')
        return render_template('alumnos.html', alumnos=[])

@app.route('/agregar_alumno', methods=['GET', 'POST'])
def agregar_alumno():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            fecha_nacimiento = request.form['fecha_nacimiento']
            email = request.form['email']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            
            if not nombre or not apellido or not email:
                flash('Por favor complete todos los campos requeridos', 'error')
                return render_template('agregar_alumno.html')
            
            alumno = Alumno(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=fecha_nacimiento,
                email=email,
                telefono=telefono,
                direccion=direccion
            )
            
            resultado = alumno.guardar()
            if resultado:
                flash('Alumno agregado correctamente', 'success')
                return redirect(url_for('alumnos'))
            else:
                flash('Error al agregar alumno. Verifique que el email no exista.', 'error')
        except Exception as e:
            flash(f'Error al procesar el formulario: {e}', 'error')
    
    return render_template('agregar_alumno.html')

@app.route('/editar_alumno/<int:id>', methods=['GET', 'POST'])
def editar_alumno(id):
    try:
        alumno_data = Alumno.obtener_por_id(id)
        if not alumno_data:
            flash('Alumno no encontrado', 'error')
            return redirect(url_for('alumnos'))
        
        alumno = Alumno(**alumno_data)
        
        if request.method == 'POST':
            alumno.nombre = request.form['nombre']
            alumno.apellido = request.form['apellido']
            alumno.fecha_nacimiento = request.form['fecha_nacimiento']
            alumno.email = request.form['email']
            alumno.telefono = request.form['telefono']
            alumno.direccion = request.form['direccion']
            
            resultado = alumno.actualizar()
            if resultado:
                flash('Alumno actualizado correctamente', 'success')
                return redirect(url_for('alumnos'))
            else:
                flash('Error al actualizar alumno', 'error')
        
        return render_template('editar_alumno.html', alumno=alumno)
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('alumnos'))

@app.route('/eliminar_alumno/<int:id>')
def eliminar_alumno(id):
    try:
        resultado = Alumno.eliminar(id)
        if resultado:
            flash('Alumno eliminado correctamente', 'success')
        else:
            flash('Error al eliminar alumno', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
    return redirect(url_for('alumnos'))

# ===== RUTAS PARA GRUPOS =====
@app.route('/grupos')
def grupos():
    try:
        grupos = Grupo.obtener_todos() or []
        return render_template('grupos.html', grupos=grupos)
    except Exception as e:
        flash(f'Error cargando grupos: {e}', 'error')
        return render_template('grupos.html', grupos=[])

@app.route('/agregar_grupo', methods=['GET', 'POST'])
def agregar_grupo():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            grado = request.form['grado']
            turno = request.form['turno']
            capacidad = request.form['capacidad']
            
            grupo = Grupo(
                nombre=nombre,
                grado=grado,
                turno=turno,
                capacidad=capacidad
            )
            
            resultado = grupo.guardar()
            if resultado:
                flash('Grupo agregado correctamente', 'success')
                return redirect(url_for('grupos'))
            else:
                flash('Error al agregar grupo', 'error')
        except Exception as e:
            flash(f'Error al procesar el formulario: {e}', 'error')
    
    return render_template('agregar_grupo.html')

@app.route('/editar_grupo/<int:id>', methods=['GET', 'POST'])
def editar_grupo(id):
    try:
        grupo_data = Grupo.obtener_por_id(id)
        if not grupo_data:
            flash('Grupo no encontrado', 'error')
            return redirect(url_for('grupos'))
        
        grupo = Grupo(**grupo_data)
        
        if request.method == 'POST':
            grupo.nombre = request.form['nombre']
            grupo.grado = request.form['grado']
            grupo.turno = request.form['turno']
            grupo.capacidad = request.form['capacidad']
            
            resultado = grupo.actualizar()
            if resultado:
                flash('Grupo actualizado correctamente', 'success')
                return redirect(url_for('grupos'))
            else:
                flash('Error al actualizar grupo', 'error')
        
        return render_template('editar_grupo.html', grupo=grupo)
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('grupos'))

@app.route('/eliminar_grupo/<int:id>')
def eliminar_grupo(id):
    try:
        resultado = Grupo.eliminar(id)
        if resultado:
            flash('Grupo eliminado correctamente', 'success')
        else:
            flash('Error al eliminar grupo', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
    return redirect(url_for('grupos'))

# ===== RUTAS PARA GESTIÓN DE ALUMNOS EN GRUPOS =====

@app.route('/grupo/<int:id>/alumnos')
def grupo_alumnos(id):
    try:
        grupo = Grupo.obtener_por_id(id)
        if not grupo:
            flash('Grupo no encontrado', 'error')
            return redirect(url_for('grupos'))
        
        alumnos = Grupo.obtener_alumnos_por_grupo(id) or []
        
        # Obtener alumnos disponibles (no en este grupo)
        db = Database()
        query = """
            SELECT a.* FROM alumnos a
            WHERE a.id NOT IN (
                SELECT m.alumno_id FROM matriculas m 
                WHERE m.grupo_id = %s AND m.estado = 'Activa'
            )
            ORDER BY a.apellido, a.nombre
        """
        alumnos_disponibles = db.execute_query(query, (id,)) or []
        
        return render_template('grupo_alumnos.html', 
                             grupo=grupo, 
                             alumnos=alumnos,
                             alumnos_disponibles=alumnos_disponibles,
                             now=datetime.now())
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('grupos'))

@app.route('/grupo/<int:grupo_id>/agregar_alumno', methods=['POST'])
def agregar_alumno_grupo(grupo_id):
    try:
        alumno_id = request.form['alumno_id']
        anio_escolar = request.form['anio_escolar']
        
        # Verificar que el grupo existe
        grupo = Grupo.obtener_por_id(grupo_id)
        if not grupo:
            flash('Grupo no encontrado', 'error')
            return redirect(url_for('grupos'))
        
        # Verificar que el alumno existe
        alumno = Alumno.obtener_por_id(alumno_id)
        if not alumno:
            flash('Alumno no encontrado', 'error')
            return redirect(url_for('grupo_alumnos', id=grupo_id))
        
        # Verificar que el alumno no está ya en el grupo
        alumnos_grupo = Grupo.obtener_alumnos_por_grupo(grupo_id) or []
        alumno_ids = [a['id'] for a in alumnos_grupo]
        if int(alumno_id) in alumno_ids:
            flash('El alumno ya está en este grupo', 'error')
            return redirect(url_for('grupo_alumnos', id=grupo_id))
        
        # Verificar capacidad del grupo
        if len(alumnos_grupo) >= grupo['capacidad']:
            flash('El grupo ha alcanzado su capacidad máxima', 'error')
            return redirect(url_for('grupo_alumnos', id=grupo_id))
        
        # Crear matrícula
        matricula = Matricula(
            alumno_id=alumno_id,
            grupo_id=grupo_id,
            fecha_matricula=datetime.now().date(),
            anio_escolar=anio_escolar,
            estado='Activa'
        )
        
        resultado = matricula.guardar()
        if resultado:
            flash(f'Alumno {alumno["nombre"]} {alumno["apellido"]} agregado al grupo correctamente', 'success')
        else:
            flash('Error al agregar alumno al grupo', 'error')
            
    except Exception as e:
        flash(f"Error: {str(e)}", 'error')
    
    return redirect(url_for('grupo_alumnos', id=grupo_id))

@app.route('/grupo/<int:grupo_id>/remover_alumno', methods=['POST'])
def remover_alumno_grupo(grupo_id):
    try:
        alumno_id = request.form['alumno_id']
        
        # Buscar la matrícula activa del alumno en este grupo
        db = Database()
        query = """
            SELECT id FROM matriculas 
            WHERE alumno_id = %s AND grupo_id = %s AND estado = 'Activa'
        """
        result = db.fetch_one(query, (alumno_id, grupo_id))
        
        if result:
            # Cambiar estado de la matrícula a "Inactiva"
            update_query = "UPDATE matriculas SET estado = 'Inactiva' WHERE id = %s"
            db.execute_query(update_query, (result['id'],))
            
            # Obtener información del alumno para el mensaje
            alumno = Alumno.obtener_por_id(alumno_id)
            if alumno:
                flash(f'Alumno {alumno["nombre"]} {alumno["apellido"]} removido del grupo', 'success')
            else:
                flash('Alumno removido del grupo', 'success')
        else:
            flash('No se encontró la matrícula del alumno en este grupo', 'error')
            
    except Exception as e:
        flash(f"Error: {str(e)}", 'error')
    
    return redirect(url_for('grupo_alumnos', id=grupo_id))

# ===== RUTAS PARA HORARIOS =====
@app.route('/grupo/<int:grupo_id>/horarios')
def horarios(grupo_id):
    try:
        grupo = Grupo.obtener_por_id(grupo_id)
        horarios = Horario.obtener_por_grupo(grupo_id) or []
        return render_template('horarios.html', grupo=grupo, horarios=horarios)
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('grupos'))

@app.route('/agregar_horario/<int:grupo_id>', methods=['POST'])
def agregar_horario(grupo_id):
    try:
        dia_semana = request.form['dia_semana']
        hora_inicio = request.form['hora_inicio']
        hora_fin = request.form['hora_fin']
        materia = request.form['materia']
        profesor = request.form['profesor']
        
        horario = Horario(
            grupo_id=grupo_id,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            materia=materia,
            profesor=profesor
        )
        
        resultado = horario.guardar()
        if resultado:
            flash('Horario agregado correctamente', 'success')
        else:
            flash('Error al agregar horario', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
    return redirect(url_for('horarios', grupo_id=grupo_id))

@app.route('/eliminar_horario/<int:horario_id>/<int:grupo_id>')
def eliminar_horario(horario_id, grupo_id):
    try:
        resultado = Horario.eliminar(horario_id)
        if resultado:
            flash('Horario eliminado correctamente', 'success')
        else:
            flash('Error al eliminar horario', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
    return redirect(url_for('horarios', grupo_id=grupo_id))

# ===== RUTAS PARA MATRÍCULAS =====
@app.route('/matriculas')
def matriculas():
    try:
        matriculas = Matricula.obtener_todas() or []
        alumnos = Alumno.obtener_todos() or []
        grupos = Grupo.obtener_todos() or []
        return render_template('matriculas.html', 
                             matriculas=matriculas, 
                             alumnos=alumnos, 
                             grupos=grupos,
                             now=datetime.now())
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return render_template('matriculas.html', matriculas=[], alumnos=[], grupos=[], now=datetime.now())

@app.route('/agregar_matricula', methods=['POST'])
def agregar_matricula():
    try:
        print("🎯 INICIANDO AGREGAR_MATRICULA - DEBUG DETALLADO")
        
        # Obtener datos del formulario
        alumno_id = request.form.get('alumno_id')
        grupo_id = request.form.get('grupo_id') or None
        anio_escolar = request.form.get('anio_escolar')
        estado = request.form.get('estado')
        
        print(f"🎯 DATOS DEL FORMULARIO:")
        print(f"   alumno_id: {alumno_id} (tipo: {type(alumno_id)})")
        print(f"   grupo_id: {grupo_id} (tipo: {type(grupo_id)})")
        print(f"   anio_escolar: {anio_escolar} (tipo: {type(anio_escolar)})")
        print(f"   estado: {estado} (tipo: {type(estado)})")
        
        # Validar campos requeridos
        if not alumno_id:
            print("❌ ERROR: alumno_id está vacío")
            flash('Debe seleccionar un alumno', 'error')
            return redirect(url_for('matriculas'))
        
        if not anio_escolar:
            print("❌ ERROR: anio_escolar está vacío")
            flash('El año escolar es requerido', 'error')
            return redirect(url_for('matriculas'))
            
        if not estado:
            print("❌ ERROR: estado está vacío")
            flash('El estado es requerido', 'error')
            return redirect(url_for('matriculas'))

        # Convertir a enteros
        try:
            alumno_id = int(alumno_id)
            if grupo_id:
                grupo_id = int(grupo_id)
            anio_escolar = int(anio_escolar)
            print(f"🎯 DATOS CONVERTIDOS:")
            print(f"   alumno_id: {alumno_id} (tipo: {type(alumno_id)})")
            print(f"   grupo_id: {grupo_id} (tipo: {type(grupo_id)})")
            print(f"   anio_escolar: {anio_escolar} (tipo: {type(anio_escolar)})")
        except ValueError as e:
            print(f"❌ ERROR en conversión de tipos: {e}")
            flash('Error en el formato de los datos numéricos', 'error')
            return redirect(url_for('matriculas'))
        
        # Verificar que el alumno existe
        alumno = Alumno.obtener_por_id(alumno_id)
        if not alumno:
            print(f"❌ ERROR: No existe alumno con ID {alumno_id}")
            flash('El alumno seleccionado no existe', 'error')
            return redirect(url_for('matriculas'))
        
        print(f"🎯 ALUMNO ENCONTRADO: {alumno['nombre']} {alumno['apellido']}")

        # Crear objeto matrícula
        matricula = Matricula(
            alumno_id=alumno_id,
            grupo_id=grupo_id,
            fecha_matricula=datetime.now().date(),
            anio_escolar=anio_escolar,
            estado=estado
        )
        
        print("🎯 OBJETO MATRICULA CREADO, LLAMANDO A guardar()...")
        
        # Guardar matrícula
        resultado = matricula.guardar()
        
        print(f"🎯 RESULTADO DE guardar(): {resultado}")
        
        if resultado:
            print("✅ MATRÍCULA GUARDADA EXITOSAMENTE")
            flash('Matrícula agregada correctamente', 'success')
        else:
            print("❌ matricula.guardar() retornó False")
            flash('Error al agregar matrícula - no se pudo guardar en la base de datos', 'error')
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en agregar_matricula: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al procesar la solicitud: {str(e)}', 'error')
    
    return redirect(url_for('matriculas'))

@app.route('/cambiar_estado_matricula', methods=['POST'])
def cambiar_estado_matricula():
    try:
        data = request.get_json()
        matricula_id = data['matricula_id']
        estado = data['estado']
        
        resultado = Matricula.actualizar_estado(matricula_id, estado)
        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== NUEVAS RUTAS PARA EDITAR Y ELIMINAR MATRÍCULAS =====

@app.route('/editar_matricula', methods=['POST'])
def editar_matricula():
    try:
        print("🎯 INICIANDO EDICIÓN DE MATRÍCULA")
        
        matricula_id = request.form.get('matricula_id')
        grupo_id = request.form.get('grupo_id') or None
        anio_escolar = request.form.get('anio_escolar')
        estado = request.form.get('estado')
        
        print(f"🎯 Datos edición: matricula_id={matricula_id}, grupo_id={grupo_id}, anio_escolar={anio_escolar}, estado={estado}")
        
        # Validar campos
        if not matricula_id or not anio_escolar or not estado:
            flash('Faltan campos requeridos', 'error')
            return redirect(url_for('matriculas'))
        
        # Convertir a enteros
        try:
            matricula_id = int(matricula_id)
            if grupo_id:
                grupo_id = int(grupo_id)
            anio_escolar = int(anio_escolar)
        except ValueError as e:
            flash('Error en el formato de los datos', 'error')
            return redirect(url_for('matriculas'))
        
        # Actualizar la matrícula
        db = Database()
        query = """
            UPDATE matriculas 
            SET grupo_id = %s, anio_escolar = %s, estado = %s 
            WHERE id = %s
        """
        params = (grupo_id, anio_escolar, estado, matricula_id)
        
        resultado = db.execute_query(query, params)
        
        if resultado:
            flash('Matrícula actualizada correctamente', 'success')
        else:
            flash('Error al actualizar matrícula', 'error')
            
    except Exception as e:
        print(f"❌ Error editando matrícula: {e}")
        flash(f'Error al procesar la solicitud: {str(e)}', 'error')
    
    return redirect(url_for('matriculas'))

@app.route('/eliminar_matricula', methods=['POST'])
def eliminar_matricula():
    try:
        data = request.get_json()
        matricula_id = data['matricula_id']
        
        print(f"🎯 Eliminando matrícula ID: {matricula_id}")
        
        # Eliminar la matrícula
        db = Database()
        query = "DELETE FROM matriculas WHERE id = %s"
        resultado = db.execute_query(query, (matricula_id,))
        
        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo eliminar la matrícula'})
            
    except Exception as e:
        print(f"❌ Error eliminando matrícula: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ===== RUTAS PARA CORREGIR USUARIOS =====

@app.route('/reset_admin')
def reset_admin():
    """Ruta temporal para recrear el usuario admin correctamente"""
    try:
        db = Database()
        
        # Eliminar usuario admin existente
        db.execute_query("DELETE FROM usuarios WHERE username = 'admin'")
        print("✅ Usuario admin eliminado")
        
        # Crear nuevo usuario admin con bcrypt correcto
        import bcrypt
        password = 'admin123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        insert_query = """
        INSERT INTO usuarios (username, password_hash, rol, activo) 
        VALUES (%s, %s, %s, %s)
        """
        resultado = db.execute_query(insert_query, ('admin', password_hash, 'admin', True))
        
        if resultado:
            return """
            <h1>✅ Usuario admin recreado correctamente</h1>
            <p><strong>Credenciales:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> admin</li>
                <li><strong>Contraseña:</strong> admin123</li>
            </ul>
            <a href='/login'>Ir al login</a>
            """
        else:
            return "❌ Error creando usuario admin"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/generar_usuarios_matriculas')
def generar_usuarios_matriculas():
    """Generar usuarios para todas las matrículas existentes que no tengan usuario"""
    try:
        from models import Usuario
        
        # Obtener todas las matrículas
        matriculas = Matricula.obtener_todas() or []
        usuarios_creados = 0
        errores = 0
        
        for matricula in matriculas:
            try:
                # Verificar si ya existe usuario para esta matrícula
                usuario_existente = Usuario.obtener_por_matricula(matricula['id'])
                
                if not usuario_existente:
                    # Generar código de matrícula si no existe
                    if not matricula['codigo_matricula']:
                        # Buscar datos del alumno
                        alumno = Alumno.obtener_por_id(matricula['alumno_id'])
                        if alumno:
                            nombre_completo = alumno['nombre'].strip()
                            apellido_completo = alumno['apellido'].strip()
                            
                            partes_nombre = nombre_completo.split()
                            partes_apellido = apellido_completo.split()

                            iniciales = ""
                            if len(partes_nombre) > 0:
                                iniciales += partes_nombre[0][0].upper()
                            if len(partes_nombre) > 1:
                                iniciales += partes_nombre[1][0].upper()
                            if len(partes_apellido) > 0:
                                iniciales += partes_apellido[0][0].upper()
                            if len(partes_apellido) > 1:
                                iniciales += partes_apellido[1][0].upper()

                            if len(iniciales) < 2:
                                iniciales = "MAT"

                            codigo = f"{iniciales}-{matricula['anio_escolar']}-{matricula['alumno_id']}-{matricula['id']}"
                            
                            # Actualizar matrícula con código
                            db = Database()
                            db.execute_query(
                                "UPDATE matriculas SET codigo_matricula = %s WHERE id = %s",
                                (codigo, matricula['id'])
                            )
                            matricula['codigo_matricula'] = codigo
                    
                    # Crear usuario
                    if matricula['codigo_matricula']:
                        resultado = Usuario.crear_usuario(
                            username=matricula['codigo_matricula'],
                            password=matricula['codigo_matricula'],
                            rol='estudiante',
                            matricula_id=matricula['id']
                        )
                        
                        if resultado:
                            usuarios_creados += 1
                            print(f"✅ Usuario creado para matrícula {matricula['id']}: {matricula['codigo_matricula']}")
                        else:
                            errores += 1
                            print(f"❌ Error creando usuario para matrícula {matricula['id']}")
                
            except Exception as e:
                errores += 1
                print(f"❌ Error procesando matrícula {matricula['id']}: {e}")
        
        return f"""
        <h1>✅ Generación de usuarios completada</h1>
        <p><strong>Usuarios creados:</strong> {usuarios_creados}</p>
        <p><strong>Errores:</strong> {errores}</p>
        <p><strong>Total matrículas procesadas:</strong> {len(matriculas)}</p>
        <a href='/login'>Ir al login</a>
        """
        
    except Exception as e:
        return f"❌ Error general: {str(e)}"

@app.route('/fix_usuario_imb')
def fix_usuario_imb():
    """Corregir el usuario IMB-2025-1-36 con hash bcrypt válido"""
    try:
        from models import Usuario
        
        # Primero eliminar el usuario existente si existe
        db = Database()
        db.execute_query("DELETE FROM usuarios WHERE username = 'IMB-2025-1-36'")
        print("✅ Usuario IMB-2025-1-36 eliminado")
        
        # Buscar la matrícula
        matricula = db.fetch_one(
            "SELECT * FROM matriculas WHERE codigo_matricula = %s", 
            ('IMB-2025-1-36',)
        )
        
        if not matricula:
            return "❌ No se encontró la matrícula IMB-2025-1-36"
        
        # Crear usuario con bcrypt real
        resultado = Usuario.crear_usuario(
            username='IMB-2025-1-36',
            password='IMB-2025-1-36',  # Esto generará un hash bcrypt válido
            rol='estudiante',
            matricula_id=matricula['id']
        )
        
        if resultado:
            return f"""
            <h1>✅ Usuario IMB-2025-1-36 creado correctamente</h1>
            <p><strong>Usuario:</strong> IMB-2025-1-36</p>
            <p><strong>Contraseña:</strong> IMB-2025-1-36</p>
            <p><strong>Matrícula ID:</strong> {matricula['id']}</p>
            <p><strong>Alumno ID:</strong> {matricula['alumno_id']}</p>
            <a href='/login'>Ir al login</a>
            """
        else:
            return "❌ Error creando usuario IMB-2025-1-36"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/fix_usuario/<username>')
def fix_usuario(username):
    """Corregir cualquier usuario con hash bcrypt válido"""
    try:
        from models import Usuario
        
        # Primero eliminar el usuario existente si existe
        db = Database()
        db.execute_query("DELETE FROM usuarios WHERE username = %s", (username,))
        print(f"✅ Usuario {username} eliminado")
        
        # Buscar si es una matrícula
        matricula = db.fetch_one(
            "SELECT * FROM matriculas WHERE codigo_matricula = %s", 
            (username,)
        )
        
        if matricula:
            # Es un estudiante
            resultado = Usuario.crear_usuario(
                username=username,
                password=username,
                rol='estudiante',
                matricula_id=matricula['id']
            )
        else:
            # Es otro tipo de usuario
            resultado = Usuario.crear_usuario(
                username=username,
                password=username,
                rol='estudiante'
            )
        
        if resultado:
            return f"""
            <h1>✅ Usuario {username} creado correctamente</h1>
            <p><strong>Usuario:</strong> {username}</p>
            <p><strong>Contraseña:</strong> {username}</p>
            <p><strong>Rol:</strong> estudiante</p>
            <a href='/login'>Ir al login</a>
            """
        else:
            return f"❌ Error creando usuario {username}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/crear_usuario_especifico/<codigo_matricula>')
def crear_usuario_especifico(codigo_matricula):
    """Crear usuario para una matrícula específica"""
    try:
        from models import Usuario
        
        # Buscar la matrícula
        db = Database()
        matricula = db.fetch_one(
            "SELECT * FROM matriculas WHERE codigo_matricula = %s", 
            (codigo_matricula,)
        )
        
        if not matricula:
            return f"❌ No se encontró la matrícula con código: {codigo_matricula}"
        
        # Verificar si ya existe usuario
        usuario_existente = Usuario.obtener_por_matricula(matricula['id'])
        if usuario_existente:
            return f"✅ Ya existe usuario para esta matrícula: {usuario_existente.username}"
        
        # Crear usuario
        resultado = Usuario.crear_usuario(
            username=codigo_matricula,
            password=codigo_matricula,
            rol='estudiante',
            matricula_id=matricula['id']
        )
        
        if resultado:
            return f"""
            <h1>✅ Usuario creado exitosamente</h1>
            <p><strong>Matrícula:</strong> {codigo_matricula}</p>
            <p><strong>Usuario:</strong> {codigo_matricula}</p>
            <p><strong>Contraseña:</strong> {codigo_matricula}</p>
            <p><strong>Rol:</strong> estudiante</p>
            <a href='/login'>Ir al login</a>
            """
        else:
            return f"❌ Error creando usuario para: {codigo_matricula}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/verificar_usuarios')
def verificar_usuarios():
    """Verificar todos los usuarios y sus hashes"""
    try:
        db = Database()
        usuarios = db.fetch_all("SELECT username, password_hash FROM usuarios")
        
        html = """
        <h1>🔍 Verificación de Usuarios</h1>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Username</th>
                <th>Hash</th>
                <th>Estado</th>
            </tr>
        """
        
        for usuario in usuarios:
            hash_valido = usuario['password_hash'].startswith(('$2a$', '$2b$', '$2y$'))
            estado = "✅ Válido" if hash_valido else "❌ Inválido"
            color = "green" if hash_valido else "red"
            
            html += f"""
            <tr>
                <td>{usuario['username']}</td>
                <td>{usuario['password_hash'][:30]}...</td>
                <td style="color: {color}; font-weight: bold;">{estado}</td>
            </tr>
            """
        
        html += """
        </table>
        <br>
        <a href='/fix_usuario_imb'>Corregir usuario IMB-2025-1-36</a> | 
        <a href='/generar_usuarios_matriculas'>Generar usuarios para todas las matrículas</a> | 
        <a href='/login'>Ir al login</a>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ===== PANEL DE ADMINISTRACIÓN DE USUARIOS =====

@app.route('/admin/usuarios')
def admin_usuarios():
    """Panel de administración de usuarios"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Obtener todas las matrículas
        matriculas = Matricula.obtener_todas() or []
        
        # Obtener todos los usuarios
        db = Database()
        usuarios = db.fetch_all("""
            SELECT u.*, m.codigo_matricula, a.nombre, a.apellido 
            FROM usuarios u 
            LEFT JOIN matriculas m ON u.matricula_id = m.id 
            LEFT JOIN alumnos a ON m.alumno_id = a.id
            ORDER BY u.username
        """) or []
        
        # Separar matrículas con y sin usuario
        matriculas_con_usuario = []
        matriculas_sin_usuario = []
        
        for matricula in matriculas:
            tiene_usuario = any(usuario.get('matricula_id') == matricula['id'] for usuario in usuarios)
            if tiene_usuario:
                matriculas_con_usuario.append(matricula)
            else:
                matriculas_sin_usuario.append(matricula)
        
        return render_template('admin_usuarios.html',
                             matriculas_con_usuario=matriculas_con_usuario,
                             matriculas_sin_usuario=matriculas_sin_usuario,
                             usuarios=usuarios)
        
    except Exception as e:
        flash(f'Error cargando panel de usuarios: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/crear_usuario/<int:matricula_id>')
def admin_crear_usuario(matricula_id):
    """Crear usuario para una matrícula específica desde el panel admin"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        # Obtener la matrícula
        matricula = Matricula.obtener_por_id(matricula_id)
        if not matricula:
            return jsonify({'success': False, 'error': 'Matrícula no encontrada'})
        
        # Generar código si no existe
        if not matricula['codigo_matricula']:
            alumno = Alumno.obtener_por_id(matricula['alumno_id'])
            if alumno:
                nombre_completo = alumno['nombre'].strip()
                apellido_completo = alumno['apellido'].strip()
                
                partes_nombre = nombre_completo.split()
                partes_apellido = apellido_completo.split()

                iniciales = ""
                if len(partes_nombre) > 0:
                    iniciales += partes_nombre[0][0].upper()
                if len(partes_nombre) > 1:
                    iniciales += partes_nombre[1][0].upper()
                if len(partes_apellido) > 0:
                    iniciales += partes_apellido[0][0].upper()
                if len(partes_apellido) > 1:
                    iniciales += partes_apellido[1][0].upper()

                if len(iniciales) < 2:
                    iniciales = "MAT"

                codigo = f"{iniciales}-{matricula['anio_escolar']}-{matricula['alumno_id']}-{matricula['id']}"
                
                # Actualizar matrícula con código
                db = Database()
                db.execute_query(
                    "UPDATE matriculas SET codigo_matricula = %s WHERE id = %s",
                    (codigo, matricula['id'])
                )
                matricula['codigo_matricula'] = codigo
        
        # Verificar si ya existe usuario
        usuario_existente = Usuario.obtener_por_matricula(matricula_id)
        if usuario_existente:
            return jsonify({
                'success': False, 
                'error': f'Ya existe usuario: {usuario_existente.username}'
            })
        
        # Crear usuario
        resultado = Usuario.crear_usuario(
            username=matricula['codigo_matricula'],
            password=matricula['codigo_matricula'],
            rol='estudiante',
            matricula_id=matricula_id
        )
        
        if resultado:
            return jsonify({
                'success': True,
                'message': f'Usuario creado: {matricula["codigo_matricula"]}',
                'username': matricula['codigo_matricula']
            })
        else:
            return jsonify({'success': False, 'error': 'Error creando usuario'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/eliminar_usuario/<int:usuario_id>')
def admin_eliminar_usuario(usuario_id):
    """Eliminar usuario desde el panel admin"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        db = Database()
        # Obtener info del usuario antes de eliminar
        usuario_info = db.fetch_one("SELECT username FROM usuarios WHERE id = %s", (usuario_id,))
        
        if not usuario_info:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'})
        
        # No permitir eliminar al admin
        if usuario_info['username'] == 'admin':
            return jsonify({'success': False, 'error': 'No se puede eliminar el usuario admin'})
        
        # Eliminar usuario
        resultado = db.execute_query("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        
        if resultado:
            return jsonify({
                'success': True,
                'message': f'Usuario {usuario_info["username"]} eliminado'
            })
        else:
            return jsonify({'success': False, 'error': 'Error eliminando usuario'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generar_todos_usuarios')
def admin_generar_todos_usuarios():
    """Generar usuarios para todas las matrículas sin usuario"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        matriculas = Matricula.obtener_todas() or []
        usuarios_creados = 0
        errores = 0
        
        for matricula in matriculas:
            try:
                # Verificar si ya existe usuario
                usuario_existente = Usuario.obtener_por_matricula(matricula['id'])
                if not usuario_existente:
                    # Generar código si no existe
                    if not matricula['codigo_matricula']:
                        alumno = Alumno.obtener_por_id(matricula['alumno_id'])
                        if alumno:
                            nombre_completo = alumno['nombre'].strip()
                            apellido_completo = alumno['apellido'].strip()
                            
                            partes_nombre = nombre_completo.split()
                            partes_apellido = apellido_completo.split()

                            iniciales = ""
                            if len(partes_nombre) > 0:
                                iniciales += partes_nombre[0][0].upper()
                            if len(partes_nombre) > 1:
                                iniciales += partes_nombre[1][0].upper()
                            if len(partes_apellido) > 0:
                                iniciales += partes_apellido[0][0].upper()
                            if len(partes_apellido) > 1:
                                iniciales += partes_apellido[1][0].upper()

                            if len(iniciales) < 2:
                                iniciales = "MAT"

                            codigo = f"{iniciales}-{matricula['anio_escolar']}-{matricula['alumno_id']}-{matricula['id']}"
                            
                            db = Database()
                            db.execute_query(
                                "UPDATE matriculas SET codigo_matricula = %s WHERE id = %s",
                                (codigo, matricula['id'])
                            )
                            matricula['codigo_matricula'] = codigo
                    
                    # Crear usuario
                    if matricula['codigo_matricula']:
                        resultado = Usuario.crear_usuario(
                            username=matricula['codigo_matricula'],
                            password=matricula['codigo_matricula'],
                            rol='estudiante',
                            matricula_id=matricula['id']
                        )
                        
                        if resultado:
                            usuarios_creados += 1
                        else:
                            errores += 1
                            
            except Exception as e:
                errores += 1
                print(f"❌ Error procesando matrícula {matricula['id']}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Usuarios creados: {usuarios_creados}, Errores: {errores}',
            'usuarios_creados': usuarios_creados,
            'errores': errores
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    app.run(debug=True, port=5000)