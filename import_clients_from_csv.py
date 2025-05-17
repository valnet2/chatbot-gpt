# import_clients_from_csv.py
import csv
import sqlite3
from chat_manager import ConversationManager 
import datetime

# --- CONFIGURACIÓN DE NOMBRES DE COLUMNA DEL CSV ---
CSV_COL_USER_ID = 'user_id' 
CSV_COL_NOMBRE = 'nombre'
CSV_COL_TELEFONO = 'Telefono' 
CSV_COL_EMAIL = 'Correo'      
CSV_COL_ETAPA_EMBUDO = 'ETAPA DE EMBUDO'
CSV_COL_FECHA_CREACION = 'FECHA DE CREACION'
CSV_COL_ULTIMA_ACTUALIZACION = 'ULTIMA ACTUALIZACION'
CSV_COL_NOTAS_AGENTE = 'NOTAS DE AGENTE'
CSV_COL_PROMO_APLICADA = 'PROMO APLICADA'
CSV_COL_CLASE_MUESTRA_DT = 'CLASE MUESTRA AGENDADA'
CSV_COL_ASISTIO_CLASE = 'ASISTIO CLASE MUESTRA'
CSV_COL_FECHA_NACIMIENTO_EXCEL = 'Fecha de nacimiento'

CSV_COL_GENERO = 'Género'
CSV_COL_DIRECCION = 'Dirección'
CSV_COL_CODIGO_POSTAL = 'Código postal'
CSV_COL_CIUDAD = 'Ciudad'
CSV_COL_PROVINCIA = 'Provincia'
CSV_COL_PAIS = 'País'
CSV_COL_FECHA_ALTA_EXCEL = 'Fecha de alta' 
CSV_COL_NOTAS_EXCEL = 'Notas' 

ASISTIO_TRUE_VALUES = ['si', 'sí', 'yes', 'true', '1', 'verdadero', 'VERDADERO']

def normalize_user_id(raw_id):
    if not raw_id:
        return None
    raw_id = str(raw_id).strip()
    if '@' not in raw_id:
        raw_id_digits = ''.join(filter(str.isdigit, raw_id))
        if raw_id_digits:
            return f"{raw_id_digits}@s.whatsapp.net"
        else:
            print(f"ADVERTENCIA: No se pudieron extraer dígitos del user_id: {raw_id}")
            return None 
    return raw_id

def parse_boolean(value_str):
    if isinstance(value_str, str):
        return value_str.strip().lower() in ASISTIO_TRUE_VALUES
    return bool(value_str)

def parse_datetime_iso(date_str):
    if not date_str or not str(date_str).strip():
        return None
    formats_to_try = [
        '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S',
        '%Y/%m/%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y',
        '%m/%d/%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S', '%m/%d/%Y'
    ]
    for fmt in formats_to_try:
        try:
            dt_obj = datetime.datetime.strptime(str(date_str).strip(), fmt)
            return dt_obj.isoformat()
        except ValueError:
            continue
    try: 
        return datetime.datetime.fromisoformat(str(date_str).strip().replace('Z', '+00:00')).isoformat()
    except ValueError:
        print(f"Advertencia: No se pudo parsear la fecha '{date_str}' a formato ISO. Se usará None.")
        return None

def import_clients(csv_filepath):
    try:
        conv_manager = ConversationManager()
        print("ConversationManager inicializado.")
    except Exception as e:
        print(f"Error al inicializar ConversationManager: {e}")
        return

    rows_to_process = []
    encodings_to_try = ['utf-8-sig', 'latin1', 'cp1252']
    file_opened_successfully = False

    for encoding in encodings_to_try:
        try:
            print(f"Intentando leer CSV con codificación: {encoding}...")
            with open(csv_filepath, mode='r', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                # Verificar si los encabezados son leídos correctamente
                if not reader.fieldnames:
                    print(f"ADVERTENCIA: No se detectaron encabezados con {encoding} o el archivo está vacío.")
                    # Si es utf-8-sig y falla por BOM pero es otro encoding, podría dar falso negativo aquí.
                    # Pero si es realmente un CSV vacío o sin encabezados, es un problema.
                    if encoding == encodings_to_try[-1]: # Si es el último intento
                         print("ERROR: No se pudieron leer los encabezados del CSV con ninguna codificación probada.")
                         return
                    continue # Intentar siguiente codificación

                print(f"Encabezados detectados en CSV con {encoding}: {reader.fieldnames}")
                
                # Leer todas las filas con esta codificación
                temp_rows = []
                for i, row in enumerate(reader):
                    temp_rows.append(dict(row))
                    if i < 2:
                        print(f"DEBUG: Fila {i+1} del CSV (con {encoding}): {row}")
                
                rows_to_process = temp_rows # Asignar si la lectura fue exitosa
                file_opened_successfully = True
                print(f"Archivo CSV leído exitosamente con codificación: {encoding}")
                break # Salir del bucle de encodings si la lectura fue exitosa
        except UnicodeDecodeError:
            print(f"Fallo al decodificar con {encoding}. Intentando siguiente...")
            if encoding == encodings_to_try[-1]: # Si fue el último intento
                print(f"Error leyendo el archivo CSV: Fallo al decodificar con todas las codificaciones probadas ({', '.join(encodings_to_try)}).")
                return
        except FileNotFoundError:
            print(f"Error: Archivo CSV no encontrado en '{csv_filepath}'")
            return
        except Exception as e:
            print(f"Error inesperado leyendo el archivo CSV con {encoding}: {e}")
            if encoding == encodings_to_try[-1]:
                 return
            # Continuar al siguiente encoding si hay otro error genérico, por si acaso.

    if not file_opened_successfully or not rows_to_process:
        print("No se pudieron leer datos del archivo CSV o el archivo está vacío.")
        return

    if not rows_to_process:
        print("No se encontraron filas para procesar en el CSV.")
        return

    print(f"\nSe encontraron {len(rows_to_process)} filas en el CSV. Iniciando importación/actualización...")
    count_added = 0
    count_updated = 0

    for row_idx, row_data in enumerate(rows_to_process):
        print(f"\nProcesando fila CSV {row_idx + 1}: {row_data}")
        user_id_raw = row_data.get(CSV_COL_USER_ID)
        user_id = normalize_user_id(user_id_raw)
        nombre = str(row_data.get(CSV_COL_NOMBRE, '')).strip()

        if not user_id:
            print(f"ADVERTENCIA: Saltando fila {row_idx + 1} por user_id vacío o inválido: '{user_id_raw}'")
            continue
        if not nombre:
            print(f"ADVERTENCIA: Saltando fila {row_idx + 1} para user_id '{user_id}' por falta de nombre.")
            continue

        db_data = {
            'nombre': nombre,
            'telefono': str(row_data.get(CSV_COL_TELEFONO, '')).strip() or None,
            'email': str(row_data.get(CSV_COL_EMAIL, '')).strip() or None,
            'etapa_embudo': str(row_data.get(CSV_COL_ETAPA_EMBUDO, 'CLIENTE_IMPORTADO')).strip(),
            'promo_aplicada': str(row_data.get(CSV_COL_PROMO_APLICADA, '')).strip() or None,
        }

        current_notes = str(row_data.get(CSV_COL_NOTAS_AGENTE, '')).strip()
        
        fn_excel = str(row_data.get(CSV_COL_FECHA_NACIMIENTO_EXCEL, '')).strip()
        if fn_excel:
            current_notes = (current_notes + f"\nFechaNacimiento_Excel: {fn_excel}").strip()

        extra_info_parts = []
        for csv_col, label in [
            (CSV_COL_GENERO, "Genero_Excel"), (CSV_COL_DIRECCION, "Direccion_Excel"),
            (CSV_COL_CODIGO_POSTAL, "CP_Excel"), (CSV_COL_CIUDAD, "Ciudad_Excel"),
            (CSV_COL_PROVINCIA, "Provincia_Excel"), (CSV_COL_PAIS, "Pais_Excel"),
            (CSV_COL_FECHA_ALTA_EXCEL, "FechaAlta_Excel"), (CSV_COL_NOTAS_EXCEL, "NotasAdicionales_Excel")
        ]:
            val = str(row_data.get(csv_col, '')).strip()
            if val:
                extra_info_parts.append(f"{label}: {val}")
        
        if extra_info_parts:
            current_notes = (current_notes + "\n" + "\n".join(extra_info_parts)).strip()
        
        db_data['notas_agente'] = current_notes if current_notes else None

        fc_csv = row_data.get(CSV_COL_FECHA_CREACION)
        if fc_csv: db_data['fecha_creacion'] = parse_datetime_iso(fc_csv)
        
        ua_csv = row_data.get(CSV_COL_ULTIMA_ACTUALIZACION)
        if ua_csv: db_data['ultima_actualizacion'] = parse_datetime_iso(ua_csv)
        
        cma_dt_csv = row_data.get(CSV_COL_CLASE_MUESTRA_DT)
        if cma_dt_csv: db_data['clase_muestra_agendada_dt'] = parse_datetime_iso(cma_dt_csv)
        
        asistio_val_csv = row_data.get(CSV_COL_ASISTIO_CLASE)
        if asistio_val_csv is not None and str(asistio_val_csv).strip() != "":
            db_data['asistio_clase_muestra'] = parse_boolean(asistio_val_csv)

        final_db_data = {k: v for k, v in db_data.items() if v is not None}
        if 'nombre' not in final_db_data and nombre: # Asegurar que nombre siempre esté si se proporcionó
             final_db_data['nombre'] = nombre
        if 'etapa_embudo' not in final_db_data and db_data.get('etapa_embudo'):
             final_db_data['etapa_embudo'] = db_data.get('etapa_embudo')


        try:
            existing_prospect = conv_manager.get_prospect(user_id)
            print(f"Datos a guardar para {user_id}: {final_db_data}")
            conv_manager.add_or_update_prospect(user_id=user_id, **final_db_data)
            
            if existing_prospect:
                count_updated += 1
                print(f"OK - Prospecto ACTUALIZADO: {user_id} - {final_db_data.get('nombre')}")
            else:
                count_added += 1
                print(f"OK - Prospecto AÑADIDO: {user_id} - {final_db_data.get('nombre')}")
        except Exception as e:
            print(f"ERROR procesando user_id {user_id} ({final_db_data.get('nombre')}): {e}")
            print(f"Datos que se intentaron guardar: {final_db_data}")

    print(f"\nProceso completado. {count_added} prospectos añadidos, {count_updated} prospectos actualizados.")

    if hasattr(conv_manager, 'db_conn') and conv_manager.db_conn:
        conv_manager.db_conn.close()
        print("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    csv_file_path_input = input("Introduce la ruta completa a tu archivo CSV de clientes (ej: /root/whatsapp-bot-ai/mis_clientes.csv): ").strip()
    if csv_file_path_input:
        import_clients(csv_file_path_input)
    else:
        print("No se proporcionó ruta al archivo CSV. Saliendo.")
