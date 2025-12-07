import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from modules.downloader.records_downloader import SeismicDownloader


NUM_EVENTS = 100
PARALLEL_STATIONS = 10
CATALOG_PARSER_CONFIG = {
    "igp": '2025-01-01',
    # "usgs": '2025-12-28',
    # "emsc": '2025-12-28',
}

downloader = SeismicDownloader()

downloader.process_multiple_catalogs(
    catalogs=CATALOG_PARSER_CONFIG,
    max_workers=80,
    parallel_stations=PARALLEL_STATIONS,
)