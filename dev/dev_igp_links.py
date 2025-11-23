import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from modules.downloader.records_downloader import SeismicDownloader


NUM_EVENTS = 100
PARALLEL_STATIONS = 10
CATALOG_PARSER_CONFIG = {
    "igp": 200,
    # "usgs": 5,
    # "emsc": 15,
}

downloader = SeismicDownloader()

downloader.process_multiple_catalogs(
    catalogs=CATALOG_PARSER_CONFIG,
    max_workers=80,
    parallel_stations=PARALLEL_STATIONS,
)