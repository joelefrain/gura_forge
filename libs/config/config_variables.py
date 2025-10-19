# This file contains configuration variables for the application.
# ---------------------------------------------------------------
import os
from pathlib import Path


# Constants for formats
# ---------------------------------------------------------------
SEP_FORMAT = ";"

# Font for the report
DEFAULT_FONT = "Arial"

# Constants for number formats
DECIMAL_CHAR = ","
THOUSAND_CHAR = " "
DATE_FORMAT = "%d-%m-%y"

# Language settings
LANG_DEFAULT = "es"  # Default language for the application

# Defaults for the report
# ---------------------------------------------------------------
DOC_TITLE = "SIG-AND"
THEME_COLOR = "#0069AA"
THEME_COLOR_FONT = "white"

# Paths to data files
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent.parent

LOG_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "var"
ENV_FILE_PATH = BASE_DIR / "config" / ".env"

# Paths to database and schema files
# ---------------------------------------------------------------
PROCESSOR_PATH_CONFIG = BASE_DIR / "data" / "processor"
SCHEMA_SQL_PATH = BASE_DIR / "data" / "database" / "schema.sql"
DATABASE_PATH = BASE_DIR / "data" / "database" / "geo_sentry.db"
FILE_PATHS_CONFIG = BASE_DIR / "data" / "database" / "file_paths_config.json"

# Paths to data files
# ---------------------------------------------------------------
LOGO_SVG = BASE_DIR / "data" / "logo" / "logo_main_109x50.svg"
LOGO_PDF = BASE_DIR / "data" / "logo" / "logo_main_109x50.pdf"
DATA_CONFIG = BASE_DIR / "data" / "config"
DXF_COLORS_PATH = BASE_DIR / "data" / "styles" / "dxf_colors.json"
DXF_LINETYPES_PATH = BASE_DIR / "data" / "styles" / "dxf_linetypes.json"
DATETIME_FORMATS_PATH = BASE_DIR / "data" / "styles" / "datetime_formats.json"

# Paths to configuration directories
# ---------------------------------------------------------------
CALC_CONFIG_DIR = BASE_DIR / "modules" / "calculations" / "data"
REPORT_CONFIG_DIR = BASE_DIR / "modules" / "reporter" / "data" / "reports"
CHART_CONFIG_DIR = BASE_DIR / "modules" / "reporter" / "data" / "charts"
NOTE_CONFIG_DIR = BASE_DIR / "modules" / "reporter" / "data" / "notes"
TABLE_CONFIG_DIR = BASE_DIR / "modules" / "reporter" / "data" / "tables"

# Allowed characters in formats
# ---------------------------------------------------------------
DEFAULT_SEP_CHARS = (",", ";", "\t", "|")
DEFAULT_CHARS_IN_TEXTS = r"[^\w\s:/\-.+]"

# Minimum records required for processing & plotting
# ---------------------------------------------------------------
MINIMUN_RECORDS = 2

# Máximo número de workers
# ---------------------------------------------------------------
MAX_WORKERS = min(40, (os.cpu_count() or 1) * 5)

# Límite de datos
MAX_TOTAL_SIZE = 2.5 * 1024**3  # 2.5 GB
MAX_FILE_SIZE = 800 * 1024**2  # 800 MB

# Estilos para matplotlib
# ---------------------------------------------------------------
UNIQUE_MARKERS = ("o", "s", "D", "v", "^", "<", ">", "p", "h")

# Extensiones permitidas en parsers
# ---------------------------------------------------------------
TEXT_EXTENSIONS = [".csv", ".txt", ".dat", ".gkn"]
EXCEL_EXTENSIONS = [".xlsx", ".xls", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"]

# Formatos de parseo de fechas
# ---------------------------------------------------------------
TIMESTAMP_ALLOWABLE_DECIMALS = 6  # hasta microsegundos
DATETIME_ALLOWABLE_PATTERN = r"[^\w\s:/\-.,]"
TIMESTAMP_ALLOWABLE_PATTERN = r"(\d{2}:\d{2}:\d{2})\.(\d{7,})"

# Configuración de tipos de instrumentos
# ---------------------------------------------------------------
INSTRUMENTS_TYPES_SCHEMA = [
    {
        "code": "PCV",
        "key": "instrument_type_pcv",
        "es": "Piezómetro de cuerda vibrante",
        "en": "Vibrating Wire Piezometer",
        "processor_path": PROCESSOR_PATH_CONFIG / "PCV.toml",
        "styles": '{"bokeh_marker": "circle_x", "mpl_marker": "$\\\\circ$", "color": "skyblue"}',
    },
    {
        "code": "PTA",
        "key": "instrument_type_pta",
        "es": "Piezómetro de tubo abierto",
        "en": "Open Pipe Piezometer",
        "processor_path": PROCESSOR_PATH_CONFIG / "PTA.toml",
        "styles": '{"bokeh_marker": "circle", "mpl_marker": "o", "color": "blue"}',
    },
    {
        "code": "PCT",
        "key": "instrument_type_pct",
        "es": "Punto de control topográfico",
        "en": "Topographic Control Point",
        "processor_path": PROCESSOR_PATH_CONFIG / "PCT.toml",
        "styles": '{"bokeh_marker": "diamond", "mpl_marker": "D", "color": "purple"}',
    },
    {
        "code": "SACV",
        "key": "instrument_type_sacv",
        "es": "Sensor de asentamiento de cuerda vibrante",
        "en": "Vibrating Wire Settlement Sensor",
        "processor_path": PROCESSOR_PATH_CONFIG / "SACV.toml",
        "styles": '{"bokeh_marker": "triangle", "mpl_marker": "^", "color": "orange"}',
    },
    {
        "code": "CPCV",
        "key": "instrument_type_cpcv",
        "es": "Celda de presión de cuerda vibrante",
        "en": "Vibrating Wire Pressure Cell",
        "processor_path": PROCESSOR_PATH_CONFIG / "CPCV.toml",
        "styles": '{"bokeh_marker": "circle_dot", "mpl_marker": "$\\\\odot$", "color": "pink"}',
    },
    {
        "code": "INC",
        "key": "instrument_type_inc",
        "es": "Inclinómetro vertical",
        "en": "Vertical Inclinometer",
        "processor_path": PROCESSOR_PATH_CONFIG / "INC.toml",
        "styles": '{"bokeh_marker": "square", "mpl_marker": "s", "color": "green"}',
    },
]

ALLOWABLE_INSTRUMENTS_TYPES = [
    instrument["code"] for instrument in INSTRUMENTS_TYPES_SCHEMA
]

INSTRUMENTS_TOML_PATHS = {
    instrument["code"]: instrument["processor_path"]
    for instrument in INSTRUMENTS_TYPES_SCHEMA
}
