import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

# Añade el directorio actual al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_2024'

# Importación después de configurar el path
try:
    from database import Database
    from models import Alumno, Grupo, Horario, Matricula
    print("✅ Módulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")

# Variable para controlar la inicialización de la base de datos
db_initialized = False

@app.before_request
def initialize_database():
    """Inicializar base de datos solo una vez al primer request"""
    global db_initialized
    if not db_initialized:
        try:
            db = Database()
            db.initialize_database()
            db_initialized = True
            print("✅ Base de datos inicializada correctamente")
        except Exception as e:
            print(f"❌ Error inicializando BD: {e}")

@app.route('/')
def index():
    try:
        # Calcular los datos para el dashboard
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
        año_escolar = request.form['año_escolar']
        
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
            año_escolar=año_escolar,
            estado='Activa'
        )
        
        resultado = matricula.guardar()
        if resultado:
            flash(f'Alumno {alumno["nombre"]} {alumno["apellido"]} agregado al grupo correctamente', 'success')
        else:
            flash('Error al agregar alumno al grupo', 'error')
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
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
        flash(f'Error: {str(e)}', 'error')
    
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
        alumno_id = request.form['alumno_id']
        grupo_id = request.form['grupo_id'] or None
        año_escolar = request.form['año_escolar']
        estado = request.form['estado']
        
        matricula = Matricula(
            alumno_id=alumno_id,
            grupo_id=grupo_id,
            fecha_matricula=datetime.now().date(),
            año_escolar=año_escolar,
            estado=estado
        )
        
        resultado = matricula.guardar()
        if resultado:
            flash('Matrícula agregada correctamente', 'success')
        else:
            flash('Error al agregar matrícula', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    
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

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    app.run(debug=True, port=5000)