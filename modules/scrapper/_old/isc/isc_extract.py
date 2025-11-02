import requests

from libs.config.config_logger import get_logger

logger = get_logger()

def query_isc_data(min_lat, max_lat, min_lon, max_lon, start_date, end_date):
    """
    Construye la URL de solicitud para el catálogo de terremotos del ISC.

    Parámetros:
    - min_lat: Latitud mínima (sur)
    - max_lat: Latitud máxima (norte)
    - min_lon: Longitud mínima (oeste)
    - max_lon: Longitud máxima (este)
    - start_date: Fecha de inicio en formato 'YYYY-MM-DD'
    - end_date: Fecha de fin en formato 'YYYY-MM-DD'

    Retorna:
    - URL construida para la solicitud.
    """
    start_year, start_month, start_day = start_date.split('-')
    end_year, end_month, end_day = end_date.split('-')

    url = (
        "http://www.isc.ac.uk/cgi-bin/web-db-run?"
        "request=COMPREHENSIVE&out_format=CATCSV&searchshape=RECT"
        f"&bot_lat={min_lat}&top_lat={max_lat}&left_lon={min_lon}&right_lon={max_lon}"
        f"&start_year={start_year}&start_month={start_month}&start_day={start_day}&start_time=00%3A00%3A00"
        f"&end_year={end_year}&end_month={end_month}&end_day={end_day}&end_time=00%3A00%3A00"
    )
    
    return url

def download_isc_data(url, output_file):
    """
    Descarga los datos del ISC en un archivo específico.

    Parámetros:
    - url: URL de la solicitud.
    - output_file: Ruta y nombre del archivo de salida.
    """
    response = requests.get(url)
    
    if response.status_code == 200:
        with open(output_file, 'wb') as file:
            file.write(response.content)
    else:
        logger.error(f"Error en la solicitud al ISC: {response.status_code}")

