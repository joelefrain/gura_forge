import json
import pandas as pd

from libs.config.config_logger import get_logger

logger = get_logger()

def transform_igp_csv_to_json(csv_file, json_file):
    # Intentar leer el archivo CSV con diferentes codificaciones
    encodings = ['utf-8', 'latin1', 'ISO-8859-1']
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_file, encoding=encoding)
            break
        except UnicodeDecodeError:
            logger.warning(f"Error de codificacion con {encoding}. Intentando otra codificacion.")
    else:
        raise ValueError("No se pudo leer el archivo CSV con ninguna de las codificaciones intentadas.")
    
    # Verificar las columnas necesarias
    required_columns = ['codigo', 'fecha_local', 'hora_local', 'longitud', 'latitud', 'profundidad', 'magnitud']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Falta la columna {col} en el archivo CSV.")

    # Crear una lista para almacenar los datos transformados
    transformed_data = []
    
    for _, row in df.iterrows():
        # Convertir la fecha y la hora desde el formato ISO 8601
        try:
            fecha = pd.to_datetime(row['fecha_local'])
            hora = pd.to_datetime(row['hora_local'], format='%Y-%m-%dT%H:%M:%S.%fZ', errors='coerce')
            if pd.isnull(hora):
                hora = pd.to_datetime(row['hora_local'], errors='coerce').time()
            else:
                hora = hora.time()
        except Exception as e:
            logger.error(f"Error al procesar la fecha y hora: {e}")
            continue
        
        # Crear el diccionario con la estructura requerida
        data = {
            'eventID': row['codigo'],
            'Agency': 'igp',
            'catalog': 'igp',
            'year': fecha.year,
            'month': fecha.month,
            'day': fecha.day,
            'hour': hora.hour,
            'minute': hora.minute,
            'second': hora.second,
            'longitude': row['longitud'],
            'latitude': row['latitud'],
            'Depth': row['profundidad'],
            'magnitude': row['magnitud'],
            'magType': 'M'
        }
        
        # Añadir al listado
        transformed_data.append(data)
    
    # # Definir el nombre del archivo JSON
    # json_file = csv_file.replace('.csv', '.json')
    
    # Guardar el JSON en un archivo
    with open(json_file, 'w') as f:
        json.dump(transformed_data, f, indent=4)
    
    logger.info(f"Archivo JSON guardado como: {json_file}")
