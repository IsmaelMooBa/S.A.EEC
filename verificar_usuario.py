import sys
import os

# Añade el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Usuario

def verificar_clase_usuario():
    print("🔍 VERIFICANDO CLASE USUARIO...")
    
    # Verificar los parámetros del constructor
    import inspect
    signature = inspect.signature(Usuario.__init__)
    print(f"📋 Parámetros de Usuario.__init__: {list(signature.parameters.keys())}")
    
    # Verificar si maestro_id está en los parámetros
    params = list(signature.parameters.keys())
    if 'maestro_id' in params:
        print("✅ maestro_id está en el constructor de Usuario")
    else:
        print("❌ maestro_id NO está en el constructor de Usuario")
        print("📋 Parámetros actuales:", params)
    
    # Testear creación de instancia
    try:
        usuario_test = Usuario(
            id=1,
            username='test',
            password_hash='test',
            rol='admin',
            matricula_id=None,
            maestro_id=None  # ← Probar con maestro_id
        )
        print("✅ Se puede crear instancia Usuario con maestro_id")
    except Exception as e:
        print(f"❌ Error creando instancia: {e}")

if __name__ == "__main__":
    verificar_clase_usuario()