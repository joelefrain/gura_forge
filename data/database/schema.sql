-- Tabla de claves de traducción
CREATE TABLE IF NOT EXISTS translation_key (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT NOT NULL UNIQUE -- Identificador único para textos
);

-- Tabla de traducciones
CREATE TABLE IF NOT EXISTS translation (
    key_id INTEGER NOT NULL,
    language_code TEXT NOT NULL,
    -- 'es', 'en', 'fr', etc.
    translated_text TEXT NOT NULL,
    PRIMARY KEY (key_id, language_code),
    FOREIGN KEY (key_id) REFERENCES translation_key(id)
);

-- Tabla para almacenar información de clientes
CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_key_id INTEGER NOT NULL,
    -- Referencia a la tabla de traducción
    code TEXT NOT NULL UNIQUE,
    -- Código único de cliente
    logo_path TEXT NOT NULL,
    -- Ruta del archivo de logo
    FOREIGN KEY (name_key_id) REFERENCES translation_key(id)
);

-- Tabla para unidades mineras
CREATE TABLE IF NOT EXISTS mining_unit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    name_key_id INTEGER NOT NULL,
    -- Referencia a la tabla de traducción
    code TEXT NOT NULL UNIQUE,
    -- Código único de unidad minera
    geometries_path TEXT NOT NULL,
    -- Ruta base para archivos de geometría
    documentation_path TEXT NOT NULL,
    -- Ruta base para archivos de documentación
    utm_zone TEXT NOT NULL,
    -- Zona UTM asociada
    FOREIGN KEY (client_id) REFERENCES client(id),
    FOREIGN KEY (name_key_id) REFERENCES translation_key(id)
);

-- Tabla para estructuras mineras
CREATE TABLE IF NOT EXISTS mine_structure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mining_unit_id INTEGER NOT NULL,
    name_key_id INTEGER NOT NULL,
    -- Referencia a la tabla de traducción
    code TEXT NOT NULL UNIQUE,
    -- Código único de estructura
    min_east REAL NOT NULL,
    -- Coordenada Este mínima
    max_east REAL NOT NULL,
    -- Coordenada Este máxima
    min_north REAL NOT NULL,
    -- Coordenada Norte mínima
    max_north REAL NOT NULL,
    -- Coordenada Norte máxima
    preprocessor_path TEXT NOT NULL,
    -- Ruta de plantillas de preprocesamiento
    FOREIGN KEY (mining_unit_id) REFERENCES mining_unit(id),
    FOREIGN KEY (name_key_id) REFERENCES translation_key(id)
);

-- Tabla para proyectos de ingeniería
CREATE TABLE IF NOT EXISTS engineering_project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mining_unit_id INTEGER NOT NULL,
    name_key_id INTEGER NOT NULL,
    -- Referencia a la tabla de traducción
    code TEXT NOT NULL UNIQUE,
    -- Código único del proyecto
    postprocessor_path TEXT NOT NULL,
    -- Ruta de plantillas de postprocesamiento
    FOREIGN KEY (mining_unit_id) REFERENCES mining_unit(id),
    FOREIGN KEY (name_key_id) REFERENCES translation_key(id)
);

-- Tabla para sesiones de análisis
CREATE TABLE IF NOT EXISTS session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    session_code TEXT NOT NULL,
    -- Referencia a la tabla de traducción
    analysis_type TEXT NOT NULL,
    -- Nombre descriptivo de la sesión
    session_name TEXT NOT NULL,
    -- Tipo de análisis (preprocess, process, etc.)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_data_path TEXT,
    -- Ruta de datos crudos
    temp_path TEXT,
    outputs_path TEXT,
    -- Ruta de trabajo de la sesión
    FOREIGN KEY (project_id) REFERENCES engineering_project(id)
);

-- Tabla principal de eventos sísmicos
CREATE TABLE IF NOT EXISTS seismic_events (
    event_id TEXT PRIMARY KEY,
    agency TEXT NOT NULL,
    catalog TEXT NOT NULL,
    event_time DATETIME NOT NULL,
    longitude REAL NOT NULL,
    latitude REAL NOT NULL,
    depth REAL,
    magnitude REAL,
    mag_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para estaciones sísmicas
CREATE TABLE IF NOT EXISTS seismic_station (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    -- Código de estación (ej: LAGU, APLA)
    name TEXT NOT NULL,
    -- Nombre descriptivo (ej: LAGUNAS-LAMBAYEQUE)
    latitude REAL NOT NULL,
    -- Latitud de la estación
    longitude REAL NOT NULL,
    -- Longitud de la estación
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para registros de aceleración por estación
CREATE TABLE IF NOT EXISTS seismic_acceleration_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    -- Referencia al evento sísmico
    station_id INTEGER NOT NULL,
    -- Referencia a la estación
    start_time DATETIME NOT NULL,
    -- Tiempo de inicio del registro (UTC)
    num_samples INTEGER NOT NULL,
    -- Número total de muestras
    sampling_frequency REAL NOT NULL,
    -- Frecuencia de muestreo en Hz
    pga_vertical REAL,
    -- PGA vertical (cm/s²)
    pga_north REAL,
    -- PGA norte-sur (cm/s²)
    pga_east REAL,
    -- PGA este-oeste (cm/s²)
    baseline_correction BOOLEAN DEFAULT TRUE,
    -- Corrección por línea base aplicada
    units TEXT DEFAULT 'cm/s2',
    -- Unidades de medida
    downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Fecha de descarga del registro
    file_path TEXT,
    -- Ruta local del archivo descargado
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES seismic_events(event_id),
    FOREIGN KEY (station_id) REFERENCES seismic_station(id),
    UNIQUE(event_id, station_id)
);

-- Tabla para muestras de aceleración (series de tiempo)
CREATE TABLE IF NOT EXISTS acceleration_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    -- Referencia al registro de aceleración
    sample_index INTEGER NOT NULL,
    -- Índice de la muestra (0, 1, 2, ...)
    accel_vertical REAL NOT NULL,
    -- Aceleración vertical (Z)
    accel_north REAL NOT NULL,
    -- Aceleración norte-sur (N)
    accel_east REAL NOT NULL,
    -- Aceleración este-oeste (E)
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(record_id, sample_index)
);

-- Tabla de control de sincronización
CREATE TABLE IF NOT EXISTS sync_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog TEXT NOT NULL,
    year INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    status TEXT CHECK(status IN ('running', 'completed', 'failed')) DEFAULT 'running',
    error_message TEXT,
    UNIQUE(catalog, year)
);

-- Nueva tabla para registrar cada ejecución de sincronización (una fila por run)
CREATE TABLE IF NOT EXISTS sync_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_catalog_id INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    status TEXT CHECK(
        status IN (
            'running',
            'completed',
            'failed',
            'completed_with_errors'
        )
    ) DEFAULT 'running',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sync_catalog_id) REFERENCES sync_catalog(id)
);

-- Índices para consultas eficientes
CREATE INDEX IF NOT EXISTS idx_session_project ON session(project_id);

CREATE INDEX IF NOT EXISTS idx_event_time ON seismic_events(event_time);

CREATE INDEX IF NOT EXISTS idx_catalog ON seismic_events(catalog);

CREATE INDEX IF NOT EXISTS idx_magnitude ON seismic_events(magnitude);

CREATE INDEX IF NOT EXISTS idx_location ON seismic_events(latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_station_code ON seismic_station(code);

CREATE INDEX IF NOT EXISTS idx_station_location ON seismic_station(latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_accel_record_event ON seismic_acceleration_record(event_id);

CREATE INDEX IF NOT EXISTS idx_accel_record_station ON seismic_acceleration_record(station_id);

CREATE INDEX IF NOT EXISTS idx_accel_record_timestamp ON seismic_acceleration_record(start_time);

CREATE INDEX IF NOT EXISTS idx_acceleration_sample_record ON acceleration_sample(record_id);

CREATE INDEX IF NOT EXISTS idx_acceleration_sample_index ON acceleration_sample(record_id, sample_index);