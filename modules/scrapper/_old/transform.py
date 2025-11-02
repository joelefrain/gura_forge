import os
from modules.scrapper.igp.igp_transform import transform_igp_csv_to_json
from modules.scrapper.usgs.usgs_transform import transform_usgs_csv_to_json
from modules.scrapper.isc.isc_transform import transform_isc_csv_to_json

from libs.config.config_logger import get_logger

logger = get_logger()


def process_directory(input_directory, output_directory, catalog_name, transformation_func, start_year):
    """
    Procesa todos los archivos CSV en un directorio específico usando la función de transformación proporcionada.

    Args:
        input_directory (str): El directorio que contiene los archivos CSV.
        output_directory (str): El directorio que contiene los archivos JSON.
        catalog_name (str): El nombre del catálogo (ej. 'igp', 'usgs').
        transformation_func (function): La función de transformación a aplicar a cada archivo CSV.
    """
    # Listar todos los archivos en el directorio
    files = os.listdir(input_directory)

    # # Filtrar archivos que comienzan con el nombre del catálogo y terminan en '.csv'
    # csv_files = [f for f in files if f.startswith(
    #     catalog_name) and f.endswith('.csv')]

    csv_files = [f for f in files if f.startswith(catalog_name) and f.endswith(
        '.csv') and int(f.split('_')[1].split('.')[0]) >= start_year]

    # Procesar cada archivo CSV
    for csv_file in csv_files:
        csv_path = os.path.join(input_directory, csv_file)
        json_file = csv_file.replace('.csv', '.json')
        json_path = os.path.join(output_directory, json_file)
        transformation_func(csv_path, json_path)


def transform(seismic_catalog_path, start_year):
    """
    Punto de entrada principal para procesar catálogos de datos sísmicos y transformarlos en JSON.
    """
    # Lista de catálogos y sus respectivas funciones de transformación
    catalog_transformations = {
        'igp': transform_igp_csv_to_json,
        'usgs': transform_usgs_csv_to_json,
        'isc': transform_isc_csv_to_json
    }

    # Procesar cada catálogo en la lista
    for catalog, transformation_func in catalog_transformations.items():
        # Directorio que contiene los archivos CSV para el catálogo específico
        input_directory = f'{seismic_catalog_path}/raw/{catalog}'
        output_directory = f'{seismic_catalog_path}/processed/{catalog}'

        # Procesar los archivos en el directorio
        process_directory(input_directory, output_directory,
                          catalog, transformation_func, start_year)
