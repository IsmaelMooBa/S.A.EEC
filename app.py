import os
import sys
import base64
import json
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime
from io import BytesIO

# Añade el directorio actual al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_aqui_2024'

# Configuración de sesión
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_aqui_2024'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600000  # 1 hora

# AGREGAR ESTAS CONFIGURACIONES NUEVAS:
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STATIC_FOLDER'] = 'static'

# Crear directorios si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['STATIC_FOLDER'], 'fotos'), exist_ok=True)

# Importación después de configurar el path
try:
    from database import Database
    from models import Alumno, Grupo, Horario, Matricula, Usuario, Maestro, MatriculaMaestro  # ← Agrega Maestro aquí
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

    class MatriculaMaestro:
        @staticmethod
        def obtener_por_maestro(maestro_id): return []
        @staticmethod
        def eliminar(id): return False
        @staticmethod
        def actualizar_estado(matricula_id, estado): return False

    class Usuario:
        @staticmethod
        def obtener_por_username(username): return None
    
    # Agrega también la clase Maestro básica para evitar errores
    class Maestro:
        @staticmethod
        def obtener_todos(): return []
        @staticmethod
        def obtener_por_id(id): return None
        @staticmethod
        def eliminar(id): return False
        @staticmethod
        def buscar(texto): return []
        

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
            
def procesar_csv(archivo_csv):
    """Procesa el archivo CSV y devuelve los datos en formato JSON"""
    try:
        # Leer el archivo CSV
        df = pd.read_csv(archivo_csv)
        
        print("Columnas encontradas:", df.columns.tolist())
        print("Primeras filas:", df.head().to_dict())
        
        # Verificar columnas requeridas - con manejo de encoding
        columnas_requeridas = ['CÓDIGO', 'ALUMNO', 'AÑO ESCOLAR']
        
        # Verificar si las columnas existen (con tildes)
        columnas_encontradas = []
        for columna in columnas_requeridas:
            if columna in df.columns:
                columnas_encontradas.append(columna)
            else:
                # Intentar encontrar columnas sin tildes o con encoding diferente
                columnas_sin_tildes = {
                    'CÓDIGO': ['CODIGO', 'CÓDIGO'],
                    'ALUMNO': ['ALUMNO', 'NOMBRE', 'ESTUDIANTE'],
                    'AÑO ESCOLAR': ['AÑO ESCOLAR', 'AÑO', 'ANO ESCOLAR', 'ESCOLAR']
                }
                
                for variante in columnas_sin_tildes.get(columna, []):
                    if variante in df.columns:
                        # Renombrar la columna al nombre esperado
                        df = df.rename(columns={variante: columna})
                        columnas_encontradas.append(columna)
                        break
                else:
                    return None, f"Falta la columna requerida: {columna}"
        
        # Filtrar solo registros con estado "Activa"
        if 'ESTADO' in df.columns:
            df = df[df['ESTADO'] == 'Activa']
            print(f"Registros después de filtrar activos: {len(df)}")
        
        # Crear estructura de datos para credenciales
        datos_credenciales = []
        for _, fila in df.iterrows():
            credencial = {
                'nombre': fila['ALUMNO'],
                'rol': 'ESTUDIANTE',  # Todos serán estudiantes
                'matricula': fila['CÓDIGO'],
                'ano_escolar': str(fila['AÑO ESCOLAR']),  # Convertir a string
                'foto': f"{fila['CÓDIGO']}.jpg",  # Asumiendo que las fotos se llaman como el código
                'telefono': '',
                'email': ''
            }
            datos_credenciales.append(credencial)
        
        print(f"Datos procesados: {len(datos_credenciales)} credenciales")
        return datos_credenciales, None
        
    except Exception as e:
        import traceback
        print(f"Error completo: {traceback.format_exc()}")
        return None, f"Error al procesar el CSV: {str(e)}"
# ===== RUTAS PARA MATRÍCULAS DE MAESTROS =====

@app.route('/matriculas_maestros')
def matriculas_maestros():
    """Gestión de matrículas de maestros"""
    try:
        # Obtener parámetros de búsqueda
        search = request.args.get('search', '').strip()
        estado = request.args.get('estado', '')
        anio_escolar = request.args.get('anio_escolar', '')
        
        # Obtener todas las matrículas de maestros
        if search:
            # Búsqueda por nombre, apellido, código o especialidad
            db = Database()
            query = """
                SELECT mm.*, 
                       m.nombre AS maestro_nombre, 
                       m.apellido AS maestro_apellido,
                       m.email AS maestro_email,
                       m.especialidad AS maestro_especialidad
                FROM matriculas_maestros mm
                JOIN maestros m ON mm.maestro_id = m.id
                WHERE (m.nombre LIKE %s OR m.apellido LIKE %s OR 
                       mm.codigo_matricula LIKE %s OR m.especialidad LIKE %s)
            """
            search_term = f"%{search}%"
            matriculas = db.fetch_all(query, (search_term, search_term, search_term, search_term)) or []
        else:
            matriculas = MatriculaMaestro.obtener_todas() or []
        
        # Aplicar filtros adicionales
        if estado:
            matriculas = [m for m in matriculas if m['estado'] == estado]
        
        if anio_escolar:
            matriculas = [m for m in matriculas if str(m['anio_escolar']) == anio_escolar]
        
        # Obtener todos los maestros para el modal
        maestros = Maestro.obtener_todos() or []
        
        return render_template('matriculas_maestros.html', 
                             matriculas=matriculas,
                             maestros=maestros,
                             now=datetime.now())
        
    except Exception as e:
        flash(f'Error cargando matrículas de maestros: {e}', 'error')
        return render_template('matriculas_maestros.html', 
                             matriculas=[],
                             maestros=[],
                             now=datetime.now())

@app.route('/agregar_matricula_maestro', methods=['POST'])
def agregar_matricula_maestro():
    """Agregar nueva matrícula para maestro"""
    try:
        print("🎯 INICIANDO AGREGAR_MATRICULA_MAESTRO")
        
        # Obtener datos del formulario
        maestro_id = request.form.get('maestro_id')
        anio_escolar = request.form.get('anio_escolar')
        estado = request.form.get('estado')
        especialidad_principal = request.form.get('especialidad_principal')
        grado_asignado = request.form.get('grado_asignado')
        turno_asignado = request.form.get('turno_asignado')
        observaciones = request.form.get('observaciones', '')
        
        print(f"🎯 DATOS DEL FORMULARIO:")
        print(f"   maestro_id: {maestro_id}")
        print(f"   anio_escolar: {anio_escolar}")
        print(f"   estado: {estado}")
        print(f"   especialidad_principal: {especialidad_principal}")
        
        # Validar campos requeridos
        if not maestro_id or not anio_escolar or not estado:
            flash('Debe completar todos los campos requeridos', 'error')
            return redirect(url_for('matriculas_maestros'))
        
        # Convertir a enteros
        try:
            maestro_id = int(maestro_id)
            anio_escolar = int(anio_escolar)
        except ValueError as e:
            flash('Error en el formato de los datos numéricos', 'error')
            return redirect(url_for('matriculas_maestros'))
        
        # Verificar que el maestro existe
        maestro = Maestro.obtener_por_id(maestro_id)
        if not maestro:
            flash('El maestro seleccionado no existe', 'error')
            return redirect(url_for('matriculas_maestros'))
        
        print(f"🎯 MAESTRO ENCONTRADO: {maestro['nombre']} {maestro['apellido']}")

        # Crear objeto matrícula de maestro
        matricula = MatriculaMaestro(
            maestro_id=maestro_id,
            fecha_matricula=datetime.now().date(),
            anio_escolar=anio_escolar,
            estado=estado,
            especialidad_principal=especialidad_principal,
            grado_asignado=grado_asignado,
            turno_asignado=turno_asignado,
            observaciones=observaciones
        )
        
        print("🎯 OBJETO MATRICULA MAESTRO CREADO, LLAMANDO A guardar()...")
        
        # Guardar matrícula
        resultado = matricula.guardar()
        
        print(f"🎯 RESULTADO DE guardar(): {resultado}")
        
        if resultado:
            print("✅ MATRÍCULA MAESTRO GUARDADA EXITOSAMENTE")
            flash('Matrícula de maestro agregada correctamente', 'success')
        else:
            print("❌ matricula.guardar() retornó False")
            flash('Error al agregar matrícula de maestro', 'error')
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en agregar_matricula_maestro: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al procesar la solicitud: {str(e)}', 'error')
    
    return redirect(url_for('matriculas_maestros'))

@app.route('/cambiar_estado_matricula_maestro', methods=['POST'])
def cambiar_estado_matricula_maestro():
    """Cambiar estado de matrícula de maestro"""
    try:
        data = request.get_json()
        matricula_id = data['matricula_id']
        estado = data['estado']
        
        resultado = MatriculaMaestro.actualizar_estado(matricula_id, estado)
        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/eliminar_matricula_maestro', methods=['POST'])
def eliminar_matricula_maestro():
    """Eliminar matrícula de maestro"""
    try:
        data = request.get_json()
        matricula_id = data['matricula_id']
        
        print(f"🎯 Eliminando matrícula de maestro ID: {matricula_id}")
        
        resultado = MatriculaMaestro.eliminar(matricula_id)
        
        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo eliminar la matrícula'})
            
    except Exception as e:
        print(f"❌ Error eliminando matrícula de maestro: {e}")
        return jsonify({'success': False, 'error': str(e)})
    
# ===== RUTAS PARA MAESTROS =====
@app.route('/maestros')
def maestros():
    try:
        # Obtener parámetros de búsqueda
        search = request.args.get('search', '').strip()
        letra_apellido = request.args.get('letra_apellido', '')
        especialidad = request.args.get('especialidad', '')
        
        # Obtener todos los maestros
        if search:
            maestros = Maestro.buscar(search) or []
        else:
            maestros = Maestro.obtener_todos() or []
        
        # Aplicar filtros adicionales
        if letra_apellido:
            maestros = [m for m in maestros if 
                       m['apellido'] and m['apellido'].upper().startswith(letra_apellido.upper())]
        
        if especialidad:
            maestros = [m for m in maestros if m['especialidad'] == especialidad]
        
        return render_template('maestros.html', maestros=maestros)
    except Exception as e:
        flash(f'Error cargando maestros: {e}', 'error')
        return render_template('maestros.html', maestros=[])

@app.route('/agregar_maestro', methods=['GET', 'POST'])
def agregar_maestro():
    if request.method == 'POST':
        try:
            print("🎯 INICIANDO AGREGAR MAESTRO - DEBUG")
            print(f"📋 Datos del formulario: {request.form}")
            
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            email = request.form['email']
            telefono = request.form.get('telefono', '')
            especialidad = request.form['especialidad']
            fecha_contratacion = request.form.get('fecha_contratacion')
            salario = request.form.get('salario')
            direccion = request.form.get('direccion', '')
            notas = request.form.get('notas', '')
            activo = request.form.get('activo') == 'true'

            print(f"🔍 Datos procesados:")
            print(f"   Nombre: {nombre}")
            print(f"   Apellido: {apellido}")
            print(f"   Email: {email}")
            print(f"   Especialidad: {especialidad}")
            print(f"   Teléfono: {telefono}")
            print(f"   Fecha Contratación: {fecha_contratacion}")
            print(f"   Salario: {salario}")
            print(f"   Activo: {activo}")

            # Convertir salario a float si existe
            salario_float = float(salario) if salario else None
            
            # Manejar especialidad "Otro"
            if especialidad == 'Otro':
                especialidad = request.form.get('otra_especialidad', 'General')
                print(f"🔍 Especialidad cambiada a: {especialidad}")

            if not nombre or not apellido or not email or not especialidad:
                flash('Por favor complete todos los campos requeridos', 'error')
                return render_template('agregar_maestro.html')

            maestro = Maestro(
                nombre=nombre,
                apellido=apellido,
                email=email,
                telefono=telefono,
                especialidad=especialidad,
                fecha_contratacion=fecha_contratacion,
                salario=salario_float,
                direccion=direccion,
                notas=notas,
                activo=activo
            )

            print("🎯 Intentando guardar maestro...")
            resultado = maestro.guardar()
            
            if resultado:
                print("✅ Maestro guardado exitosamente")
                flash('Maestro agregado correctamente', 'success')
                return redirect(url_for('maestros'))
            else:
                print("❌ Error al guardar maestro")
                flash('Error al agregar maestro. Verifique que el email no exista.', 'error')
                
        except Exception as e:
            print(f"❌ Error al procesar el formulario: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error al procesar el formulario: {e}', 'error')

    return render_template('agregar_maestro.html', now=datetime.now())

@app.route('/editar_maestro/<int:id>', methods=['GET', 'POST'])
def editar_maestro(id):
    try:
        maestro_data = Maestro.obtener_por_id(id)
        if not maestro_data:
            flash('Maestro no encontrado', 'error')
            return redirect(url_for('maestros'))
        
        maestro = Maestro(**maestro_data)
        
        if request.method == 'POST':
            maestro.nombre = request.form['nombre']
            maestro.apellido = request.form['apellido']
            maestro.email = request.form['email']
            maestro.telefono = request.form.get('telefono', '')
            maestro.especialidad = request.form['especialidad']
            maestro.fecha_contratacion = request.form.get('fecha_contratacion')
            
            # Manejar salario
            salario = request.form.get('salario')
            maestro.salario = float(salario) if salario else None
            
            maestro.direccion = request.form.get('direccion', '')
            maestro.notas = request.form.get('notas', '')
            maestro.activo = request.form.get('activo') == 'true'
            
            # Manejar especialidad "Otro"
            if maestro.especialidad == 'Otro':
                maestro.especialidad = request.form.get('otra_especialidad', 'General')
            
            resultado = maestro.actualizar()
            if resultado:
                flash('Maestro actualizado correctamente', 'success')
                return redirect(url_for('maestros'))
            else:
                flash('Error al actualizar maestro', 'error')
        
        return render_template('editar_maestro.html', maestro=maestro, now=datetime.now())
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('maestros'))

@app.route('/eliminar_maestro/<int:id>')
def eliminar_maestro(id):
    try:
        resultado = Maestro.eliminar(id)
        if resultado:
            flash('Maestro eliminado correctamente', 'success')
        else:
            flash('Error al eliminar maestro', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
    return redirect(url_for('maestros'))

def obtener_info_maestro(maestro_id):
    """Obtener información completa del maestro basado en el ID"""
    try:
        # Obtener datos del maestro
        maestro = Maestro.obtener_por_id(maestro_id)
        if not maestro:
            return None
        
        # Obtener matrícula actual del maestro
        db = Database()
        matricula_maestro = db.fetch_one("""
            SELECT * FROM matriculas_maestros 
            WHERE maestro_id = %s AND estado = 'Activa'
            ORDER BY fecha_matricula DESC 
            LIMIT 1
        """, (maestro_id,))
        
        return {
            'maestro': maestro,
            'matricula_actual': matricula_maestro
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo info maestro: {e}")
        return None

# ===== RUTAS PARA PASE DE LISTA =====

@app.route('/pase_lista')
def pase_lista():
    try:
        # Obtener parámetros de filtro
        grupo_id = request.args.get('grupo_id', type=int)
        materia = request.args.get('materia', '')
        dia = request.args.get('dia', '')
        mes = request.args.get('mes', type=int)
        
        # Consulta base usando Database
        db = Database()
        
        # Consulta corregida - más simple y directa
        query = """
            SELECT 
                la.*, 
                g.nombre as grupo_nombre, 
                g.grado, 
                g.turno,
                (SELECT COUNT(*) FROM asistencias_alumnos aa WHERE aa.lista_id = la.id AND aa.asistio = 1) as total_asistencia,
                (SELECT COUNT(*) FROM matriculas m WHERE m.grupo_id = g.id AND m.estado = 'Activa') as total_alumnos
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE 1=1
        """
        params = []
        
        if grupo_id:
            query += " AND la.grupo_id = %s"
            params.append(grupo_id)
        
        if materia:
            query += " AND la.materia LIKE %s"
            params.append(f"%{materia}%")
        
        if dia:
            query += " AND la.fecha = %s"
            params.append(dia)
        
        if mes:
            query += " AND MONTH(la.fecha) = %s"
            params.append(mes)
        
        query += " ORDER BY la.fecha DESC, la.hora DESC"
        
        listas_asistencia = db.fetch_all(query, params) or []
        
        # Obtener todos los grupos para el filtro
        todos_grupos = Grupo.obtener_todos() or []
        
        # Pasar la fecha actual al template
        now = datetime.now()
        
        print(f"🔍 Listas encontradas: {len(listas_asistencia)}")  # Debug
        
        return render_template('pase_lista.html', 
                             listas_asistencia=listas_asistencia,
                             todos_grupos=todos_grupos,
                             now=now)
    except Exception as e:
        flash(f'Error cargando listas de asistencia: {e}', 'error')
        import traceback
        traceback.print_exc()  # Para ver el error completo
        now = datetime.now()
        return render_template('pase_lista.html', 
                             listas_asistencia=[],
                             todos_grupos=[],
                             now=now)

@app.route('/crear_lista_asistencia', methods=['POST'])
def crear_lista_asistencia():
    try:
        grupo_id = request.form['grupo_id']
        fecha = request.form['fecha']
        hora = request.form['hora']
        materia = request.form['materia']
        profesor = request.form['profesor']
        
        # Obtener el mes automáticamente de la fecha
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        mes = fecha_obj.strftime('%B')  # Nombre completo del mes
        
        db = Database()
        resultado = db.execute_query("""
            INSERT INTO listas_asistencia (grupo_id, fecha, mes, hora, materia, profesor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (grupo_id, fecha, mes, hora, materia, profesor))
        
        if resultado:
            flash('Lista de asistencia creada exitosamente', 'success')
        else:
            flash('Error al crear lista de asistencia', 'error')
            
    except Exception as e:
        flash(f'Error al crear lista: {str(e)}', 'error')
    
    return redirect(url_for('pase_lista'))

@app.route('/editar_lista_asistencia/<int:lista_id>')
def editar_lista_asistencia(lista_id):
    try:
        db = Database()
        
        # Obtener información de la lista
        lista = db.fetch_one("""
            SELECT la.*, g.nombre as grupo_nombre, g.grado, g.turno
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE la.id = %s
        """, (lista_id,))
        
        if not lista:
            flash('Lista de asistencia no encontrada', 'error')
            return redirect(url_for('pase_lista'))
        
        # Obtener total de listas en el sistema
        total_listas = db.fetch_one("SELECT COUNT(*) as total FROM listas_asistencia")
        total_listas_sistema = total_listas['total'] if total_listas else 0
        
        # Obtener alumnos del grupo con su asistencia y calificaciones
        alumnos = db.fetch_all("""
            SELECT 
                a.id, 
                m.codigo_matricula,
                a.nombre, 
                a.apellido, 
                COALESCE(aa.asistio, 0) as asistio,
                COALESCE(aa.calificacion, 0) as calificacion,
                COALESCE(aa.validado, 0) as validado
            FROM alumnos a
            JOIN matriculas m ON m.alumno_id = a.id AND m.grupo_id = %s AND m.estado = 'Activa'
            LEFT JOIN asistencias_alumnos aa ON aa.alumno_id = a.id AND aa.lista_id = %s
            ORDER BY a.nombre, a.apellido
        """, (lista['grupo_id'], lista_id)) or []
        
        # Calcular totales
        total_asistencia = sum(1 for alumno in alumnos if alumno['asistio'])
        total_validados = sum(1 for alumno in alumnos if alumno['validado'])
        
        return render_template('editar_lista_asistencia.html',
                             lista=lista,
                             alumnos=alumnos,
                             total_alumnos=len(alumnos),
                             total_asistencia=total_asistencia,
                             total_validados=total_validados,
                             total_listas_sistema=total_listas_sistema,
                             now=datetime.now())
    except Exception as e:
        flash(f'Error cargando lista de asistencia: {e}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('pase_lista'))

@app.route('/ver_lista_asistencia/<int:lista_id>')
def ver_lista_asistencia(lista_id):
    """Ver lista de asistencia (solo lectura)"""
    try:
        db = Database()
        
        # Obtener información de la lista
        lista = db.fetch_one("""
            SELECT la.*, g.nombre as grupo_nombre, g.grado, g.turno
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE la.id = %s
        """, (lista_id,))
        
        if not lista:
            flash('Lista de asistencia no encontrada', 'error')
            return redirect(url_for('pase_lista'))
        
        # Obtener alumnos del grupo con su asistencia y calificaciones
        alumnos = db.fetch_all("""
            SELECT 
                a.id, 
                m.codigo_matricula,  -- Usar codigo_matricula de la tabla matriculas
                a.nombre, 
                a.apellido, 
                COALESCE(aa.asistio, 0) as asistio,
                COALESCE(aa.calificacion, 0) as calificacion,
                COALESCE(aa.validado, 0) as validado
            FROM alumnos a
            JOIN matriculas m ON m.alumno_id = a.id AND m.grupo_id = %s AND m.estado = 'Activa'
            LEFT JOIN asistencias_alumnos aa ON aa.alumno_id = a.id AND aa.lista_id = %s
            ORDER BY a.nombre, a.apellido
        """, (lista['grupo_id'], lista_id)) or []
        
        # Calcular totales
        total_alumnos = len(alumnos)
        total_asistencia = sum(1 for alumno in alumnos if alumno['asistio'])
        total_validados = sum(1 for alumno in alumnos if alumno['validado'])
        
        return render_template('ver_lista_asistencia.html',
                             lista=lista,
                             alumnos=alumnos,
                             total_alumnos=total_alumnos,
                             total_asistencia=total_asistencia,
                             total_validados=total_validados)
    except Exception as e:
        flash(f'Error cargando lista de asistencia: {e}', 'error')
        return redirect(url_for('pase_lista'))

@app.route('/guardar_asistencia', methods=['POST'])
def guardar_asistencia():
    try:
        lista_id = request.form['lista_id']
        db = Database()
        
        # Obtener todos los alumnos del grupo
        alumnos = db.fetch_all("""
            SELECT a.id 
            FROM alumnos a
            JOIN matriculas m ON m.alumno_id = a.id
            JOIN listas_asistencia la ON la.grupo_id = m.grupo_id
            WHERE la.id = %s AND m.estado = 'Activa'
        """, (lista_id,)) or []
        
        for alumno in alumnos:
            alumno_id = alumno['id']
            
            # Obtener valores del formulario
            asistio = request.form.get(f'asistencia_{alumno_id}') == '1'
            calificacion = request.form.get(f'calificacion_{alumno_id}')
            validado = request.form.get(f'validado_{alumno_id}') == 'on'
            
            # Convertir calificación
            calificacion_val = float(calificacion) if calificacion and calificacion.strip() else None
            
            # Verificar si ya existe un registro
            existe = db.fetch_one("""
                SELECT id FROM asistencias_alumnos 
                WHERE lista_id = %s AND alumno_id = %s
            """, (lista_id, alumno_id))
            
            if existe:
                # Actualizar registro existente
                db.execute_query("""
                    UPDATE asistencias_alumnos 
                    SET asistio = %s, calificacion = %s, validado = %s
                    WHERE lista_id = %s AND alumno_id = %s
                """, (asistio, calificacion_val, validado, lista_id, alumno_id))
            else:
                # Insertar nuevo registro
                db.execute_query("""
                    INSERT INTO asistencias_alumnos (lista_id, alumno_id, asistio, calificacion, validado)
                    VALUES (%s, %s, %s, %s, %s)
                """, (lista_id, alumno_id, asistio, calificacion_val, validado))
        
        flash('Asistencias y calificaciones guardadas exitosamente', 'success')
    except Exception as e:
        flash(f'Error al guardar: {str(e)}', 'error')
    
    return redirect(url_for('editar_lista_asistencia', lista_id=lista_id))

@app.route('/eliminar_lista_asistencia', methods=['POST'])
def eliminar_lista_asistencia():
    try:
        data = request.get_json()
        lista_id = data.get('lista_id')
        
        db = Database()
        
        # Eliminar registros de asistencia primero
        db.execute_query("DELETE FROM asistencias_alumnos WHERE lista_id = %s", (lista_id,))
        # Eliminar la lista
        resultado = db.execute_query("DELETE FROM listas_asistencia WHERE id = %s", (lista_id,))
        
        if resultado:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No se pudo eliminar la lista'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== RUTAS PARA VALIDACIÓN DE ASISTENCIA POR ESTUDIANTES =====

@app.route('/estudiante/asistencia')
def estudiante_asistencia():
    """Vista para que los estudiantes validen su asistencia"""
    if 'usuario' not in session or session['usuario']['rol'] != 'estudiante':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        usuario = session['usuario']
        db = Database()
        
        # Obtener información del estudiante
        estudiante_info = obtener_info_estudiante(usuario['matricula_id'])
        if not estudiante_info:
            flash('No se encontró información del estudiante', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener listas de asistencia del grupo del estudiante
        grupo_id = estudiante_info['matricula_actual']['grupo_id']
        if not grupo_id:
            flash('No estás asignado a un grupo', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener listas de asistencia recientes del grupo
        listas_asistencia = db.fetch_all("""
            SELECT la.*, g.nombre as grupo_nombre
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE la.grupo_id = %s 
            AND la.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY la.fecha DESC, la.hora DESC
        """, (grupo_id,)) or []
        
        # Para cada lista, obtener el estado de asistencia del estudiante
        for lista in listas_asistencia:
            asistencia_estudiante = db.fetch_one("""
                SELECT aa.asistio, aa.calificacion, aa.validado
                FROM asistencias_alumnos aa
                WHERE aa.lista_id = %s AND aa.alumno_id = %s
            """, (lista['id'], estudiante_info['alumno']['id']))
            
            if asistencia_estudiante:
                lista['asistio_estudiante'] = asistencia_estudiante['asistio']
                lista['calificacion_estudiante'] = asistencia_estudiante['calificacion']
                lista['validado_estudiante'] = asistencia_estudiante['validado']
            else:
                lista['asistio_estudiante'] = False
                lista['calificacion_estudiante'] = None
                lista['validado_estudiante'] = False
        
        return render_template('estudiante_asistencia.html',
                             estudiante=estudiante_info,
                             listas_asistencia=listas_asistencia,
                             now=datetime.now())
        
    except Exception as e:
        flash(f'Error cargando asistencia: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/estudiante/validar_asistencia', methods=['POST'])
def estudiante_validar_asistencia():
    """Permite al estudiante validar su asistencia"""
    if 'usuario' not in session or session['usuario']['rol'] != 'estudiante':
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        data = request.get_json()
        lista_id = data.get('lista_id')
        validar = data.get('validar', True)
        
        usuario = session['usuario']
        estudiante_info = obtener_info_estudiante(usuario['matricula_id'])
        
        if not estudiante_info:
            return jsonify({'success': False, 'error': 'Estudiante no encontrado'})
        
        db = Database()
        
        # Verificar si existe registro de asistencia
        asistencia_existente = db.fetch_one("""
            SELECT id FROM asistencias_alumnos 
            WHERE lista_id = %s AND alumno_id = %s
        """, (lista_id, estudiante_info['alumno']['id']))
        
        if asistencia_existente:
            # Actualizar validación
            db.execute_query("""
                UPDATE asistencias_alumnos 
                SET validado = %s 
                WHERE lista_id = %s AND alumno_id = %s
            """, (validar, lista_id, estudiante_info['alumno']['id']))
        else:
            # Crear nuevo registro (solo con validación, sin asistencia)
            db.execute_query("""
                INSERT INTO asistencias_alumnos (lista_id, alumno_id, asistio, calificacion, validado)
                VALUES (%s, %s, %s, %s, %s)
            """, (lista_id, estudiante_info['alumno']['id'], False, None, validar))
        
        # Registrar la acción en un log (opcional)
        db.execute_query("""
            INSERT INTO logs_validacion (lista_id, alumno_id, accion, fecha_validacion)
            VALUES (%s, %s, %s, %s)
        """, (lista_id, estudiante_info['alumno']['id'], 
              'VALIDADO' if validar else 'NO_VALIDADO', 
              datetime.now()))
        
        return jsonify({
            'success': True,
            'message': 'Asistencia validada correctamente' if validar else 'Validación removida'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/estudiante/detalle_asistencia/<int:lista_id>')
def estudiante_detalle_asistencia(lista_id):
    """Mostrar detalles de una lista de asistencia específica para el estudiante"""
    if 'usuario' not in session or session['usuario']['rol'] != 'estudiante':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        usuario = session['usuario']
        db = Database()
        
        # Obtener información de la lista
        lista = db.fetch_one("""
            SELECT la.*, g.nombre as grupo_nombre, g.grado, g.turno
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE la.id = %s
        """, (lista_id,))
        
        if not lista:
            flash('Lista de asistencia no encontrada', 'error')
            return redirect(url_for('estudiante_asistencia'))
        
        # Obtener información del estudiante
        estudiante_info = obtener_info_estudiante(usuario['matricula_id'])
        
        # Obtener asistencia específica del estudiante
        asistencia_estudiante = db.fetch_one("""
            SELECT aa.asistio, aa.calificacion, aa.validado
            FROM asistencias_alumnos aa
            WHERE aa.lista_id = %s AND aa.alumno_id = %s
        """, (lista_id, estudiante_info['alumno']['id']))
        
        return render_template('estudiante_detalle_asistencia.html',
                             lista=lista,
                             estudiante=estudiante_info,
                             asistencia=asistencia_estudiante)
        
    except Exception as e:
        flash(f'Error cargando detalle de asistencia: {e}', 'error')
        return redirect(url_for('estudiante_asistencia'))
    
# ===== RUTAS DE AUTENTICACIÓN =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir al dashboard
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
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
            
            # ✅ NUEVA VALIDACIÓN: Verificar si la matrícula permite login
            db = Database()
            
            if usuario.matricula_id:
                # Es un estudiante - verificar en tabla matriculas
                matricula = db.fetch_one("""
                    SELECT permite_login, estado FROM matriculas 
                    WHERE id = %s
                """, (usuario.matricula_id,))
                
                if matricula:
                    if not matricula['permite_login']:
                        flash('Su matrícula no tiene permisos para iniciar sesión. Contacte al administrador.', 'error')
                        return render_template('login.html')
                    if matricula['estado'] != 'Activa':
                        flash('Su matrícula no está activa. Contacte al administrador.', 'error')
                        return render_template('login.html')
            
            elif usuario.maestro_id:
                # Es un maestro - verificar en tabla matriculas_maestros
                matricula_maestro = db.fetch_one("""
                    SELECT permite_login, estado FROM matriculas_maestros 
                    WHERE maestro_id = %s
                """, (usuario.maestro_id,))
                
                if matricula_maestro:
                    if not matricula_maestro['permite_login']:
                        flash('Su matrícula de maestro no tiene permisos para iniciar sesión. Contacte al administrador.', 'error')
                        return render_template('login.html')
                    if matricula_maestro['estado'] != 'Activa':
                        flash('Su matrícula de maestro no está activa. Contacte al administrador.', 'error')
                        return render_template('login.html')
            
            # Actualizar último login
            usuario.actualizar_ultimo_login()
            
            # Guardar en sesión
            session['usuario'] = {
                'id': usuario.id,
                'username': usuario.username,
                'rol': usuario.rol,
                'matricula_id': usuario.matricula_id,
                'maestro_id': usuario.maestro_id
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

@app.route('/dashboard_maestro')
def dashboard_maestro():
    """Dashboard específico para maestros"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if session['usuario']['rol'] != 'maestro':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        usuario = session['usuario']
        db = Database()
        
        # Obtener información del maestro
        maestro_info = obtener_info_maestro(usuario['maestro_id'])
        
        # Obtener grupos asignados al maestro
        grupos_asignados = db.fetch_all("""
            SELECT DISTINCT g.*, 
                   (SELECT COUNT(*) FROM matriculas m WHERE m.grupo_id = g.id AND m.estado = 'Activa') as total_estudiantes
            FROM grupos g
            JOIN horarios h ON h.grupo_id = g.id
            WHERE h.profesor LIKE %s
            ORDER BY g.grado, g.nombre
        """, (f"%{maestro_info['maestro']['nombre']}%",)) or []
        
        # Obtener materias por grupo
        for grupo in grupos_asignados:
            materias = db.fetch_all("""
                SELECT DISTINCT materia 
                FROM horarios 
                WHERE grupo_id = %s AND profesor LIKE %s
            """, (grupo['id'], f"%{maestro_info['maestro']['nombre']}%")) or []
            grupo['materias'] = [m['materia'] for m in materias]
        
        # Calcular total de estudiantes
        total_estudiantes = sum(grupo['total_estudiantes'] for grupo in grupos_asignados)
        
        # Obtener listas de asistencia recientes del maestro
        listas_recientes = db.fetch_all("""
            SELECT la.*, g.nombre as grupo_nombre,
                   (SELECT COUNT(*) FROM asistencias_alumnos aa WHERE aa.lista_id = la.id AND aa.asistio = 1) as total_asistencia,
                   (SELECT COUNT(*) FROM matriculas m WHERE m.grupo_id = g.id AND m.estado = 'Activa') as total_alumnos
            FROM listas_asistencia la
            JOIN grupos g ON la.grupo_id = g.id
            WHERE la.profesor LIKE %s
            ORDER BY la.fecha DESC, la.hora DESC
            LIMIT 5
        """, (f"%{maestro_info['maestro']['nombre']}%",)) or []
        
        # Contar listas de hoy
        listas_hoy = db.fetch_one("""
            SELECT COUNT(*) as total 
            FROM listas_asistencia 
            WHERE profesor LIKE %s AND fecha = CURDATE()
        """, (f"%{maestro_info['maestro']['nombre']}%",))
        listas_hoy = listas_hoy['total'] if listas_hoy else 0
        
        return render_template('dashboard_maestro.html',
                             maestro_info=maestro_info,
                             grupos_asignados=grupos_asignados,
                             total_estudiantes=total_estudiantes,
                             listas_recientes=listas_recientes,
                             listas_hoy=listas_hoy,
                             now=datetime.now())
        
    except Exception as e:
        print(f"❌ Error en dashboard maestro: {e}")
        flash('Error cargando el dashboard', 'error')
        return render_template('dashboard_maestro.html',
                             maestro_info=None,
                             grupos_asignados=[],
                             total_estudiantes=0,
                             listas_recientes=[],
                             listas_hoy=0,
                             now=datetime.now())

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
        
        # Obtener total de usuarios
        db = Database()
        total_usuarios_result = db.fetch_one("SELECT COUNT(*) as total FROM usuarios")
        total_usuarios = total_usuarios_result['total'] if total_usuarios_result else 0
        
        # Obtener total de listas de asistencia
        total_listas_result = db.fetch_one("SELECT COUNT(*) as total FROM listas_asistencia")
        total_listas = total_listas_result['total'] if total_listas_result else 0
        
        # Obtener información de cumpleaños
        hoy = datetime.now().date()
        
        # Cumpleaños hoy
        cumpleanos_hoy = db.fetch_one("""
            SELECT COUNT(*) as total FROM alumnos 
            WHERE fecha_nacimiento IS NOT NULL 
            AND MONTH(fecha_nacimiento) = %s AND DAY(fecha_nacimiento) = %s
        """, (hoy.month, hoy.day))
        total_cumpleanos_hoy = cumpleanos_hoy['total'] if cumpleanos_hoy else 0
        
        # Cumpleaños esta semana
        cumpleanos_semana = db.fetch_one("""
            SELECT COUNT(*) as total FROM alumnos 
            WHERE fecha_nacimiento IS NOT NULL 
            AND (
                (MONTH(fecha_nacimiento) = %s AND DAY(fecha_nacimiento) BETWEEN %s AND %s) OR
                (MONTH(fecha_nacimiento) = %s AND DAY(fecha_nacimiento) BETWEEN 1 AND %s)
            )
        """, (
            hoy.month, hoy.day, min(hoy.day + 6, 31),
            hoy.month % 12 + 1, (hoy.day + 6) % 31
        ))
        total_cumpleanos_semana = cumpleanos_semana['total'] if cumpleanos_semana else 0
        
        # Cumpleaños este mes
        cumpleanos_mes = db.fetch_one("""
            SELECT COUNT(*) as total FROM alumnos 
            WHERE fecha_nacimiento IS NOT NULL 
            AND MONTH(fecha_nacimiento) = %s
        """, (hoy.month,))
        total_cumpleanos_mes = cumpleanos_mes['total'] if cumpleanos_mes else 0
        
        # Próximo cumpleaños
        proximo_cumpleanos = db.fetch_one("""
            SELECT a.id, a.nombre, a.apellido, a.fecha_nacimiento, g.nombre as grupo_nombre
            FROM alumnos a
            LEFT JOIN matriculas m ON m.alumno_id = a.id AND m.estado = 'Activa'
            LEFT JOIN grupos g ON m.grupo_id = g.id
            WHERE a.fecha_nacimiento IS NOT NULL
            ORDER BY 
                CASE 
                    WHEN (MONTH(a.fecha_nacimiento) > %s OR 
                         (MONTH(a.fecha_nacimiento) = %s AND DAY(a.fecha_nacimiento) >= %s))
                    THEN (MONTH(a.fecha_nacimiento) * 100 + DAY(a.fecha_nacimiento))
                    ELSE (MONTH(a.fecha_nacimiento) * 100 + DAY(a.fecha_nacimiento)) + 1200
                END
            LIMIT 1
        """, (hoy.month, hoy.month, hoy.day))
        
        # Procesar próximo cumpleaños
        proximo_cumpleanos_data = None
        if proximo_cumpleanos and proximo_cumpleanos['fecha_nacimiento']:
            fecha_nac = proximo_cumpleanos['fecha_nacimiento']
            cumple_este_anio = fecha_nac.replace(year=hoy.year)
            if cumple_este_anio < hoy:
                cumple_este_anio = cumple_este_anio.replace(year=hoy.year + 1)
            
            dias_restantes = (cumple_este_anio - hoy).days
            
            # Obtener nombre del mes en español
            meses_espanol = [
                'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
            ]
            nombre_mes = meses_espanol[fecha_nac.month - 1]
            
            proximo_cumpleanos_data = {
                'nombre': proximo_cumpleanos['nombre'],
                'apellido': proximo_cumpleanos['apellido'],
                'fecha_nacimiento': fecha_nac,
                'grupo': proximo_cumpleanos['grupo_nombre'],
                'dias_restantes': dias_restantes,
                'nombre_mes': nombre_mes
            }
        
        # Dashboard diferente según el rol
        if usuario['rol'] == 'admin':
            return render_template('dashboard_admin.html', 
                                 usuario=usuario,
                                 total_alumnos=total_alumnos,
                                 total_grupos=total_grupos,
                                 total_matriculas=total_matriculas,
                                 total_usuarios=total_usuarios,
                                 total_listas=total_listas,
                                 total_cumpleanos_hoy=total_cumpleanos_hoy,
                                 total_cumpleanos_semana=total_cumpleanos_semana,
                                 total_cumpleanos_mes=total_cumpleanos_mes,
                                 proximo_cumpleanos=proximo_cumpleanos_data,
                                 now=datetime.now())
        else:
            # Obtener información completa del estudiante
            estudiante_info = obtener_info_estudiante(usuario['matricula_id'])
            
            # Verificar si hay felicitaciones pendientes (con manejo de errores)
            tiene_felicitacion = False
            if estudiante_info and estudiante_info.get('alumno'):
                try:
                    # Primero verificar si la tabla existe
                    tabla_existe = db.fetch_one("""
                        SELECT TABLE_NAME 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_NAME = 'felicitaciones_cumpleanos'
                    """)
                    
                    if tabla_existe:
                        felicitacion = db.fetch_one("""
                            SELECT * FROM felicitaciones_cumpleanos 
                            WHERE alumno_id = %s AND fecha_envio >= CURDATE() - INTERVAL 7 DAY
                            ORDER BY fecha_envio DESC LIMIT 1
                        """, (estudiante_info['alumno']['id'],))
                        tiene_felicitacion = felicitacion is not None
                except Exception as e:
                    print(f"⚠️ Error verificando felicitaciones: {e}")
                    # Si hay error, continuar sin felicitaciones
            
            return render_template('dashboard_estudiante.html', 
                                 usuario=usuario,
                                 estudiante=estudiante_info,
                                 Matricula=Matricula,
                                 tiene_felicitacion=tiene_felicitacion,
                                 now=datetime.now())
                                 
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        flash('Error cargando el dashboard', 'error')
        # Renderizar según el rol con valores por defecto
        if usuario['rol'] == 'admin':
            return render_template('dashboard_admin.html', 
                                 usuario=usuario,
                                 total_alumnos=0,
                                 total_grupos=0,
                                 total_matriculas=0,
                                 total_usuarios=0,
                                 total_listas=0,
                                 total_cumpleanos_hoy=0,
                                 total_cumpleanos_semana=0,
                                 total_cumpleanos_mes=0,
                                 proximo_cumpleanos=None,
                                 now=datetime.now())
        else:
            return render_template('dashboard_estudiante.html', 
                                 usuario=usuario,
                                 estudiante=None,
                                 tiene_felicitacion=False,
                                 now=datetime.now())

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
    # Redirigir directamente al login
    return redirect(url_for('login'))

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
@app.route('/cumpleanos')
def cumpleanos_alumnos():
    """Calendario de cumpleaños de alumnos"""
    try:
        # Obtener parámetros de filtro
        mes = request.args.get('mes', type=int)
        orden = request.args.get('orden', 'dia')
        
        # Obtener todos los alumnos con fecha de nacimiento
        db = Database()
        query = "SELECT * FROM alumnos WHERE fecha_nacimiento IS NOT NULL"
        params = []
        
        if mes:
            query += " AND MONTH(fecha_nacimiento) = %s"
            params.append(mes)
        
        # Ordenar
        if orden == 'dia':
            query += " ORDER BY DAY(fecha_nacimiento), MONTH(fecha_nacimiento)"
        elif orden == 'nombre':
            query += " ORDER BY nombre, apellido"
        elif orden == 'edad':
            query += " ORDER BY fecha_nacimiento DESC"
        
        alumnos_db = db.fetch_all(query, params) or []
        
        # Procesar datos para el template
        alumnos = []
        hoy = datetime.now().date()
        cumpleanos_hoy = 0
        cumpleanos_este_mes = 0
        cumpleanos_proxima_semana = 0
        
        for alumno in alumnos_db:
            if alumno['fecha_nacimiento']:
                fecha_nac = alumno['fecha_nacimiento']
                # Calcular edad
                edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
                
                # Calcular próximo cumpleaños
                cumple_este_anio = fecha_nac.replace(year=hoy.year)
                if cumple_este_anio < hoy:
                    cumple_este_anio = cumple_este_anio.replace(year=hoy.year + 1)
                
                dias_restantes = (cumple_este_anio - hoy).days
                
                # Estadísticas
                if fecha_nac.month == hoy.month:
                    cumpleanos_este_mes += 1
                    if fecha_nac.day == hoy.day:
                        cumpleanos_hoy += 1
                
                if 0 <= dias_restantes <= 7:
                    cumpleanos_proxima_semana += 1
                
                alumno_data = {
                    'id': alumno['id'],
                    'nombre': alumno['nombre'],
                    'apellido': alumno['apellido'],
                    'fecha_nacimiento': fecha_nac,
                    'edad': edad,
                    'dia_mes': fecha_nac.day,
                    'nombre_mes': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][fecha_nac.month - 1],
                    'iniciales': f"{alumno['nombre'][0]}{alumno['apellido'][0]}",
                    'dias_restantes': dias_restantes,
                    'cumple_hoy': fecha_nac.month == hoy.month and fecha_nac.day == hoy.day,
                    'cumple_proximo': dias_restantes <= 7 and dias_restantes > 0
                }
                alumnos.append(alumno_data)
        
        total_alumnos = len(Alumno.obtener_todos() or [])
        
        return render_template('cumpleanos_alumnos.html',
                             alumnos=alumnos,
                             total_alumnos=total_alumnos,
                             cumpleanos_hoy=cumpleanos_hoy,
                             cumpleanos_este_mes=cumpleanos_este_mes,
                             cumpleanos_proxima_semana=cumpleanos_proxima_semana)
        
    except Exception as e:
        flash(f'Error cargando calendario de cumpleaños: {e}', 'error')
        return render_template('cumpleanos_alumnos.html',
                             alumnos=[],
                             total_alumnos=0,
                             cumpleanos_hoy=0,
                             cumpleanos_este_mes=0,
                             cumpleanos_proxima_semana=0)

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
            flash('Grupo no encontrada', 'error')
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

# ===== RUTAS PARA MATRÍCULAS CON BÚSQUEDA =====
@app.route('/matriculas')
def matriculas():
    try:
        # Obtener parámetros de búsqueda
        search = request.args.get('search', '').strip()
        estado = request.args.get('estado', '')
        anio_escolar = request.args.get('anio_escolar', '')
        grupo_id = request.args.get('grupo_id', '')
        
        # Obtener todos los grupos para el dropdown
        todos_grupos = Grupo.obtener_todos() or []
        
        # Obtener todos los alumnos para el modal
        alumnos = Alumno.obtener_todos() or []
        
        # Obtener matrículas con filtros
        db = Database()
        
        # Construir consulta base
        query = """
            SELECT m.*, 
                   a.nombre as alumno_nombre, 
                   a.apellido as alumno_apellido,
                   g.nombre as grupo_nombre,
                   g.id as grupo_id
            FROM matriculas m
            LEFT JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN grupos g ON m.grupo_id = g.id
            WHERE 1=1
        """
        params = []
        
        # Aplicar filtros
        if search:
            query += " AND (a.nombre LIKE %s OR a.apellido LIKE %s OR m.codigo_matricula LIKE %s OR g.nombre LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if estado:
            query += " AND m.estado = %s"
            params.append(estado)
        
        if anio_escolar:
            query += " AND m.anio_escolar = %s"
            params.append(int(anio_escolar))
        
        if grupo_id:
            query += " AND m.grupo_id = %s"
            params.append(int(grupo_id))
        
        # Ordenar por fecha de matrícula descendente
        query += " ORDER BY m.fecha_matricula DESC"
        
        # Ejecutar consulta
        matriculas = db.fetch_all(query, params) or []
        
        return render_template('matriculas.html', 
                             matriculas=matriculas,
                             todos_grupos=todos_grupos,
                             alumnos=alumnos,
                             now=datetime.now())
        
    except Exception as e:
        flash(f'Error cargando matrículas: {e}', 'error')
        # En caso de error, devolver datos básicos
        return render_template('matriculas.html', 
                             matriculas=[],
                             todos_grupos=[],
                             alumnos=[],
                             now=datetime.now())

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
        # Obtener todas las matrículas de alumnos
        db = Database()
        
        # Matrículas con usuario
        matriculas_con_usuario = db.fetch_all("""
            SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido,
                   g.nombre as grupo_nombre, u.username
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN grupos g ON m.grupo_id = g.id
            LEFT JOIN usuarios u ON u.matricula_id = m.id
            WHERE u.id IS NOT NULL
            ORDER BY a.apellido, a.nombre
        """) or []
        
        # Matrículas sin usuario
        matriculas_sin_usuario = db.fetch_all("""
            SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido,
                   g.nombre as grupo_nombre
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN grupos g ON m.grupo_id = g.id
            LEFT JOIN usuarios u ON u.matricula_id = m.id
            WHERE u.id IS NULL
            ORDER BY a.apellido, a.nombre
        """) or []
        
        # Matrículas de maestros
        matriculas_maestros = db.fetch_all("""
            SELECT mm.*, m.nombre as maestro_nombre, m.apellido as maestro_apellido,
                   u.username, u.id as usuario_id
            FROM matriculas_maestros mm
            JOIN maestros m ON mm.maestro_id = m.id
            LEFT JOIN usuarios u ON u.maestro_id = m.id
            ORDER BY m.apellido, m.nombre
        """) or []
        
        # Obtener todos los usuarios
        usuarios = db.fetch_all("""
            SELECT u.*, m.codigo_matricula, a.nombre, a.apellido, 
                   ma.nombre as maestro_nombre, ma.apellido as maestro_apellido
            FROM usuarios u 
            LEFT JOIN matriculas m ON u.matricula_id = m.id 
            LEFT JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN maestros ma ON u.maestro_id = ma.id
            ORDER BY u.username
        """) or []
        
        # Obtener total de listas en el sistema
        total_listas = db.fetch_one("SELECT COUNT(*) as total FROM listas_asistencia")
        total_listas_sistema = total_listas['total'] if total_listas else 0
        
        total_usuarios = len(usuarios)
        
        return render_template('admin_usuarios.html',
                             matriculas_con_usuario=matriculas_con_usuario,
                             matriculas_sin_usuario=matriculas_sin_usuario,
                             matriculas_maestros=matriculas_maestros,
                             usuarios=usuarios,
                             total_usuarios=total_usuarios,
                             total_listas_sistema=total_listas_sistema)
        
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
    
# ===== RUTAS PARA GENERACIÓN DE CREDENCIALES =====

@app.route('/credenciales')
def credenciales_index():
    """Página principal para generar credenciales"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    return render_template('generar_credenciales.html')

@app.route('/procesar_csv_credenciales', methods=['POST'])
def procesar_csv_credenciales():
    """Procesa el archivo CSV para credenciales"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        if 'archivo_csv' not in request.files:
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo_csv']
        
        if archivo.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        if not archivo.filename.lower().endswith('.csv'):
            return jsonify({'error': 'El archivo debe ser un CSV'}), 400
        
        # Guardar el archivo CSV en la carpeta uploads
        if archivo:
            # Crear un nombre único para el archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"csv_{timestamp}_{archivo.filename}"
            ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
            archivo.save(ruta_archivo)
            print(f"Archivo guardado en: {ruta_archivo}")
        
        # Procesar el CSV (usar el archivo guardado o el original)
        archivo.seek(0)  # Volver al inicio del archivo para procesarlo
        datos, error = procesar_csv(archivo)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'datos': datos,
            'total': len(datos),
            'archivo_guardado': nombre_archivo
        })
        
    except Exception as e:
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/generar_credenciales', methods=['POST'])
def generar_credenciales():
    """Genera las credenciales en formato HTML para imprimir"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        # Obtener datos del formulario
        datos_json = request.form.get('datos')
        
        if not datos_json:
            return jsonify({'error': 'No hay datos para generar credenciales'}), 400
        
        # Convertir string JSON a objeto Python
        datos = json.loads(datos_json)
        
        if not datos:
            return jsonify({'error': 'No hay datos válidos para generar credenciales'}), 400
        
        print(f"Generando {len(datos)} credenciales...")
        
        # AGREGAR ESTA LÍNEA: Pasar la fecha actual al template
        return render_template('credenciales.html', 
                             datos=datos, 
                             now=datetime.now())  # ← Agregar esta variable
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Error al decodificar JSON: {str(e)}'}), 400
    except Exception as e:
        import traceback
        print(f"Error en generar_credenciales: {traceback.format_exc()}")
        return jsonify({'error': f'Error al generar credenciales: {str(e)}'}), 500

@app.route('/archivos_csv')
def listar_archivos_csv():
    """Lista los archivos CSV guardados (solo admin)"""
    if 'usuario' not in session or session['usuario']['rol'] != 'admin':
        return jsonify({'error': 'Acceso denegado'}), 403
    
    try:
        archivos = os.listdir(app.config['UPLOAD_FOLDER'])
        archivos_csv = [f for f in archivos if f.lower().endswith('.csv')]
        return jsonify({'archivos': archivos_csv})
    except Exception as e:
        return jsonify({'error': f'Error al listar archivos: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    app.run(debug=True, port=5000)