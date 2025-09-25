from database import Database
from datetime import datetime

db = Database()

class Alumno:
    def __init__(self, id=None, nombre=None, apellido=None, fecha_nacimiento=None, 
                 email=None, telefono=None, direccion=None):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.fecha_nacimiento = fecha_nacimiento
        self.email = email
        self.telefono = telefono
        self.direccion = direccion
    
    def guardar(self):
        query = """
        INSERT INTO alumnos (nombre, apellido, fecha_nacimiento, email, telefono, direccion)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (self.nombre, self.apellido, self.fecha_nacimiento, 
                 self.email, self.telefono, self.direccion)
        return db.execute_query(query, params)
    
    @staticmethod
    def obtener_todos():
        query = "SELECT * FROM alumnos ORDER BY apellido, nombre"
        return db.execute_query(query)
    
    @staticmethod
    def obtener_por_id(alumno_id):
        query = "SELECT * FROM alumnos WHERE id = %s"
        result = db.execute_query(query, (alumno_id,))
        return result[0] if result else None
    
    def actualizar(self):
        query = """
        UPDATE alumnos 
        SET nombre = %s, apellido = %s, fecha_nacimiento = %s, 
            email = %s, telefono = %s, direccion = %s 
        WHERE id = %s
        """
        params = (self.nombre, self.apellido, self.fecha_nacimiento,
                 self.email, self.telefono, self.direccion, self.id)
        return db.execute_query(query, params)
    
    @staticmethod
    def eliminar(alumno_id):
        query = "DELETE FROM alumnos WHERE id = %s"
        return db.execute_query(query, (alumno_id,))

class Grupo:
    def __init__(self, id=None, nombre=None, grado=None, turno=None, capacidad=None):
        self.id = id
        self.nombre = nombre
        self.grado = grado
        self.turno = turno
        self.capacidad = capacidad
    
    def guardar(self):
        query = """
        INSERT INTO grupos (nombre, grado, turno, capacidad)
        VALUES (%s, %s, %s, %s)
        """
        params = (self.nombre, self.grado, self.turno, self.capacidad)
        return db.execute_query(query, params)
    
    @staticmethod
    def obtener_todos():
        query = "SELECT * FROM grupos ORDER BY grado, nombre"
        return db.execute_query(query)
    
    @staticmethod
    def obtener_por_id(grupo_id):
        query = "SELECT * FROM grupos WHERE id = %s"
        result = db.execute_query(query, (grupo_id,))
        return result[0] if result else None
    
    def actualizar(self):
        query = """
        UPDATE grupos 
        SET nombre = %s, grado = %s, turno = %s, capacidad = %s 
        WHERE id = %s
        """
        params = (self.nombre, self.grado, self.turno, self.capacidad, self.id)
        return db.execute_query(query, params)
    
    @staticmethod
    def eliminar(grupo_id):
        query = "DELETE FROM grupos WHERE id = %s"
        return db.execute_query(query, (grupo_id,))
    
    @staticmethod
    def obtener_alumnos_por_grupo(grupo_id):
        query = """
        SELECT a.* FROM alumnos a
        JOIN matriculas m ON a.id = m.alumno_id
        WHERE m.grupo_id = %s AND m.estado = 'Activa'
        """
        return db.execute_query(query, (grupo_id,))

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
        query = """
        INSERT INTO horarios (grupo_id, dia_semana, hora_inicio, hora_fin, materia, profesor)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (self.grupo_id, self.dia_semana, self.hora_inicio, 
                 self.hora_fin, self.materia, self.profesor)
        return db.execute_query(query, params)
    
    @staticmethod
    def obtener_por_grupo(grupo_id):
        query = """
        SELECT * FROM horarios 
        WHERE grupo_id = %s 
        ORDER BY 
            FIELD(dia_semana, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'),
            hora_inicio
        """
        return db.execute_query(query, (grupo_id,))
    
    @staticmethod
    def eliminar(horario_id):
        query = "DELETE FROM horarios WHERE id = %s"
        return db.execute_query(query, (horario_id,))

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
        query = """
        INSERT INTO matriculas (alumno_id, grupo_id, fecha_matricula, año_escolar, estado)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (self.alumno_id, self.grupo_id, self.fecha_matricula, 
                 self.año_escolar, self.estado)
        return db.execute_query(query, params)
    
    @staticmethod
    def obtener_todas():
        query = """
        SELECT m.*, a.nombre as alumno_nombre, a.apellido as alumno_apellido, 
               g.nombre as grupo_nombre
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        LEFT JOIN grupos g ON m.grupo_id = g.id
        ORDER BY m.fecha_matricula DESC
        """
        return db.execute_query(query)
    
    @staticmethod
    def obtener_por_alumno(alumno_id):
        query = """
        SELECT m.*, g.nombre as grupo_nombre, g.grado
        FROM matriculas m
        LEFT JOIN grupos g ON m.grupo_id = g.id
        WHERE m.alumno_id = %s
        ORDER BY m.año_escolar DESC
        """
        return db.execute_query(query, (alumno_id,))
    
    @staticmethod
    def actualizar_estado(matricula_id, estado):
        query = "UPDATE matriculas SET estado = %s WHERE id = %s"
        return db.execute_query(query, (estado, matricula_id))