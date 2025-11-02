import json

from datetime import datetime

from libs.config.config_logger import get_logger

logger = get_logger()

def transform_isc_csv_to_json(text_file, json_file):
    """
    Transforma un archivo de texto con formato CSV en un archivo JSON con la estructura deseada.

    Args:
        text_file (str): Ruta al archivo de texto.
    """
    transformed_data = []
    start_processing = False

    def parse_datetime(date_str, time_str):
        """
        Intenta parsear la fecha y hora con o sin fracciones de segundo.

        Args:
            date_str (str): Cadena de fecha.
            time_str (str): Cadena de hora.

        Returns:
            datetime: Objeto datetime si el formato es válido, None en caso contrario.
        """
        try:
            # Intentar con fracciones de segundo
            return datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Intentar sin fracciones de segundo
                return datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Si no se puede parsear, retornar None
                return None

    with open(text_file, mode='r', encoding='utf-8') as file:
        lines = file.readlines()
        
        for line in lines:
            # Verificar si la línea contiene 'No events were found.'
            if 'No events were found.' in line:
                logger.warning(f"No data in file: {text_file}")
                return

            # Verificar si la línea contiene 'EVENTID' (Inicio del procesamiento)
            if 'EVENTID' in line:
                start_processing = True
                continue

            # Verificar si la línea contiene 'STOP' (Fin del procesamiento)
            if 'STOP' in line:
                start_processing = False
                break

            if start_processing:
                # Limpiar espacios y dividir la línea por comas
                line = line.strip()
                columns = [col.strip() for col in line.split(',')]
                
                # Asegurarse de que la cantidad de columnas es al menos la cantidad esperada
                if len(columns) < 12:
                    continue

                # Extraer las columnas según el índice
                try:
                    date_str = columns[3]
                    time_str = columns[4]
                    event_datetime = parse_datetime(date_str, time_str)
                    
                    if event_datetime is None:
                        logger.warning(f"Fecha y hora invalidas: {date_str} {time_str}")
                        continue
                    
                    # Construir la estructura del JSON
                    event_data = {
                        "eventID": columns[0],
                        "Agency": columns[2].strip(),
                        "catalog": "isc",
                        "year": event_datetime.year,
                        "month": event_datetime.month,
                        "day": event_datetime.day,
                        "hour": event_datetime.hour,
                        "minute": event_datetime.minute,
                        "second": event_datetime.second,
                        "longitude": float(columns[6]) if columns[6] and is_numeric(columns[6]) else None,
                        "latitude": float(columns[5]) if columns[5] and is_numeric(columns[5]) else None,
                        "Depth": float(columns[7]) if columns[7] and is_numeric(columns[7]) else None,
                        "magnitude": float(columns[11]) if columns[11] and is_numeric(columns[11]) else None,
                        "magType": columns[1].strip()
                    }
                    transformed_data.append(event_data)
                except ValueError as e:
                    logger.error(f"Error al procesar la linea: {line}. Error: {e}")

    # # Definir el nombre del archivo JSON
    # json_file = text_file.replace('.csv', '.json')
    
    # Guardar el JSON en un archivo
    with open(json_file, 'w') as f:
        json.dump(transformed_data, f, indent=4)
    
    logger.info(f"Archivo JSON guardado como: {json_file}")

def is_numeric(value):
    """
    Verifica si una cadena de texto puede ser convertida a un número flotante.

    Args:
        value (str): La cadena de texto a verificar.

    Returns:
        bool: True si la cadena puede ser convertida a un número flotante, False en caso contrario.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False