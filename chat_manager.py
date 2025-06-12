import os
import sqlite3
import datetime
import time  # <--- Añadir importación de time
from collections import defaultdict
from dotenv import load_dotenv
import openai

load_dotenv()

DB_FILE = "chatbot_data.db"


def es_nombre_valido(mensaje):
    mensaje = mensaje.strip().lower()
    
    # Filtrar frases no válidas
    palabras_prohibidas = ["hola", "quiero", "información", "puedo", "cómo", "precio", "clase", "crossfit"]
    if any(p in mensaje for p in palabras_prohibidas):
        return False

    # Aceptar si tiene estructura de nombre
    if any(mensaje.startswith(p) for p in ["soy ", "me llamo ", "mi nombre es "]):
        return True

    # Aceptar si parece nombre sin conector
    if len(mensaje.split()) in [2, 3] and mensaje.replace(" ", "").isalpha():
        return True

    return False
class ConversationManager:
    def __init__(self, prompt_path="system_prompt.txt"):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.history = defaultdict(list)
        with open(prompt_path, encoding="utf-8") as f:
            self.system_prompt = f.read()
        self.max_turns = 20
        self.is_human_active = defaultdict(bool)
        self.users_requesting_human = set()
        self.db_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.db_conn.row_factory = sqlite3.Row
        self._create_prospects_table()  # Llamar al método de creación de tabla

    def _create_prospects_table(self):
        try:
            query = """
            CREATE TABLE IF NOT EXISTS prospectos (
                user_id TEXT PRIMARY KEY,
                nombre TEXT,
                telefono TEXT,
                email TEXT,
                etapa_embudo TEXT,
                fecha_creacion DATETIME,
                ultima_actualizacion DATETIME,
                notas_agente TEXT,
                promo_aplicada TEXT,
                clase_muestra_agendada_dt DATETIME,
                asistio_clase_muestra BOOLEAN DEFAULT FALSE,
                fecha_nacimiento TEXT,
                fecha_ingreso TEXT,
                fecha_corte TEXT,
                monto_pagan TEXT,
                saludo_enviado BOOLEAN DEFAULT FALSE,
                estado_membresia TEXT DEFAULT 'activo',
                motivo_cancelacion TEXT
            )
           """
            self._execute_query(query)
        except sqlite3.OperationalError as e:
            print(f"--- CHAT_MANAGER: La tabla 'prospectos' ya existe. Intentando agregar nuevas columnas...")
            try:
                cursor = self.db_conn.cursor()
                # Verificar si la columna ya existe antes de intentar agregarla
                cursor.execute("PRAGMA table_info(prospectos)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'saludo_enviado' not in columns:
                    cursor.execute("ALTER TABLE prospectos ADD COLUMN saludo_enviado BOOLEAN DEFAULT FALSE")
                    print("--- CHAT_MANAGER: Columna 'saludo_enviado' agregada exitosamente.")
                
                # Agregar otras columnas si no existen
                for column in ['fecha_nacimiento', 'fecha_ingreso', 'fecha_corte', 'monto_pagan']:
                    if column not in columns:
                        cursor.execute(f"ALTER TABLE prospectos ADD COLUMN {column} TEXT")
                
                self.db_conn.commit()
                print("--- CHAT_MANAGER: Todas las columnas necesarias han sido agregadas.")
            except sqlite3.Error as e2:
                print(f"--- CHAT_MANAGER: Error al agregar columnas: {e2}")
            except Exception as e:
                print(f"--- CHAT_MANAGER: Error al crear la tabla: {e}")

    def get_reply(self, user_id, user_message):
        # Primero, verificamos si el usuario existe en la base de datos
        prospect = self.get_prospect(user_id)

        if prospect and prospect.get('saludo_enviado', False):
            # Si ya tiene saludo, procedemos directamente con la respuesta
            return self.procesar_respuesta(user_id, user_message)
        else:
            if not prospect:
                # Si el usuario no existe, solicitamos el nombre
                if es_nombre_valido(user_message):
                    # Si el nombre es válido, lo guardamos y enviamos un saludo
                    self.add_or_update_prospect(user_id, nombre=user_message)
                    prospect = self.get_prospect(user_id)
                    system_prompt = self.system_prompt.replace("[Nombre del Usuario]", prospect.get('nombre'))
                    self.history[user_id].append({"role": "system", "content": system_prompt})
                    self.add_or_update_prospect(user_id, saludo_enviado=True)
                    return f"¡Hola {user_message}! Soy Froning, tu asistente virtual de CrossF4. ¿En qué puedo ayudarte?"
                else:
                    # Si el nombre no es válido, volvemos a solicitar el nombre
                    return "¡Hola! Soy Froning, tu asistente virtual de CrossF4. Para poder ofrecerte una atención más personalizada, ¿podrías decirme tu nombre completo, por favor?"
    
        # Si no tiene saludo, enviamos uno personalizado
        if prospect and prospect.get('nombre'):
            system_prompt = self.system_prompt.replace("[Nombre del Usuario]", prospect.get('nombre'))
            self.history[user_id].append({"role": "system", "content": system_prompt})
            self.add_or_update_prospect(user_id, saludo_enviado=True)
            return self.procesar_respuesta(user_id, user_message)
    
        return "¡Hola! Soy Froning, tu asistente virtual de CrossF4. ¿En qué puedo ayudarte?"

    def procesar_respuesta(self, user_id, user_message):
        if self.is_human_active[user_id]:
            return None

        prospect = self.get_prospect(user_id)
        if prospect and prospect.get('estado_membresia') == 'cancelado':
            return "Tu membresía está cancelada. No puedes realizar esta acción."

        # Detectar solicitud de cancelación
        if "cancelar membresía" in user_message.lower() or "quiero cancelar" in user_message.lower() or "no puedo asistir" in user_message.lower() or "estoy enfermo" in user_message.lower():
            motivo_cancelacion = user_message  # Usar el mensaje del usuario como motivo
            prospect = self.get_prospect(user_id)
            respuesta = "Lamentamos que desees cancelar tu membresía.\n"

            # Obtener el reglamento interno del system_prompt
            try:
                with open("system_prompt.txt", "r", encoding="utf-8") as f:
                    system_prompt = f.read()
                start_index = system_prompt.find("/////////////REGLAMENTO INTERNO DE CROSSF4/////////////")
                end_index = system_prompt.find("/////////////TERMNA FLUJO GESTORES DE ESTUDIOS O GIMNASIOS////////////////////")
                if start_index != -1 and end_index != -1:
                    reglamento = system_prompt[start_index:end_index]
                    respuesta += "Aquí está nuestro reglamento interno:\n" + reglamento + "\n"
                else:
                    respuesta += "No se encontró el reglamento interno. Por favor, contacta con soporte.\n"
            except FileNotFoundError:
                respuesta += "No se encontró el archivo system_prompt.txt. Por favor, contacta con soporte.\n"

            respuesta += "Si tienes alguna duda, házmelo saber. Un miembro de nuestro equipo revisará tu solicitud en breve.\n"

            if prospect:
                respuesta += f"Tenemos los siguientes datos de tu membresía: Nombre: {prospect.get('nombre', 'No disponible')}, Email: {prospect.get('email', 'No disponible')}.\n"
            else:
                respuesta += "No encontramos información de tu membresía en nuestra base de datos. Un miembro de nuestro equipo revisará tu solicitud.\n"

            # No cancelar la membresía automáticamente, sino esperar la revisión humana
            # if self.cancelar_membresia(user_id, motivo_cancelacion):
            #     respuesta += "Tu membresía ha sido cancelada. Lamentamos que te vayas."
            # else:
            #     respuesta += "Hubo un error al cancelar tu membresía. Por favor, contacta con soporte."

            return respuesta

        # Obtener el historial de conversación
        if not self.history[user_id]:
            prospect = self.get_prospect(user_id)
            if prospect and prospect.get('nombre'):
                system_prompt = self.system_prompt.replace("[Nombre del Usuario]", prospect.get('nombre'))
                self.history[user_id].append({"role": "system", "content": system_prompt})
    
        # Agregar el mensaje del usuario al historial
        self.history[user_id].append({"role": "user", "content": user_message})
    
        # Llamar al modelo de lenguaje
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.history[user_id],
                temperature=0.2,
                frequency_penalty=0.7,
                presence_penalty=0.3,
                max_tokens=250
            )
            reply = response.choices[0].message.content.strip()
        
            # Agregar la respuesta al historial
            self.history[user_id].append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"Error al obtener respuesta del modelo: {e}")
            return "Lo siento, no pude procesar tu mensaje en este momento."

    def _execute_query(self, query, params=()):
        cursor = self.db_conn.cursor()
        try:
            cursor.execute(query, params)
            self.db_conn.commit()
            return cursor
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            # Podrías querer re-lanzar la excepción o manejarla de otra forma
            return None  # O re-raise e

    def add_or_update_prospect(self, user_id, nombre=None, telefono=None, email=None,
                                etapa_embudo=None, promo_aplicada=None, notas_agente=None,
                                clase_muestra_agendada_dt=None, asistio_clase_muestra=None, saludo_enviado=None):
        print(f"--- CHAT_MANAGER DEBUG: add_or_update_prospect called for user_id: {user_id}")
        print(
            f"--- CHAT_MANAGER DEBUG: Provided nombre: {nombre}, etapa_embudo: {etapa_embudo}, saludo_enviado: {saludo_enviado}")
        now_iso = datetime.datetime.now().isoformat()
        existing_prospect = self.get_prospect(user_id)
        print(f"--- CHAT_MANAGER DEBUG: Existing prospect data: {existing_prospect}")

        fields_to_update = {}
        if nombre is not None:
            fields_to_update['nombre'] = nombre
        if telefono is not None:
            fields_to_update['telefono'] = telefono
        if email is not None:
            fields_to_update['email'] = email
        if etapa_embudo is not None:
            fields_to_update['etapa_embudo'] = etapa_embudo
        if promo_aplicada is not None:
            fields_to_update['promo_aplicada'] = promo_aplicada
        if notas_agente is not None:
            fields_to_update['notas_agente'] = notas_agente
        if clase_muestra_agendada_dt is not None:
            fields_to_update['clase_muestra_agendada_dt'] = clase_muestra_agendada_dt
        if asistio_clase_muestra is not None:
            fields_to_update['asistio_clase_muestra'] = asistio_clase_muestra
        if saludo_enviado is not None:
            fields_to_update['saludo_enviado'] = saludo_enviado

        fields_to_update['ultima_actualizacion'] = now_iso

        if existing_prospect:
            # Update existing prospect
            set_clauses = ", ".join(
                [f"{key} = ?" for key in fields_to_update.keys()])
            params = list(fields_to_update.values()) + [user_id]
            query = f"UPDATE prospectos SET {set_clauses} WHERE user_id = ?"
            print(
                f"--- CHAT_MANAGER DEBUG: Updating existing prospect. Query: {query}, Params: {tuple(params)}")
            self._execute_query(query, tuple(params))
        else:
            # Insert new prospect
            print(f"--- CHAT_MANAGER DEBUG: Inserting new prospect for user_id: {user_id}")
            fields_to_update['user_id'] = user_id
            fields_to_update['fecha_creacion'] = now_iso
            # Asegurar que todos los campos del schema estén presentes para la inserción,
            # usando None si no se proveyeron y no están en fields_to_update
            all_cols = ['user_id', 'nombre', 'telefono', 'email', 'etapa_embudo',
                        'fecha_creacion', 'ultima_actualizacion', 'notas_agente',
                        'promo_aplicada', 'clase_muestra_agendada_dt', 'asistio_clase_muestra', 'saludo_enviado']

            final_fields = {col: fields_to_update.get(col) for col in all_cols}
            # Si un valor es None y la columna no permite NULL (no es el caso aquí por ahora), se necesitaría un valor por defecto

            columns = ", ".join(final_fields.keys())
            placeholders = ", ".join(["?"] * len(final_fields))
            params = tuple(final_fields.values())
            query = f"INSERT INTO prospectos ({columns}) VALUES ({placeholders})"
            print(f"--- CHAT_MANAGER DEBUG: Insert query: {query}, Params: {params}")
            self._execute_query(query, params)

        # Verificar si se guardó/actualizó correctamente
        updated_prospect_check = self.get_prospect(user_id)
        print(
            f"--- CHAT_MANAGER DEBUG: Prospect data after add/update: {updated_prospect_check}")
        return updated_prospect_check

    def get_prospect(self, user_id):
        query = "SELECT * FROM prospectos WHERE user_id = ?"
        cursor = self._execute_query(query, (user_id,))
        if cursor:
            row = cursor.fetchone()
            return dict(row) if row else None
        return None

    def update_prospect_stage(self, user_id, nueva_etapa):
        return self.add_or_update_prospect(user_id, etapa_embudo=nueva_etapa)

    def get_all_prospects_in_stage(self, etapa_embudo):
        query = "SELECT * FROM prospectos WHERE etapa_embudo = ? ORDER BY ultima_actualizacion DESC"
        cursor = self._execute_query(query, (etapa_embudo,))
        if cursor:
            return [dict(row) for row in cursor.fetchall()]
        return []

    def get_all_prospects_summary(self, limit=100):  # Limitar para no sobrecargar la UI inicialmente
        """Devuelve un resumen de los prospectos (user_id, nombre, ultima_actualizacion) ordenados por nombre."""
        # Seleccionamos solo prospectos que tengan un nombre para que la lista sea útil.
        query = """
        SELECT user_id, nombre, ultima_actualizacion
        FROM prospectos
        WHERE nombre IS NOT NULL AND nombre != ''
        ORDER BY nombre ASC
        LIMIT ?
        """
        cursor = self._execute_query(query, (limit,))
        prospects = []
        if cursor:
            prospects = [dict(row) for row in cursor.fetchall()]
        print(
            f"--- CHAT_MANAGER: Getting prospects summary for console. Found: {len(prospects)}")
        return prospects

    def update_prospect_name(self, user_id, nombre):
        """Actualiza el nombre de un prospecto en la base de datos."""
        query = "UPDATE prospectos SET nombre = ? WHERE user_id = ?"
        cursor = self._execute_query(query, (nombre, user_id))
        if cursor:
            print(
                f"--- CHAT_MANAGER: Nombre de prospecto actualizado para user_id {user_id} a {nombre}")
            return True
        else:
            print(
                f"--- CHAT_MANAGER: Error al actualizar el nombre del prospecto para user_id {user_id}")
            return False

    def update_prospect(self, user_id, nombre=None, fecha_nacimiento=None, fecha_ingreso=None, fecha_corte=None, monto_pagan=None):
        """Actualiza la información de un prospecto en la base de datos."""
        query = "UPDATE prospectos SET nombre = ?, fecha_nacimiento = ?, fecha_ingreso = ?, fecha_corte = ?, monto_pagan = ? WHERE user_id = ?"
        cursor = self._execute_query(query, (nombre, fecha_nacimiento, fecha_ingreso, fecha_corte, monto_pagan, user_id))
        if cursor:
            print(
                f"--- CHAT_MANAGER: Información de prospecto actualizada para user_id {user_id}")
            return True
        else:
            print(
                f"--- CHAT_MANAGER: Error al actualizar la información del prospecto para user_id {user_id}")
            return False

    def cancelar_membresia(self, user_id, motivo_cancelacion):
        """Cancela la membresía de un prospecto."""
        query = "UPDATE prospectos SET estado_membresia = 'cancelado', motivo_cancelacion = ? WHERE user_id = ?"
        cursor = self._execute_query(query, (motivo_cancelacion, user_id))
        if cursor:
            print(
                f"--- CHAT_MANAGER: Membresía cancelada para user_id {user_id} con motivo: {motivo_cancelacion}")
            return True
        else:
            print(
                f"--- CHAT_MANAGER: Error al cancelar la membresía para user_id {user_id}")
            return False

    # --- Manejo de control de usuarios ---
    def mark_human_takeover(self, user_id):
        """Indica que un humano toma el control de la conversación."""
        self.is_human_active[user_id] = True

    def mark_bot_intervention(self, user_id):
        """Devuelve el control al bot y limpia la lista de espera."""
        self.is_human_active[user_id] = False
        self.users_requesting_human.discard(user_id)

    def add_to_human_request_list(self, user_id):
        """Añade al usuario a la lista de quienes esperan atención humana."""
        self.users_requesting_human.add(user_id)

    def get_users_waiting_for_human(self):
        """Devuelve una lista de usuarios que han solicitado atención humana."""
        return list(self.users_requesting_human)

    def reset(self, user_id):
        """Reinicia la conversación con un usuario."""
        self.history[user_id] = []
        self.is_human_active[user_id] = False
        self.users_requesting_human.discard(user_id)

    def __del__(self):
        # Asegurarse de cerrar la conexión a la DB cuando el objeto es destruido
        if hasattr(self, 'db_conn') and self.db_conn:
            self.db_conn.close()
