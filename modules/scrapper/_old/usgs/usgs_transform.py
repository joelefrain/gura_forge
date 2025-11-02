import csv
import json

from datetime import datetime, timedelta

from libs.config.config_logger import get_logger

logger = get_logger()

def transform_usgs_csv_to_json(csv_file, json_file):
    """
    Transforma un archivo CSV del catálogo USGS en un archivo JSON con la estructura deseada.
    """
    transformed_data = []

    # Intentar leer el archivo CSV con diferentes codificaciones
    encodings = ['utf-8', 'latin1', 'ISO-8859-1']
    for encoding in encodings:
        try:
            with open(csv_file, mode='r', encoding=encoding) as file:
                reader = csv.DictReader(file)
        
                for row in reader:
                    # Extraer los componentes de la fecha y hora
                    timestamp_ms = int(row['time'])
                    timestamp_s = timestamp_ms / 1000        
                    event_datetime = datetime(1970, 1, 1) + timedelta(seconds=timestamp_s)
                    year = event_datetime.year
                    month = event_datetime.month
                    day = event_datetime.day
                    hour = event_datetime.hour
                    minute = event_datetime.minute
                    second = event_datetime.second
                    
                    # Construir la estructura del JSON
                    event_data = {
                        "eventID": row['ids'],
                        "Agency": row['net'],
                        "catalog": "usgs",
                        "year": year,
                        "month": month,
                        "day": day,
                        "hour": hour,
                        "minute": minute,
                        "second": second,
                        "longitude": float(row['longitude']) if row['longitude'] else None,
                        "latitude": float(row['latitude']) if row['latitude'] else None,
                        "Depth": float(row['depth']) if row['depth'] else None,
                        "magnitude": float(row['mag']) if row['mag'] else None,
                        "magType": row.get('magType', '')
                    }
                    transformed_data.append(event_data)
                    
                    break  # Salir del bucle si la lectura fue exitosa
        except UnicodeDecodeError:
            logger.warning(f"Error de codificacion con {encoding}, intentando con otra codificacion...")
        except Exception as e:
            logger.error(f"Error al procesar el archivo {csv_file}: {e}")
            return
    
        
    # # Definir el nombre del archivo JSON
    # json_file = csv_file.replace('.csv', '.json')
    
    # Guardar el JSON en un archivo
    with open(json_file, 'w') as f:
        json.dump(transformed_data, f, indent=4)
    
    logger.info(f"Archivo JSON guardado como: {json_file}")

