from database import Database
from datetime import datetime
import bcrypt

db = Database()

class Alumno:
    def __init__(self, id=None, nombre=None, apellido=None, fecha_nacimiento=None,
                 email=None, telefono=None, direccion=None, **kwargs):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.fecha_nacimiento = fecha_nacimiento
        self.email = email
        self.telefono = telefono
        self.direccion = direccion

    def guardar(self):
        """Guardar nuevo alumno en la base de datos"""
        try:
            query = """
            INSERT INTO alumnos (nombre, apellido, fecha_nacimiento, email, telefono, direccion)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (self.nombre, self.apellido, self.fecha_nacimiento,
                      self.email, self.telefono, self.direccion)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error guardando alumno: {e}")
            return False

    @staticmethod
    def obtener_todos():
        """Obtener todos los alumnos"""
        try:
            query = "SELECT * FROM alumnos ORDER BY apellido, nombre"
            return db.fetch_all(query)
        except Exception as e:
            print(f"❌ Error obteniendo alumnos: {e}")
            return []

    @staticmethod
    def obtener_por_id(alumno_id):
        """Obtener alumno por ID"""
        try:
            query = "SELECT * FROM alumnos WHERE id = %s"
            return db.fetch_one(query, (alumno_id,))
        except Exception as e:
            print(f"❌ Error obteniendo alumno por ID: {e}")
            return None

    def actualizar(self):
        """Actualizar alumno en la base de datos"""
        try:
            query = """
            UPDATE alumnos 
            SET nombre = %s, apellido = %s, fecha_nacimiento = %s, 
                email = %s, telefono = %s, direccion = %s 
            WHERE id = %s
            """
            params = (self.nombre, self.apellido, self.fecha_nacimiento,
                      self.email, self.telefono, self.direccion, self.id)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error actualizando alumno: {e}")
            return False

    @staticmethod
    def eliminar(alumno_id):
        """Eliminar alumno de la base de datos"""
        try:
            query = "DELETE FROM alumnos WHERE id = %s"
            return db.execute_query(query, (alumno_id,))
        except Exception as e:
            print(f"❌ Error eliminando alumno: {e}")
            return False


class Grupo:
    def __init__(self, id=None, nombre=None, grado=None, turno=None, capacidad=None):
        self.id = id
        self.nombre = nombre
        self.grado = grado
        self.turno = turno
        self.capacidad = capacidad

    def guardar(self):
        try:
            query = """
            INSERT INTO grupos (nombre, grado, turno, capacidad)
            VALUES (%s, %s, %s, %s)
            """
            params = (self.nombre, self.grado, self.turno, self.capacidad)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error guardando grupo: {e}")
            return False

    @staticmethod
    def obtener_todos():
        try:
            query = "SELECT * FROM grupos ORDER BY grado, nombre"
            return db.fetch_all(query)
        except Exception as e:
            print(f"❌ Error obteniendo grupos: {e}")
            return []

    @staticmethod
    def obtener_por_id(grupo_id):
        try:
            query = "SELECT * FROM grupos WHERE id = %s"
            return db.fetch_one(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error obteniendo grupo por ID: {e}")
            return None

    def actualizar(self):
        try:
            query = """
            UPDATE grupos 
            SET nombre = %s, grado = %s, turno = %s, capacidad = %s 
            WHERE id = %s
            """
            params = (self.nombre, self.grado, self.turno, self.capacidad, self.id)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error actualizando grupo: {e}")
            return False

    @staticmethod
    def eliminar(grupo_id):
        try:
            query = "DELETE FROM grupos WHERE id = %s"
            return db.execute_query(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error eliminando grupo: {e}")
            return False

    @staticmethod
    def obtener_alumnos_por_grupo(grupo_id):
        try:
            query = """
            SELECT a.* FROM alumnos a
            JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.grupo_id = %s AND m.estado = 'Activa'
            """
            return db.fetch_all(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error obteniendo alumnos del grupo: {e}")
            return []


class Horario:
    def __init__(self, id=None, grupo_id=None, dia_semana=None, hora_inicio=None,
                 hora_fin=None, materia=None, profesor=None):
        self.id = id
        self.grupo_id = grupo_id
        self.dia_semana = dia_semana
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin
        self.materia = materia
        self.profesor = profesor

    def guardar(self):
        try:
            query = """
            INSERT INTO horarios (grupo_id, dia_semana, hora_inicio, hora_fin, materia, profesor)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (self.grupo_id, self.dia_semana, self.hora_inicio,
                      self.hora_fin, self.materia, self.profesor)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error guardando horario: {e}")
            return False

    @staticmethod
    def obtener_por_grupo(grupo_id):
        try:
            query = """
            SELECT * FROM horarios 
            WHERE grupo_id = %s 
            ORDER BY 
                FIELD(dia_semana, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'),
                hora_inicio
            """
            return db.fetch_all(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error obteniendo horarios del grupo: {e}")
            return []

    @staticmethod
    def eliminar(horario_id):
        try:
            query = "DELETE FROM horarios WHERE id = %s"
            return db.execute_query(query, (horario_id,))
        except Exception as e:
            print(f"❌ Error eliminando horario: {e}")
            return False


class Matricula:
    def __init__(self, id=None, alumno_id=None, grupo_id=None, fecha_matricula=None,
                 anio_escolar=None, estado=None, codigo_matricula=None):
        self.id = id
        self.alumno_id = alumno_id
        self.grupo_id = grupo_id
        self.fecha_matricula = fecha_matricula
        self.anio_escolar = anio_escolar
        self.estado = estado
        self.codigo_matricula = codigo_matricula

    def guardar(self):
        """Guardar nueva matrícula en la base de datos y generar código automático"""
        try:
            print(f"🔍 INICIANDO GUARDADO DE MATRÍCULA")
            print(f"🔍 Datos: alumno_id={self.alumno_id}, grupo_id={self.grupo_id}, anio_escolar={self.anio_escolar}")
            
            # 1️⃣ Primero insertamos la matrícula básica
            query = """
            INSERT INTO matriculas (alumno_id, grupo_id, fecha_matricula, anio_escolar, estado, permite_login)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (self.alumno_id, self.grupo_id, self.fecha_matricula, 
                     self.anio_escolar, self.estado, True)
            
            print(f"🔍 Ejecutando query de inserción...")
            resultado = db.execute_query(query, params)
            
            if not resultado:
                print("❌ No se pudo insertar la matrícula")
                return False

            # 2️⃣ Obtener el ID de la matrícula recién insertada
            get_id_query = "SELECT LAST_INSERT_ID() as id"
            id_result = db.fetch_one(get_id_query)
            
            if not id_result:
                print("❌ No se pudo obtener el ID de la matrícula insertada")
                return False

            matricula_id = id_result['id']
            print(f"🔍 ID de matrícula obtenido: {matricula_id}")

            # 3️⃣ Buscar los datos del alumno para generar las iniciales
            alumno_query = "SELECT nombre, apellido FROM alumnos WHERE id = %s"
            alumno_data = db.fetch_one(alumno_query, (self.alumno_id,))
            
            if not alumno_data:
                print("❌ No se encontró el alumno con ID:", self.alumno_id)
                return False

            # 4️⃣ Generar código con iniciales
            nombre_completo = alumno_data['nombre'].strip()
            apellido_completo = alumno_data['apellido'].strip()
            
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

            # 5️⃣ Crear código final
            codigo = f"{iniciales}-{self.anio_escolar}-{self.alumno_id}-{matricula_id}"
            print(f"🔍 Código generado: {codigo}")

            # 6️⃣ Actualizar la matrícula con el código
            update_query = "UPDATE matriculas SET codigo_matricula = %s WHERE id = %s"
            resultado_update = db.execute_query(update_query, (codigo, matricula_id))
            
            if resultado_update:
                # 7️⃣ GENERAR USUARIO AUTOMÁTICAMENTE
                usuario_creado = Usuario.generar_usuario_estudiante(matricula_id, codigo)
                
                if usuario_creado:
                    print(f"✅ Matrícula y usuario creados exitosamente con código: {codigo}")
                else:
                    print(f"⚠️ Matrícula creada pero falló la creación de usuario: {codigo}")
                
                return True
            else:
                print("❌ Falló la actualización del código")
                return False

        except Exception as e:
            print(f"❌ ERROR guardando matrícula: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def obtener_todas():
        """Obtener todas las matrículas con información de alumnos y grupos"""
        try:
            query = """
            SELECT m.*, a.nombre AS alumno_nombre, a.apellido AS alumno_apellido,
                   g.nombre AS grupo_nombre, g.grado AS grupo_grado
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN grupos g ON m.grupo_id = g.id
            ORDER BY m.fecha_matricula DESC
            """
            return db.fetch_all(query)
        except Exception as e:
            print(f"❌ Error obteniendo matrículas: {e}")
            return []

    @staticmethod
    def obtener_por_alumno(alumno_id):
        """Obtener matrículas de un alumno específico"""
        try:
            query = """
            SELECT m.*, g.nombre AS grupo_nombre, g.grado
            FROM matriculas m
            LEFT JOIN grupos g ON m.grupo_id = g.id
            WHERE m.alumno_id = %s
            ORDER BY m.anio_escolar DESC
            """
            return db.fetch_all(query, (alumno_id,))
        except Exception as e:
            print(f"❌ Error obteniendo matrículas del alumno: {e}")
            return []

    @staticmethod
    def obtener_por_grupo(grupo_id):
        """Obtener matrículas de un grupo específico"""
        try:
            query = """
            SELECT m.*, a.nombre AS alumno_nombre, a.apellido AS alumno_apellido
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            WHERE m.grupo_id = %s AND m.estado = 'Activa'
            """
            return db.fetch_all(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error obteniendo matrículas del grupo: {e}")
            return []

    @staticmethod
    def obtener_por_id(matricula_id):
        """Obtener matrícula por ID"""
        try:
            query = """
            SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido,
                   g.nombre as grupo_nombre, g.grado as grupo_grado
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            LEFT JOIN grupos g ON m.grupo_id = g.id
            WHERE m.id = %s
            """
            return db.fetch_one(query, (matricula_id,))
        except Exception as e:
            print(f"❌ Error obteniendo matrícula por ID: {e}")
            return None

    @staticmethod
    def actualizar_estado(matricula_id, estado):
        """Actualizar estado de una matrícula"""
        try:
            query = "UPDATE matriculas SET estado = %s WHERE id = %s"
            return db.execute_query(query, (estado, matricula_id))
        except Exception as e:
            print(f"❌ Error actualizando estado de matrícula: {e}")
            return False

    @staticmethod
    def actualizar(matricula_id, grupo_id, anio_escolar, estado):
        """Actualizar matrícula existente"""
        try:
            query = """
            UPDATE matriculas 
            SET grupo_id = %s, anio_escolar = %s, estado = %s 
            WHERE id = %s
            """
            params = (grupo_id, anio_escolar, estado, matricula_id)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error actualizando matrícula: {e}")
            return False

    @staticmethod
    def eliminar(matricula_id):
        """Eliminar matrícula"""
        try:
            query = "DELETE FROM matriculas WHERE id = %s"
            return db.execute_query(query, (matricula_id,))
        except Exception as e:
            print(f"❌ Error eliminando matrícula: {e}")
            return False

    @staticmethod
    def obtener_matricula_activa(alumno_id, grupo_id):
        """Obtener matrícula activa de un alumno en un grupo"""
        try:
            query = """
            SELECT * FROM matriculas 
            WHERE alumno_id = %s AND grupo_id = %s AND estado = 'Activa'
            """
            return db.fetch_one(query, (alumno_id, grupo_id))
        except Exception as e:
            print(f"❌ Error obteniendo matrícula activa: {e}")
            return None


class Usuario:
    def __init__(self, id=None, matricula_id=None, username=None, password_hash=None, 
                 rol=None, fecha_creacion=None, ultimo_login=None, activo=True):
        self.id = id
        self.matricula_id = matricula_id
        self.username = username
        self.password_hash = password_hash
        self.rol = rol
        self.fecha_creacion = fecha_creacion
        self.ultimo_login = ultimo_login
        self.activo = activo

    @staticmethod
    def hash_password(password):
        """Generar hash de contraseña"""
        try:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        except Exception as e:
            print(f"❌ Error hashing password: {e}")
            return None

    def verificar_password(self, password):
        """Verificar contraseña"""
        try:
            if not self.password_hash:
                print("❌ No hay password_hash para verificar")
                return False
            
            # Verificar que el hash parece ser un hash bcrypt válido
            if not self.password_hash.startswith('$2b$') and not self.password_hash.startswith('$2a$') and not self.password_hash.startswith('$2y$'):
                print(f"❌ Hash no parece ser bcrypt válido: {self.password_hash[:10]}...")
                return False
                
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception as e:
            print(f"❌ Error verificando password: {e}")
            print(f"🔍 Hash problemático: {self.password_hash}")
            return False

    @staticmethod
    def crear_usuario(username, password, rol='estudiante', matricula_id=None):
        """Crear nuevo usuario"""
        try:
            password_hash = Usuario.hash_password(password)
            if not password_hash:
                return False
                
            query = """
            INSERT INTO usuarios (username, password_hash, rol, matricula_id)
            VALUES (%s, %s, %s, %s)
            """
            params = (username, password_hash, rol, matricula_id)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error creando usuario: {e}")
            return False

    @staticmethod
    def obtener_por_username(username):
        """Obtener usuario por nombre de usuario"""
        try:
            query = "SELECT * FROM usuarios WHERE username = %s AND activo = TRUE"
            result = db.fetch_one(query, (username,))
            if result:
                return Usuario(**result)
            return None
        except Exception as e:
            print(f"❌ Error obteniendo usuario: {e}")
            return None

    @staticmethod
    def obtener_por_matricula(matricula_id):
        """Obtener usuario por ID de matrícula"""
        try:
            query = "SELECT * FROM usuarios WHERE matricula_id = %s AND activo = TRUE"
            result = db.fetch_one(query, (matricula_id,))
            if result:
                return Usuario(**result)
            return None
        except Exception as e:
            print(f"❌ Error obteniendo usuario por matrícula: {e}")
            return None

    def actualizar_ultimo_login(self):
        """Actualizar fecha de último login"""
        try:
            query = "UPDATE usuarios SET ultimo_login = %s WHERE id = %s"
            return db.execute_query(query, (datetime.now(), self.id))
        except Exception as e:
            print(f"❌ Error actualizando último login: {e}")
            return False

    @staticmethod
    def generar_usuario_estudiante(matricula_id, codigo_matricula):
        """Generar usuario automáticamente para estudiante"""
        try:
            # Verificar si ya existe
            usuario_existente = Usuario.obtener_por_matricula(matricula_id)
            if usuario_existente:
                print(f"✅ Usuario ya existe para matrícula {matricula_id}")
                return True

            # Crear nuevo usuario
            resultado = Usuario.crear_usuario(
                username=codigo_matricula,
                password=codigo_matricula,  # Mismo código como contraseña
                rol='estudiante',
                matricula_id=matricula_id
            )
            
            if resultado:
                print(f"✅ Usuario estudiante creado: {codigo_matricula}")
            else:
                print(f"❌ Error creando usuario estudiante: {codigo_matricula}")
                
            return resultado
            
        except Exception as e:
            print(f"❌ Error generando usuario estudiante: {e}")
            return False

    @staticmethod
    def crear_usuario_admin():
        """Crear usuario admin por defecto si no existe"""
        try:
            # Verificar si ya existe el usuario admin
            admin = Usuario.obtener_por_username('admin')
            if not admin:
                print("🔧 Creando usuario admin por defecto...")
                
                # Crear usuario admin
                resultado = Usuario.crear_usuario('admin', 'admin123', 'admin')
                
                if resultado:
                    print("✅ Usuario admin creado exitosamente")
                    print("🔑 Credenciales: usuario: admin, contraseña: admin123")
                else:
                    print("❌ Error creando usuario admin")
            else:
                print("✅ Usuario admin ya existe")
                
        except Exception as e:
            print(f"❌ Error creando usuario admin: {e}")