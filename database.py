import mysql.connector
from mysql.connector import Error

class Database:
    def __init__(self):
        self.host = 'localhost'
        self.database = 'sistema_alumnos'
        self.user = 'root'
        self.password = ''
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establecer conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor(dictionary=True)
            print("✅ Conexión a la base de datos establecida")
            return True
        except Error as e:
            print(f"❌ Error conectando a la base de datos: {e}")
            return False
    
    def get_connection(self):
        """Método alternativo para obtener conexión (para compatibilidad)"""
        return self.connect()
    
    def execute_query(self, query, params=None):
        """Ejecutar consultas INSERT, UPDATE, DELETE"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                result = self.cursor.fetchall()
            else:
                self.connection.commit()
                result = True
            
            print(f"✅ Query ejecutada: {query}")
            return result
        except Error as e:
            print(f"❌ Error en execute_query: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def fetch_all(self, query, params=None):
        """Obtener todos los resultados de una consulta SELECT"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            result = self.cursor.fetchall()
            return result
        except Error as e:
            print(f"❌ Error en fetch_all: {e}")
            return []
    
    def fetch_one(self, query, params=None):
        """Obtener un solo resultado de una consulta SELECT"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            result = self.cursor.fetchone()
            return result
        except Error as e:
            print(f"❌ Error en fetch_one: {e}")
            return None
    
    def insert_and_get_id(self, query, values):
        """Ejecuta una consulta INSERT y retorna el ID del registro insertado"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            print(f"📝 Ejecutando INSERT: {query}")
            print(f"📝 Valores: {values}")
            self.cursor.execute(query, values)
            self.connection.commit()
            last_id = self.cursor.lastrowid
            print(f"📝 ID obtenido: {last_id}")
            return last_id
        except Exception as e:
            print(f"❌ ERROR en insert_and_get_id: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def initialize_database(self):
        """Inicializar la base de datos con las tablas necesarias"""
        try:
            # Primero conectamos sin especificar base de datos para crearla
            temp_connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            temp_cursor = temp_connection.cursor()
            
            # Crear base de datos si no existe
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            temp_cursor.execute(f"USE {self.database}")
            
            # Tabla de Alumnos
            temp_cursor.execute("""
                CREATE TABLE IF NOT EXISTS alumnos (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nombre VARCHAR(100) NOT NULL,
                    apellido VARCHAR(100) NOT NULL,
                    fecha_nacimiento DATE NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    telefono VARCHAR(15),
                    direccion TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de Grupos
            temp_cursor.execute("""
                CREATE TABLE IF NOT EXISTS grupos (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nombre VARCHAR(50) NOT NULL,
                    grado VARCHAR(20) NOT NULL,
                    turno ENUM('Matutino', 'Vespertino', 'Nocturno') NOT NULL,
                    capacidad INT DEFAULT 30,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de Horarios
            temp_cursor.execute("""
                CREATE TABLE IF NOT EXISTS horarios (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    grupo_id INT,
                    dia_semana ENUM('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'),
                    hora_inicio TIME NOT NULL,
                    hora_fin TIME NOT NULL,
                    materia VARCHAR(100) NOT NULL,
                    profesor VARCHAR(100) NOT NULL,
                    FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla de Matrículas (ACTUALIZADA con codigo_matricula y anio_escolar)
            temp_cursor.execute("""
                CREATE TABLE IF NOT EXISTS matriculas (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    codigo_matricula VARCHAR(50),
                    alumno_id INT,
                    grupo_id INT,
                    fecha_matricula DATE NOT NULL,
                    anio_escolar YEAR NOT NULL,
                    estado ENUM('Activa', 'Inactiva', 'Graduado') DEFAULT 'Activa',
                    FOREIGN KEY (alumno_id) REFERENCES alumnos(id) ON DELETE CASCADE,
                    FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE SET NULL
                )
            """)
            
            temp_connection.commit()
            temp_cursor.close()
            temp_connection.close()
            
            # Ahora conectamos a la base de datos específica
            self.connect()
            
            print("✅ Base de datos inicializada correctamente")
            return True
            
        except Error as e:
            print(f"❌ Error inicializando base de datos: {e}")
            return False
    
    def close(self):
        """Cerrar la conexión a la base de datos"""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("✅ Conexión a la base de datos cerrada")
    
    def __enter__(self):
        """Support for context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager"""
        self.close()