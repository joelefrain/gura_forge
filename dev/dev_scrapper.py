import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from modules.scrapper.scrapper import SeismicScraper
from libs.config.config_variables import DATABASE_PATH

# Configuración
DB_PATH = DATABASE_PATH
START_YEAR = 2020

# Límites geográficos (Perú y alrededores)
MIN_LAT, MAX_LAT = -20.0, 0.0
MIN_LON, MAX_LON = -85.0, -68.0

# Ejecutar scraping
scraper = SeismicScraper(DB_PATH, max_workers=5)
results = scraper.scrape_events(
    start_year=START_YEAR,
    min_lat=MIN_LAT,
    max_lat=MAX_LAT,
    min_lon=MIN_LON,
    max_lon=MAX_LON,
    catalogs=["usgs", "isc", "igp"],  # Opcional: especifica catálogos
)
