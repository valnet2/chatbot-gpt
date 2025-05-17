# __version__ = "mayo 10 15:45 2025" # BOT CON CONSOLA DE CONTROL HUMANO
# print(f"🟢 Iniciando app.py versión {__version__}")

import os
from flask import Flask, request, jsonify, send_from_directory, abort  # Añadido abort
from dotenv import load_dotenv
from chat_manager import ConversationManager

load_dotenv()

# --- Configuración de Rutas para la Consola ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
CONSOLE_SUBDIR = 'console'
CONSOLE_ABS_DIR = os.path.join(STATIC_DIR, CONSOLE_SUBDIR)
# --- Fin Configuración ---

app = Flask(__name__)  # Inicialización simple de Flask


# --- Rutas para la Consola de Intervención ---
# Se sirven ANTES de inicializar ConversationManager por si acaso
@app.route("/console_ui")  # Usamos esta ruta más descriptiva
def serve_console_html_final():
    # print(f"--- CONSOLE FINAL: Ruta '/console_ui' accedida. Intentando servir index.html.") # Comentado para producción
    # print(f"--- CONSOLE FINAL: Sirviendo index.html desde: {CONSOLE_ABS_DIR}") # Comentado para producción
    index_path = os.path.join(CONSOLE_ABS_DIR, 'index.html')
    if not os.path.isfile(index_path):
        # print(f"--- CONSOLE FINAL: ERROR - index.html NO ENCONTRADO en {CONSOLE_ABS_DIR}") # Comentado, abort lo maneja
        abort(404, description="index.html para la consola no encontrado.")
    return send_from_directory(CONSOLE_ABS_DIR, 'index.html')


@app.route('/console_assets/<path:filename>')
def serve_console_assets_final(filename):
    # print(f"--- CONSOLE FINAL: Ruta '/console_assets/{filename}' accedida. Intentando servir asset.") # Comentado para producción
    # print(f"--- CONSOLE FINAL: Sirviendo asset '{filename}' desde: {CONSOLE_ABS_DIR}") # Comentado para producción
    file_path = os.path.join(CONSOLE_ABS_DIR, filename)
    if not os.path.isfile(file_path):
        # print(f"--- CONSOLE FINAL: ERROR - Asset '{filename}' NO ENCONTRADO en {CONSOLE_ABS_DIR}") # Comentado, abort lo maneja
        abort(404, description=f"Asset {filename} para la consola no encontrado.")
    return send_from_directory(CONSOLE_ABS_DIR, filename)
# --- Fin Rutas Consola ---

# --- Lógica Principal de la Aplicación ---
# Le decimos dónde está tu prompt maestro
try:
    conv_manager = ConversationManager(prompt_path="system_prompt.txt")
    # print("--- DEBUG: ConversationManager initialized successfully.") # Comentado para producción
except FileNotFoundError:
    print(
        f"🚨 FATAL ERROR: system_prompt.txt no encontrado. El bot NO funcionará sin él.")
    conv_manager = None
except Exception as e:
    print(f"🚨 FATAL ERROR: No se pudo inicializar ConversationManager: {e}")
    conv_manager = None

# --- Rutas de API Originales (Reactivando todas) ---
@app.route("/gpt", methods=["POST"])
def chat():
    if not conv_manager:
        return jsonify({"error": "Error interno crítico: ConversationManager no inicializado."}), 500
    data = request.json
    user_id = data.get("from")
    user_message = data.get("message", "")
    user_message_lower = user_message.lower()
    
    # Obtener el prospecto
    prospect = conv_manager.get_prospect(user_id)
    
    # Enviar saludo solo si es un usuario conocido y no se ha enviado el saludo
    if prospect and prospect.get("nombre") and not prospect.get("saludo_enviado", False):
        name = prospect.get("nombre")
        # Actualizar el prospecto para marcar que el saludo ha sido enviado
        conv_manager.add_or_update_prospect(user_id, saludo_enviado=True)
        greeting = f"¡Hola {name}! "
    else:
        greeting = ""
    
    # Obtener la respuesta del modelo de lenguaje
    reply = conv_manager.get_reply(user_id, user_message)
    
    # Si no hay respuesta del modelo y el humano no está activo
    if reply is None and not conv_manager.is_human_active.get(user_id, False):
        reply = "Lo siento, no pude procesar tu mensaje en este momento."
    
    # Asegurarnos de que el saludo esté al inicio si existe
    if greeting:
        reply = greeting + reply
    return jsonify({"reply": reply})


@app.route("/human_intervention", methods=["POST"])
def human_intervention():
    if not conv_manager:
         return jsonify({"error": "Error interno crítico: ConversationManager no inicializado."}), 500
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id es requerido"}), 400
    conv_manager.mark_human_takeover(user_id)  # Silencia el bot para este usuario
    conv_manager.add_to_human_request_list(
        user_id)  # Asegura que aparezca en la lista de espera
    print(f"🤖 Human takeover marked for user: {user_id} by console/API.")
    return jsonify({"status": "human_takeover_marked", "user_id": user_id})


@app.route("/bot_intervention", methods=["POST"])
def bot_intervention():
    if not conv_manager:
         return jsonify({"error": "Error interno crítico: ConversationManager no inicializado."}), 500
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id es requerido"}), 400
    conv_manager.mark_bot_intervention(user_id)
    print(f"🤖 Bot intervention marked for user: {user_id}")
    return jsonify({"status": "bot_intervention_marked", "user_id": user_id})


@app.route("/reset_chat", methods=["POST"])
def reset_chat_endpoint():
    if not conv_manager:
         return jsonify({"error": "Error interno crítico: ConversationManager no inicializado."}), 500
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id es requerido"}), 400
    conv_manager.reset(user_id)
    print(f"🔄 Chat reset for user: {user_id}")
    return jsonify({"status": "chat_reset_and_bot_activated", "user_id": user_id})


@app.route("/waiting_users", methods=["GET"])
def get_waiting_users():
    if not conv_manager:
        # print("--- DEBUG: /waiting_users called but conv_manager is None. Returning empty list.") # Comentado para producción
        return jsonify({"waiting_users": []})  # Devuelve lista vacía si conv_manager no se inicializó
    users = conv_manager.get_users_waiting_for_human()
    return jsonify({"waiting_users": users})  # Reactivado


@app.route("/get_prospect_list", methods=["GET"])
def get_prospect_list_route():
    if not conv_manager:
        return jsonify({"error": "ConversationManager no inicializado."}), 500

    try:
        prospects = conv_manager.get_all_prospects_summary()
        return jsonify({"prospects": prospects})
    except Exception as e:
        print(f"❌ Error en get_prospect_list_route: {e}")
        return jsonify({"error": "Error interno al obtener lista de prospectos."}), 500
# # --- Fin Rutas API Originales ---


@app.route("/update_prospect_name", methods=["POST"])
def update_prospect_name():
    if not conv_manager:
         return jsonify({"error": "Error interno crítico: ConversationManager no inicializado."}), 500
    data = request.json
    user_id = data.get("user_id")
    nombre = data.get("nombre")

    if not user_id or not nombre:
        return jsonify({"error": "user_id y nombre son requeridos"}), 400

    try:
        if conv_manager.update_prospect_name(user_id, nombre):
            return jsonify({"status": "nombre de prospecto actualizado", "user_id": user_id, "nombre": nombre})
        else:
            return jsonify({"error": "Error al actualizar el nombre del prospecto."}), 500
    except Exception as e:
        print(
            f"❌ Error al actualizar el nombre del prospecto para user_id {user_id}: {e}")
        return jsonify({"error": "Error interno al actualizar el nombre del prospecto."}), 500


if __name__ == "__main__":
    print("--- Iniciando servidor Flask ---")
    # Para producción real, NO uses app.run(). Usa un servidor WSGI como Gunicorn o Waitress.
    # Ejemplo: gunicorn --bind 0.0.0.0:5000 app:app
    # Si DEBES usar app.run() para una prueba rápida en Contabo (no recomendado para carga real):
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False, use_reloader=False)
