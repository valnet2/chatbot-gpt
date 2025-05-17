import os
from flask import Flask, send_from_directory

# --- Inicio de Configuración de Rutas ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# La carpeta 'static' debe estar al mismo nivel que este app.py
STATIC_DIR = os.path.join(BASE_DIR, 'static')
CONSOLE_SUBDIR = 'console' # Subdirectorio dentro de 'static'
CONSOLE_ABS_DIR = os.path.join(STATIC_DIR, CONSOLE_SUBDIR)
# --- Fin de Configuración de Rutas ---

print(f"--- MINIMAL DEBUG: BASE_DIR: {BASE_DIR}")
print(f"--- MINIMAL DEBUG: STATIC_DIR (usado para Flask): {STATIC_DIR}")
print(f"--- MINIMAL DEBUG: CONSOLE_ABS_DIR (para servir archivos): {CONSOLE_ABS_DIR}")

app = Flask(__name__, static_folder=STATIC_DIR) # Flask usará STATIC_DIR para su manejo de estáticos general

@app.route("/")
def hello():
    print("--- MINIMAL DEBUG: Ruta '/' accedida.")
    return "¡Hola desde Flask Mínimo!"

@app.route("/console")
def serve_console_minimal():
    print(f"--- MINIMAL DEBUG: Ruta '/console' accedida.")
    index_file_path = os.path.join(CONSOLE_ABS_DIR, 'index.html')
    print(f"--- MINIMAL DEBUG: Intentando servir index.html desde: {index_file_path}")
    
    if not os.path.isdir(CONSOLE_ABS_DIR):
        print(f"--- MINIMAL ERROR: El directorio de la consola NO EXISTE: {CONSOLE_ABS_DIR}")
        return "Error: Directorio de consola no encontrado en el servidor.", 500
    
    if not os.path.isfile(index_file_path):
        print(f"--- MINIMAL ERROR: index.html NO ENCONTRADO en: {index_file_path}")
        return "Error: Archivo index.html de la consola no encontrado.", 404
        
    print(f"--- MINIMAL DEBUG: Sirviendo index.html desde {CONSOLE_ABS_DIR}")
    return send_from_directory(CONSOLE_ABS_DIR, 'index.html')

@app.route('/console/<path:filename>')
def serve_console_static_minimal(filename):
    print(f"--- MINIMAL DEBUG: Ruta '/console/{filename}' accedida.")
    file_path = os.path.join(CONSOLE_ABS_DIR, filename)
    print(f"--- MINIMAL DEBUG: Intentando servir archivo estático: {file_path}")

    if not os.path.isfile(file_path):
        print(f"--- MINIMAL ERROR: Archivo estático '{filename}' NO ENCONTRADO en: {CONSOLE_ABS_DIR}")
        return f"Error: Archivo estático '{filename}' no encontrado.", 404

    print(f"--- MINIMAL DEBUG: Sirviendo archivo estático '{filename}' desde {CONSOLE_ABS_DIR}")
    return send_from_directory(CONSOLE_ABS_DIR, filename)

if __name__ == "__main__":
    print("--- MINIMAL DEBUG: Iniciando servidor Flask Mínimo...")
    # debug=True puede dar más información en el navegador si hay errores Python
    app.run(host="0.0.0.0", port=5000, debug=True)
