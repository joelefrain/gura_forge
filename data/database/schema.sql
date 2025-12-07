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

-- Tabla para definición de filtros aplicados a registros
CREATE TABLE IF NOT EXISTS filter_definition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    filter_type TEXT CHECK(
        filter_type IN (
            'lowpass',
            'highpass',
            'bandpass',
            'bandstop',
            'none'
        )
    ) NOT NULL,
    low_cutoff_frequency REAL,
    -- Frecuencia de corte baja (Hz)
    high_cutoff_frequency REAL,
    -- Frecuencia de corte alta (Hz)
    filter_order INTEGER,
    -- Orden del filtro
    taper_type TEXT CHECK(
        taper_type IN ('cosine', 'hann', 'hamming', 'none')
    ),
    taper_percentage REAL,
    -- Porcentaje de ventana para taper
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para registros de aceleración procesados (filtrados)
CREATE TABLE IF NOT EXISTS processed_acceleration_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_record_id INTEGER NOT NULL,
    filter_id INTEGER,
    process_type TEXT CHECK(
        process_type IN (
            'filtered',
            'baseline_corrected',
            'integrated',
            'both'
        )
    ) NOT NULL,
    pga_vertical REAL,
    -- PGA vertical procesado (cm/s²)
    pga_north REAL,
    -- PGA norte procesado (cm/s²)
    pga_east REAL,
    -- PGA este procesado (cm/s²)
    pgv_vertical REAL,
    -- PGV vertical (cm/s)
    pgv_north REAL,
    -- PGV norte (cm/s)
    pgv_east REAL,
    -- PGV este (cm/s)
    pgd_vertical REAL,
    -- PGD vertical (cm)
    pgd_north REAL,
    -- PGD norte (cm)
    pgd_east REAL,
    -- PGD este (cm)
    arias_intensity_vertical REAL,
    -- Intensidad de Arias vertical (m/s)
    arias_intensity_north REAL,
    -- Intensidad de Arias norte (m/s)
    arias_intensity_east REAL,
    -- Intensidad de Arias este (m/s)
    duration_5_95_vertical REAL,
    -- Duración 5-95% vertical (s)
    duration_5_95_north REAL,
    -- Duración 5-95% norte (s)
    duration_5_95_east REAL,
    -- Duración 5-95% este (s)
    husid_index_vertical REAL,
    -- Índice HUSID vertical
    husid_index_north REAL,
    -- Índice HUSID norte
    husid_index_east REAL,
    -- Índice HUSID este
    mean_period_vertical REAL,
    -- Periodo medio vertical (s)
    mean_period_north REAL,
    -- Periodo medio norte (s)
    mean_period_east REAL,
    -- Periodo medio este (s)
    -- Frecuencias importantes para señales sísmicas
    predominant_frequency_vertical REAL,
    -- Frecuencia predominante vertical (Hz)
    predominant_frequency_north REAL,
    -- Frecuencia predominante norte (Hz)
    predominant_frequency_east REAL,
    -- Frecuencia predominante este (Hz)
    coda_frequency_vertical REAL,
    -- Frecuencia coda vertical (Hz)
    coda_frequency_north REAL,
    -- Frecuencia coda norte (Hz)
    coda_frequency_east REAL,
    -- Frecuencia coda este (Hz)
    corner_frequency_vertical REAL,
    -- Frecuencia de esquina vertical (Hz)
    corner_frequency_north REAL,
    -- Frecuencia de esquina norte (Hz)
    corner_frequency_east REAL,
    -- Frecuencia de esquina este (Hz)
    central_frequency_vertical REAL,
    -- Frecuencia central vertical (Hz)
    central_frequency_north REAL,
    -- Frecuencia central norte (Hz)
    central_frequency_east REAL,
    -- Frecuencia central este (Hz)
    bandwidth_vertical REAL,
    -- Ancho de banda vertical (Hz)
    bandwidth_north REAL,
    -- Ancho de banda norte (Hz)
    bandwidth_east REAL,
    -- Ancho de banda este (Hz)
    spectral_moment_0_vertical REAL,
    -- Momento espectral de orden 0 (vertical)
    spectral_moment_1_vertical REAL,
    -- Momento espectral de orden 1 (vertical)
    spectral_moment_2_vertical REAL,
    -- Momento espectral de orden 2 (vertical)
    spectral_moment_0_north REAL,
    -- Momento espectral de orden 0 (north)
    spectral_moment_1_north REAL,
    -- Momento espectral de orden 1 (north)
    spectral_moment_2_north REAL,
    -- Momento espectral de orden 2 (north)
    spectral_moment_0_east REAL,
    -- Momento espectral de orden 0 (east)
    spectral_moment_1_east REAL,
    -- Momento espectral de orden 1 (east)
    spectral_moment_2_east REAL,
    -- Momento espectral de orden 2 (east)
    -- Atributos adicionales importantes
    significant_duration_vertical REAL,
    -- Duración significativa vertical (s)
    significant_duration_north REAL,
    -- Duración significativa norte (s)
    significant_duration_east REAL,
    -- Duración significativa este (s)
    bracketed_duration_vertical REAL,
    -- Duración entre brackets vertical (s)
    bracketed_duration_north REAL,
    -- Duración entre brackets norte (s)
    bracketed_duration_east REAL,
    -- Duración entre brackets este (s)
    cumulative_absolute_velocity_vertical REAL,
    -- Velocidad absoluta acumulada vertical
    cumulative_absolute_velocity_north REAL,
    -- Velocidad absoluta acumulada norte
    cumulative_absolute_velocity_east REAL,
    -- Velocidad absoluta acumulada este
    processing_notes TEXT,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_record_id) REFERENCES seismic_acceleration_record(id),
    FOREIGN KEY (filter_id) REFERENCES filter_definition(id),
    UNIQUE(original_record_id, filter_id, process_type)
);

-- Tabla para muestras de aceleración procesadas
CREATE TABLE IF NOT EXISTS processed_acceleration_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processed_record_id INTEGER NOT NULL,
    sample_index INTEGER NOT NULL,
    time_from_start REAL NOT NULL,
    -- Tiempo desde inicio (s)
    accel_vertical REAL NOT NULL,
    -- Aceleración vertical procesada (cm/s²)
    accel_north REAL NOT NULL,
    -- Aceleración norte procesada (cm/s²)
    accel_east REAL NOT NULL,
    -- Aceleración este procesada (cm/s²)
    vel_vertical REAL,
    -- Velocidad vertical (cm/s)
    vel_north REAL,
    -- Velocidad norte (cm/s)
    vel_east REAL,
    -- Velocidad este (cm/s)
    disp_vertical REAL,
    -- Desplazamiento vertical (cm)
    disp_north REAL,
    -- Desplazamiento norte (cm)
    disp_east REAL,
    -- Desplazamiento este (cm)
    FOREIGN KEY (processed_record_id) REFERENCES processed_acceleration_record(id),
    UNIQUE(processed_record_id, sample_index)
);

-- Tabla para espectros de Fourier
CREATE TABLE IF NOT EXISTS fourier_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    component TEXT CHECK(
        component IN ('vertical', 'north', 'east', 'resultant')
    ) NOT NULL,
    window_type TEXT CHECK(
        window_type IN ('none', 'cosine', 'hann', 'hamming', 'parzen')
    ) NOT NULL DEFAULT 'none',
    window_length REAL,
    -- Longitud de ventana en segundos
    nfft INTEGER,
    -- Número de puntos FFT
    frequency REAL NOT NULL,
    -- Frecuencia (Hz)
    amplitude REAL NOT NULL,
    -- Amplitud del espectro
    phase REAL,
    -- Fase (radianes)
    amplitude_db REAL,
    -- Amplitud en dB
    power_spectral_density REAL,
    -- Densidad espectral de potencia (cm²/s³/Hz)
    cumulative_power REAL,
    -- Potencia acumulada
    cumulative_power_percentage REAL,
    -- Porcentaje de potencia acumulada
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(
        record_id,
        record_type,
        component,
        frequency,
        window_type
    )
);

-- Tabla para espectros de respuesta
CREATE TABLE IF NOT EXISTS response_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    component TEXT CHECK(
        component IN ('vertical', 'north', 'east', 'resultant')
    ) NOT NULL,
    damping_ratio REAL NOT NULL,
    -- Razón de amortiguamiento (ej: 0.05 para 5%)
    period REAL NOT NULL,
    -- Periodo (s)
    spectral_acceleration REAL,
    -- Pseudo-aceleración espectral (cm/s²)
    spectral_velocity REAL,
    -- Pseudo-velocidad espectral (cm/s)
    spectral_displacement REAL,
    -- Desplazamiento espectral (cm)
    spectral_acceleration_db REAL,
    -- SA en dB
    acceleration_response REAL,
    -- Aceleración de respuesta real (cm/s²)
    velocity_response REAL,
    -- Velocidad de respuesta real (cm/s)
    displacement_response REAL,
    -- Desplazamiento de respuesta real (cm)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(
        record_id,
        record_type,
        component,
        damping_ratio,
        period
    )
);

-- Tabla para parámetros espectrales importantes
CREATE TABLE IF NOT EXISTS spectral_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_spectrum_id INTEGER NOT NULL,
    period_at_max_sa REAL,
    -- Periodo en máxima aceleración espectral (s)
    max_spectral_acceleration REAL,
    -- Máxima aceleración espectral (cm/s²)
    period_at_max_sv REAL,
    -- Periodo en máxima velocidad espectral (s)
    max_spectral_velocity REAL,
    -- Máxima velocidad espectral (cm/s)
    period_at_max_sd REAL,
    -- Periodo en máximo desplazamiento espectral (s)
    max_spectral_displacement REAL,
    -- Máximo desplazamiento espectral (cm)
    predominant_period REAL,
    -- Periodo predominante (s)
    mean_period REAL,
    -- Periodo medio (s)
    spectral_intensity REAL,
    -- Intensidad espectral (cm/s)
    a95 REAL,
    -- Aceleración para 95% de no excedencia (cm/s²)
    v95 REAL,
    -- Velocidad para 95% de no excedencia (cm/s)
    d95 REAL,
    -- Desplazamiento para 95% de no excedencia (cm)
    spectrum_bandwidth REAL,
    -- Ancho de banda del espectro (Hz)
    spectrum_central_period REAL,
    -- Periodo central del espectro (s)
    spectrum_shape_factor REAL,
    -- Factor de forma del espectro
    spectrum_regularity_factor REAL,
    -- Factor de regularidad del espectro
    FOREIGN KEY (response_spectrum_id) REFERENCES response_spectrum(id),
    UNIQUE(response_spectrum_id)
);

-- Tabla para espectros de Fourier de respuesta
CREATE TABLE IF NOT EXISTS fourier_response_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    component TEXT CHECK(
        component IN ('vertical', 'north', 'east', 'resultant')
    ) NOT NULL,
    damping_ratio REAL NOT NULL,
    frequency REAL NOT NULL,
    amplitude REAL NOT NULL,
    phase REAL,
    transfer_function_amplitude REAL,
    -- Amplitud de función de transferencia
    transfer_function_phase REAL,
    -- Fase de función de transferencia
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(
        record_id,
        record_type,
        component,
        damping_ratio,
        frequency
    )
);

-- Tabla para espectros de coherencia
CREATE TABLE IF NOT EXISTS coherence_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id_1 INTEGER NOT NULL,
    record_id_2 INTEGER NOT NULL,
    component_1 TEXT CHECK(component_1 IN ('vertical', 'north', 'east')) NOT NULL,
    component_2 TEXT CHECK(component_2 IN ('vertical', 'north', 'east')) NOT NULL,
    frequency REAL NOT NULL,
    coherence REAL NOT NULL,
    -- Coherencia (0-1)
    phase_difference REAL,
    -- Diferencia de fase (radianes)
    cross_spectrum_amplitude REAL,
    -- Amplitud del espectro cruzado
    cross_spectrum_phase REAL,
    -- Fase del espectro cruzado
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id_1) REFERENCES seismic_acceleration_record(id),
    FOREIGN KEY (record_id_2) REFERENCES seismic_acceleration_record(id),
    UNIQUE(
        record_id_1,
        record_id_2,
        component_1,
        component_2,
        frequency
    )
);

-- Tabla para análisis de estabilidad espectral
CREATE TABLE IF NOT EXISTS spectral_stability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fourier_spectrum_id INTEGER NOT NULL,
    segment_number INTEGER NOT NULL,
    segments_total INTEGER NOT NULL,
    frequency REAL NOT NULL,
    amplitude_mean REAL,
    -- Media de amplitud entre segmentos
    amplitude_stddev REAL,
    -- Desviación estándar de amplitud
    amplitude_cov REAL,
    -- Coeficiente de variación
    phase_mean REAL,
    -- Media de fase
    phase_stddev REAL,
    -- Desviación estándar de fase
    stability_index REAL,
    -- Índice de estabilidad (0-1)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fourier_spectrum_id) REFERENCES fourier_spectrum(id),
    UNIQUE(fourier_spectrum_id, segment_number, frequency)
);

-- Tabla para envolventes de respuesta
CREATE TABLE IF NOT EXISTS response_envelope (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_spectrum_id INTEGER NOT NULL,
    period REAL NOT NULL,
    time REAL NOT NULL,
    -- Tiempo desde inicio (s)
    acceleration_envelope REAL,
    -- Envolvente de aceleración (cm/s²)
    velocity_envelope REAL,
    -- Envolvente de velocidad (cm/s)
    displacement_envelope REAL,
    -- Envolvente de desplazamiento (cm)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_spectrum_id) REFERENCES response_spectrum(id),
    UNIQUE(response_spectrum_id, period, time)
);

-- Tabla para parámetros de contenido frecuencial
CREATE TABLE IF NOT EXISTS frequency_content_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    component TEXT CHECK(component IN ('vertical', 'north', 'east')) NOT NULL,
    mean_frequency REAL,
    -- Frecuencia media (Hz)
    median_frequency REAL,
    -- Frecuencia mediana (Hz)
    modal_frequency REAL,
    -- Frecuencia modal (Hz)
    peak_frequency REAL,
    -- Frecuencia del pico (Hz)
    bandwidth_90 REAL,
    -- Ancho de banda al 90% (Hz)
    frequency_centroid REAL,
    -- Centroide de frecuencia (Hz)
    frequency_stddev REAL,
    -- Desviación estándar de frecuencia (Hz)
    frequency_skewness REAL,
    -- Asimetría de frecuencia
    frequency_kurtosis REAL,
    -- Curtosis de frecuencia
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(record_id, record_type, component)
);

-- Tabla para espectros de velocidad y desplazamiento
CREATE TABLE IF NOT EXISTS velocity_displacement_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    component TEXT CHECK(component IN ('vertical', 'north', 'east')) NOT NULL,
    frequency REAL NOT NULL,
    velocity_amplitude REAL,
    -- Amplitud de velocidad (cm/s)
    displacement_amplitude REAL,
    -- Amplitud de desplazamiento (cm)
    velocity_phase REAL,
    -- Fase de velocidad (radianes)
    displacement_phase REAL,
    -- Fase de desplazamiento (radianes)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(record_id, record_type, component, frequency)
);

-- Tabla para ratios espectrales (H/V, N/E, etc.)
CREATE TABLE IF NOT EXISTS spectral_ratio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('original', 'processed')) NOT NULL,
    ratio_type TEXT CHECK(ratio_type IN ('H/V', 'N/E', 'N/Z', 'E/Z')) NOT NULL,
    frequency REAL NOT NULL,
    ratio_value REAL NOT NULL,
    -- Valor del ratio
    ratio_phase REAL,
    -- Fase del ratio (radianes)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES seismic_acceleration_record(id),
    UNIQUE(record_id, record_type, ratio_type, frequency)
);

-- Vista para resumen de parámetros importantes
CREATE VIEW IF NOT EXISTS vw_seismic_analysis_summary AS
SELECT
    e.event_id,
    e.event_time,
    e.magnitude,
    e.depth,
    s.code as station_code,
    s.name as station_name,
    ar.pga_vertical as pga_vertical_original,
    ar.pga_north as pga_north_original,
    ar.pga_east as pga_east_original,
    par.pga_vertical as pga_vertical_processed,
    par.pga_north as pga_north_processed,
    par.pga_east as pga_east_processed,
    par.pgv_vertical,
    par.pgv_north,
    par.pgv_east,
    par.arias_intensity_vertical,
    par.arias_intensity_north,
    par.arias_intensity_east,
    par.coda_frequency_vertical,
    par.coda_frequency_north,
    par.coda_frequency_east,
    par.corner_frequency_vertical,
    par.corner_frequency_north,
    par.corner_frequency_east,
    par.central_frequency_vertical,
    par.central_frequency_north,
    par.central_frequency_east,
    rs_max.max_spectral_acceleration,
    rs_max.period_at_max_sa,
    rs_max.max_spectral_velocity,
    rs_max.period_at_max_sv
FROM
    seismic_events e
    JOIN seismic_acceleration_record ar ON e.event_id = ar.event_id
    JOIN seismic_station s ON ar.station_id = s.id
    LEFT JOIN processed_acceleration_record par ON ar.id = par.original_record_id
    LEFT JOIN (
        SELECT
            rs.record_id,
            rs.record_type,
            rs.component,
            sp.max_spectral_acceleration,
            sp.period_at_max_sa,
            sp.max_spectral_velocity,
            sp.period_at_max_sv
        FROM
            response_spectrum rs
            JOIN spectral_parameters sp ON rs.id = sp.response_spectrum_id
        WHERE
            rs.component = 'resultant'
            AND rs.damping_ratio = 0.05
    ) rs_max ON ar.id = rs_max.record_id
    AND rs_max.record_type = 'original';

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

CREATE INDEX IF NOT EXISTS idx_processed_record_original ON processed_acceleration_record(original_record_id);

CREATE INDEX IF NOT EXISTS idx_processed_record_filter ON processed_acceleration_record(filter_id);

CREATE INDEX IF NOT EXISTS idx_processed_sample_record ON processed_acceleration_sample(processed_record_id);

CREATE INDEX IF NOT EXISTS idx_fourier_spectrum_record ON fourier_spectrum(record_id, record_type, component);

CREATE INDEX IF NOT EXISTS idx_fourier_spectrum_frequency ON fourier_spectrum(frequency);

CREATE INDEX IF NOT EXISTS idx_response_spectrum_record ON response_spectrum(record_id, record_type, component);

CREATE INDEX IF NOT EXISTS idx_response_spectrum_period ON response_spectrum(period);

CREATE INDEX IF NOT EXISTS idx_response_spectrum_damping ON response_spectrum(damping_ratio);

CREATE INDEX IF NOT EXISTS idx_spectral_parameters_response ON spectral_parameters(response_spectrum_id);

CREATE INDEX IF NOT EXISTS idx_fourier_response_spectrum_record ON fourier_response_spectrum(record_id, record_type, component);

CREATE INDEX IF NOT EXISTS idx_coherence_spectrum_records ON coherence_spectrum(record_id_1, record_id_2);

CREATE INDEX IF NOT EXISTS idx_coherence_spectrum_frequency ON coherence_spectrum(frequency);

CREATE INDEX IF NOT EXISTS idx_spectral_stability_fourier ON spectral_stability(fourier_spectrum_id);

CREATE INDEX IF NOT EXISTS idx_response_envelope_spectrum ON response_envelope(response_spectrum_id);

CREATE INDEX IF NOT EXISTS idx_response_envelope_period ON response_envelope(period);

CREATE INDEX IF NOT EXISTS idx_frequency_content_record ON frequency_content_parameters(record_id, record_type, component);

CREATE INDEX IF NOT EXISTS idx_velocity_displacement_spectrum_record ON velocity_displacement_spectrum(record_id, record_type, component);

CREATE INDEX IF NOT EXISTS idx_spectral_ratio_record ON spectral_ratio(record_id, record_type, ratio_type);