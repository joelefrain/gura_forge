import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from libs.config.config_variables import MAX_WORKERS, CATALOG_CSV_DIR
from modules.catalog_scraper.seismic_scraper import SeismicScraper

scraper = SeismicScraper(max_workers=MAX_WORKERS)

# Límites geográficos (Perú y alrededores)
MIN_LAT, MAX_LAT = -20.0, 0.0
MIN_LON, MAX_LON = -85.0, -68.0

# Año de inicio del scraping
START_YEAR = 2020

# Cargar catálogos CSV personalizados
results = scraper.load_csv_catalogs(
    csv_catalogs={
        "gcmt": [
            CATALOG_CSV_DIR / "gcmt/gcmt_data.csv",
        ],
        "igp": [
            CATALOG_CSV_DIR / "igp/igp_pre2021_catalogue_.csv"
        ],
        "isc": [
            CATALOG_CSV_DIR / "isc-gem/isc-gem-cat.csv",
            CATALOG_CSV_DIR / "isc-gem/isc-gem-suppl.csv",
        ],
        "sara": [
            CATALOG_CSV_DIR / "sara/T4_post1964_catalogue.csv",
            CATALOG_CSV_DIR / "sara/T4_pre1964_catalogue_.csv",
        ],
    },
    year=2020,
    min_lat=MIN_LAT,
    max_lat=MAX_LAT,
    min_lon=MIN_LON,
    max_lon=MAX_LON,
)


# scraper = SeismicScraper(max_workers=MAX_WORKERS)

# results = scraper.scrape_events(
#     start_year=START_YEAR,
#     min_lat=MIN_LAT,
#     max_lat=MAX_LAT,
#     min_lon=MIN_LON,
#     max_lon=MAX_LON,
#     catalogs=["usgs", "isc", "igp"],
# )