from modules.scrapper.extract import extract
from modules.scrapper.transform import transform
from modules.scrapper.load import load

from libs.config.config_logger import get_logger

logger = get_logger()

class Preprocessor:
    def __init__(self, seismic_catalog_path, database_path, start_year, min_lat, max_lat, min_lon, max_lon):
        """
        Inicializa y ejecuta el preprocesamiento de datos sísmicos.
        
        Parameters:
        - seismic_catalog_path: Ruta donde se almacenará el catálogo sísmico.
        - start_year: Año de inicio para la extracción de datos.
        - min_lat, max_lat: Límites de latitud para la extracción.
        - min_lon, max_lon: Límites de longitud para la extracción.
        """
        self._preprocess(seismic_catalog_path, database_path, start_year, min_lat, max_lat, min_lon, max_lon)

    def _preprocess(self, seismic_catalog_path, database_path, start_year, min_lat, max_lat, min_lon, max_lon):
        """
        Ejecuta el proceso de extracción y transformación de catálogos sísmicos.
        """
        logger.info('Iniciando la extraccion de datos...')
        extract(min_lat, max_lat, min_lon, max_lon, start_year, seismic_catalog_path)
        
        logger.info('Extraccion completada. Iniciando la transformacion de datos...')
        transform(seismic_catalog_path, start_year)
        
        json_path = f"{seismic_catalog_path}/processed"
        # start_year=1800
        logger.info('Transformacion completada. Iniciando la carga de datos...')
        load(json_path, database_path, start_year)
