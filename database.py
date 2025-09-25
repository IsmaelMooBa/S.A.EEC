import mysql.connector
from mysql.connector import Error

class Database:
    def __init__(self):
        self.host = 'localhost'
        self.database = 'sistema_alumnos'
        self.user = 'root'
        self.password = ''
    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return connection
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None
    
    def execute_query(self, query, params=None):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, params or ())
                
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                else:
                    connection.commit()
                    result = cursor.lastrowid
                
                cursor.close()
                connection.close()
                return result
            except Error as e:
                print(f"Error ejecutando query: {e}")
                return None
        return None

    def initialize_database(self):
        """Crear la base de datos y tablas si no existen"""
        try:
            # Primero conectamos sin especificar base de datos para crearla
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = connection.cursor()
            
            # Crear base de datos si no existe
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            # Tabla de Alumnos
            cursor.execute("""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grupos (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nombre VARCHAR(50) NOT NULL,
                    grado VARCHAR(20) NOT NULL,
                    turno ENUM('Matutino', 'Vespertino', 'Nocturno') NOT NULL,
                    capacidad INT DEFAULT 30
                )
            """)
            
            # Tabla de Horarios
            cursor.execute("""
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
            
            # Tabla de Matrículas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matriculas (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    alumno_id INT,
                    grupo_id INT,
                    fecha_matricula DATE NOT NULL,
                    año_escolar YEAR NOT NULL,
                    estado ENUM('Activa', 'Inactiva', 'Graduado') DEFAULT 'Activa',
                    FOREIGN KEY (alumno_id) REFERENCES alumnos(id) ON DELETE CASCADE,
                    FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE SET NULL
                )
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            print("Base de datos inicializada correctamente")
            
        except Error as e:
            print(f"Error inicializando base de datos: {e}")