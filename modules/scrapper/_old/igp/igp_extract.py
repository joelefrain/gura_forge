import csv
import requests

from libs.config.config_logger import get_logger

logger = get_logger()

def query_igp_data(year):
    """
    Consulta los datos del IGP para un año específico.

    Parámetros:
    - year: Año para el cual se consulta la información.

    Retorna:
    - Lista de diccionarios con la información del sismo para el año dado.
    """
    url = f"https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{year}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al realizar la solicitud al IGP: {e}")
        return None
    
    except ValueError as e:
        logger.error(f"Error al decodificar la respuesta JSON: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return None

def download_igp_data(data, output_file):
    """
    Guarda los datos del IGP en un archivo CSV.

    Parámetros:
    - data: Lista de diccionarios con la información del sismo.
    - output_file: Ruta y nombre del archivo de salida.
    """
    if data is None:
        logger.warning("No hay datos disponibles para guardar en CSV.")
        return
    
    fieldnames = [
        "codigo", "reporte_acelerometrico_pdf", "idlistasismos", 
        "fecha_local", "hora_local", "fecha_utc", "hora_utc", 
        "latitud", "longitud", "magnitud", "profundidad", 
        "referencia", "referencia2", "referencia3", "tipomagnitud", 
        "mapa", "informe", "publicado", "numero_reporte", 
        "id_pdf_tematico", "createdAt", "updatedAt", "intensidad"
    ]
    
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                row = { 
                    "codigo": item.get("codigo", ""),
                    "reporte_acelerometrico_pdf": item.get("reporte_acelerometrico_pdf", ""),
                    "idlistasismos": item.get("idlistasismos", ""),
                    "fecha_local": item.get("fecha_local", ""),
                    "hora_local": item.get("hora_local", ""),
                    "fecha_utc": item.get("fecha_utc", ""),
                    "hora_utc": item.get("hora_utc", ""),
                    "latitud": item.get("latitud", ""),
                    "longitud": item.get("longitud", ""),
                    "magnitud": item.get("magnitud", ""),
                    "profundidad": item.get("profundidad", ""),
                    "referencia": item.get("referencia", ""),
                    "referencia2": item.get("referencia2", ""),
                    "referencia3": item.get("referencia3", ""),
                    "tipomagnitud": item.get("tipomagnitud", ""),
                    "mapa": item.get("mapa", ""),
                    "informe": item.get("informe", ""),
                    "publicado": item.get("publicado", ""),
                    "numero_reporte": item.get("numero_reporte", ""),
                    "id_pdf_tematico": item.get("id_pdf_tematico", ""),
                    "createdAt": item.get("createdAt", ""),
                    "updatedAt": item.get("updatedAt", ""),
                    "intensidad": item.get("intensidad", "")
                }
                writer.writerow(row)
    
    except IOError as e:
        logger.error(f"Error al escribir el archivo CSV: {e}")
