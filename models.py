from database import Database
from datetime import datetime

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
            result = db.fetch_one(query, (alumno_id,))
            return result
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
            
            result = db.execute_query(query, params)
            return result is not None
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
        """Guardar nuevo grupo en la base de datos"""
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
        """Obtener todos los grupos"""
        try:
            query = "SELECT * FROM grupos ORDER BY grado, nombre"
            return db.fetch_all(query)
        except Exception as e:
            print(f"❌ Error obteniendo grupos: {e}")
            return []
    
    @staticmethod
    def obtener_por_id(grupo_id):
        """Obtener grupo por ID"""
        try:
            query = "SELECT * FROM grupos WHERE id = %s"
            result = db.fetch_one(query, (grupo_id,))
            return result
        except Exception as e:
            print(f"❌ Error obteniendo grupo por ID: {e}")
            return None
    
    def actualizar(self):
        """Actualizar grupo en la base de datos"""
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
        """Eliminar grupo de la base de datos"""
        try:
            query = "DELETE FROM grupos WHERE id = %s"
            return db.execute_query(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error eliminando grupo: {e}")
            return False
    
    @staticmethod
    def obtener_alumnos_por_grupo(grupo_id):
        """Obtener alumnos inscritos en un grupo específico"""
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
        """Guardar nuevo horario en la base de datos"""
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
        """Obtener horarios de un grupo específico"""
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
        """Eliminar horario de la base de datos"""
        try:
            query = "DELETE FROM horarios WHERE id = %s"
            return db.execute_query(query, (horario_id,))
        except Exception as e:
            print(f"❌ Error eliminando horario: {e}")
            return False

class Matricula:
    def __init__(self, id=None, alumno_id=None, grupo_id=None, fecha_matricula=None, 
                 año_escolar=None, estado=None):
        self.id = id
        self.alumno_id = alumno_id
        self.grupo_id = grupo_id
        self.fecha_matricula = fecha_matricula
        self.año_escolar = año_escolar
        self.estado = estado
    
    def guardar(self):
        """Guardar nueva matrícula en la base de datos"""
        try:
            query = """
            INSERT INTO matriculas (alumno_id, grupo_id, fecha_matricula, año_escolar, estado)
            VALUES (%s, %s, %s, %s, %s)
            """
            params = (self.alumno_id, self.grupo_id, self.fecha_matricula, 
                     self.año_escolar, self.estado)
            return db.execute_query(query, params)
        except Exception as e:
            print(f"❌ Error guardando matrícula: {e}")
            return False
    
    @staticmethod
    def obtener_todas():
        """Obtener todas las matrículas con información de alumnos y grupos"""
        try:
            query = """
            SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido, 
                   g.nombre as grupo_nombre, g.grado as grupo_grado
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
            SELECT m.*, g.nombre as grupo_nombre, g.grado
            FROM matriculas m
            LEFT JOIN grupos g ON m.grupo_id = g.id
            WHERE m.alumno_id = %s
            ORDER BY m.año_escolar DESC
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
            SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido
            FROM matriculas m
            JOIN alumnos a ON m.alumno_id = a.id
            WHERE m.grupo_id = %s AND m.estado = 'Activa'
            """
            return db.fetch_all(query, (grupo_id,))
        except Exception as e:
            print(f"❌ Error obteniendo matrículas del grupo: {e}")
            return []
    
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