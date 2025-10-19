-- Tabla de claves de traducción
CREATE TABLE translation_key (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT NOT NULL UNIQUE -- Identificador único para textos
);

-- Tabla de traducciones
CREATE TABLE translation (
    key_id INTEGER NOT NULL,
    language_code TEXT NOT NULL,
    -- 'es', 'en', 'fr', etc.
    translated_text TEXT NOT NULL,
    PRIMARY KEY (key_id, language_code),
    FOREIGN KEY (key_id) REFERENCES translation_key(id)
);

-- Tabla para almacenar información de clientes
CREATE TABLE client (
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
CREATE TABLE mining_unit (
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
CREATE TABLE mine_structure (
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
CREATE TABLE engineering_project (
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
CREATE TABLE session (
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

CREATE INDEX idx_session_project ON session(project_id);