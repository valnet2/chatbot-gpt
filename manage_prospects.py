# manage_prospects.py
from chat_manager import ConversationManager
import datetime

def main():
    # No necesitamos el prompt_path para esta operación específica,
    # pero la clase lo requiere. Podemos pasar el default.
    try:
        conv_manager = ConversationManager()
        print("Conectado a la base de datos y ConversationManager inicializado.")
    except Exception as e:
        print(f"Error al inicializar ConversationManager: {e}")
        return

    print("\n--- Insertar o Actualizar Prospecto ---")
    user_id = input("User ID (ej: 521XXXXXXXXXX@s.whatsapp.net): ").strip()
    if not user_id:
        print("El User ID es obligatorio.")
        return

    nombre = input("Nombre (dejar vacío para no cambiar): ").strip() or None
    telefono = input("Teléfono (dejar vacío para no cambiar): ").strip() or None
    email = input("Email (dejar vacío para no cambiar): ").strip() or None
    etapa_embudo = input("Etapa del Embudo (dejar vacío para no cambiar): ").strip() or None
    notas_agente = input("Notas del Agente (dejar vacío para no cambiar): ").strip() or None
    promo_aplicada = input("Promo Aplicada (dejar vacío para no cambiar): ").strip() or None
    
    clase_muestra_agendada_str = input("Fecha Clase Muestra (YYYY-MM-DD HH:MM:SS, dejar vacío para no cambiar): ").strip()
    clase_muestra_agendada_dt = None
    if clase_muestra_agendada_str:
        try:
            # Se convierte a objeto datetime y luego a string ISO para consistencia con lo que espera la DB
            clase_muestra_agendada_dt = datetime.datetime.fromisoformat(clase_muestra_agendada_str).isoformat()
        except ValueError:
            print("Formato de fecha inválido. Se ignorará la fecha de clase muestra.")

    asistio_clase_str = input("¿Asistió a Clase Muestra? (si/no, dejar vacío para no cambiar): ").strip().lower()
    asistio_clase_muestra = None
    if asistio_clase_str == 'si':
        asistio_clase_muestra = True
    elif asistio_clase_str == 'no':
        asistio_clase_muestra = False

    print(f"\nIntentando guardar/actualizar prospecto: {user_id}")
    
    try:
        resultado = conv_manager.add_or_update_prospect(
            user_id=user_id,
            nombre=nombre,
            telefono=telefono,
            email=email,
            etapa_embudo=etapa_embudo,
            notas_agente=notas_agente,
            promo_aplicada=promo_aplicada,
            clase_muestra_agendada_dt=clase_muestra_agendada_dt,
            asistio_clase_muestra=asistio_clase_muestra
        )
        if resultado:
            print("\n--- Prospecto Guardado/Actualizado Exitosamente ---")
            for key, value in resultado.items():
                print(f"{key}: {value}")
        else:
            print("\n--- Hubo un problema al guardar/actualizar el prospecto. ---")
            print("Revisa los logs de chat_manager.py si hay DEBUG prints.")

    except Exception as e:
        print(f"Error durante la operación: {e}")
    finally:
        if hasattr(conv_manager, 'db_conn') and conv_manager.db_conn:
            conv_manager.db_conn.close()
            print("\nConexión a la base de datos cerrada.")


if __name__ == "__main__":
    main()