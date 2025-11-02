import os
import json
import sqlite3

from libs.config.config_logger import get_logger

logger = get_logger()


def create_connection(sqlite_db_path):
    """Crea una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(sqlite_db_path)
    return conn


def create_table(conn):
    """Crea la tabla 'sismo' en la base de datos SQLite si no existe."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sismo (
            eventID TEXT PRIMARY KEY,
            Agency TEXT,
            catalog TEXT,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            hour INTEGER,
            minute INTEGER,
            second INTEGER,
            longitude REAL,
            latitude REAL,
            Depth REAL,
            magnitude REAL,
            magType TEXT
        )
    ''')
    conn.commit()


def insert_data(conn, data):
    """Inserta datos en la tabla 'sismo'."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO sismo (eventID, Agency, catalog, year, month, day, hour, minute, second, longitude, latitude, Depth, magnitude, magType)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['eventID'],
        data['Agency'],
        data['catalog'],
        data['year'],
        data['month'],
        data['day'],
        data['hour'],
        data['minute'],
        data['second'],
        data['longitude'],
        data['latitude'],
        data['Depth'],
        data['magnitude'],
        data['magType']
    ))
    conn.commit()


def process_json_files(json_directory, start_year):
    """Procesa los archivos JSON en el directorio, aplicando filtros si es necesario."""
    json_files = []
    for root, dirs, files in os.walk(json_directory):
        for file in files:
            if file.endswith('.json'):
                # Extraer el año del nombre del archivo
                file_parts = file.split('_')
                file_year = int(file_parts[1].split('.')[0])

                # Filtrar por año
                if start_year <= file_year:
                    json_files.append(os.path.join(root, file))
                    logger.info(f"Archivo cargado: {file}")
    return json_files


def load_and_insert_json_data(conn, json_files):
    """Carga los archivos JSON y los inserta en la base de datos."""
    for json_path in json_files:
        with open(json_path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):  # Si el JSON es una lista de objetos
                for item in data:
                    insert_data(conn, item)
            else:
                insert_data(conn, data)


def load(json_directory, sqlite_db_path, start_year=None):
    """Función principal para crear la base de datos SQLite."""
    conn = create_connection(sqlite_db_path)
    create_table(conn)

    json_files = process_json_files(json_directory, start_year)
    load_and_insert_json_data(conn, json_files)

    conn.close()
    logger.info("Base de datos SQLite creada.")
