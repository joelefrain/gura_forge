import re
import requests

import pandas as pd

from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dataclasses import dataclass, field
from threading import Lock

from libs.database.seismic_records import SeismicRecordsHandler

from libs.config.config_logger import get_logger
from libs.helpers.metadata_helpers import style_metadata_property

from libs.config.config_variables import (
    ACCEL_RECORD_STORE,
    TIMEOUT_API_REQUEST,
    MAX_WORKERS,
)

logger = get_logger()


class StationProcessStatus(Enum):
    """Estados de procesamiento de estaciones"""

    SUCCESS = "exitosa"
    FILE_NOT_FOUND = "archivo_no_encontrado"
    PARSE_ERROR = "error_parseo"
    DB_STATION_SAVE_ERROR = "error_guardar_estacion"
    DB_RECORD_SAVE_ERROR = "error_guardar_registro"
    DB_SAMPLES_SAVE_ERROR = "error_guardar_muestras"


@dataclass
class StationInfo:
    """Información de una estación sísmica"""

    code: str
    name: str
    latitude: float
    longitude: float
    network: str


@dataclass
class StationProcessResult:
    """Resultado del procesamiento de una estación"""

    station_code: str
    status: StationProcessStatus
    samples_count: int = 0
    station_id: Optional[int] = None
    record_id: Optional[int] = None
    error_detail: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == StationProcessStatus.SUCCESS


@dataclass
class ParsedAccelerationData:
    """Datos parseados de un archivo de aceleración"""

    acceleration_metadata: Dict[str, str]
    samples: List[Tuple[float, float, float]]

    @property
    def sample_count(self) -> int:
        return len(self.samples)


@dataclass
class EventProcessMetrics:
    """Métricas de procesamiento de un evento"""

    total_events_requested: int = 0
    events_downloaded: int = 0
    events_failed_download: int = 0
    events_parse_error: int = 0
    stations_processed: int = 0
    stations_saved_db: int = 0
    stations_file_not_found: int = 0
    stations_parse_error: int = 0
    stations_db_error: int = 0
    total_samples: int = 0
    failed_details: Dict[str, List[str]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def add_failed(self, category: str, station_code: str, error: str):
        """Registra un fallo categorizado (thread-safe)"""
        with self._lock:
            if category not in self.failed_details:
                self.failed_details[category] = []
            self.failed_details[category].append(f"{station_code}: {error}")

    def record_success(self, samples_count: int):
        """Registra un guardado exitoso"""
        with self._lock:
            self.stations_saved_db += 1
            self.total_samples += samples_count

    def record_file_not_found(self, station_code: str, error: str):
        """Registra archivo no encontrado"""
        with self._lock:
            self.stations_file_not_found += 1
        self.add_failed("Archivo no encontrado", station_code, error)

    def record_parse_error(self, station_code: str, error: str):
        """Registra error de parseo"""
        with self._lock:
            self.stations_parse_error += 1
        self.add_failed("Error de parseo", station_code, error)

    def record_db_error(self, station_code: str, error: str):
        """Registra error de BD"""
        with self._lock:
            self.stations_db_error += 1
        self.add_failed("Error de BD", station_code, error)


class FileDownloader:
    """Responsable de descargar archivos"""

    __slots__ = ("output_dir", "base_url", "timeout", "_session_pool")

    def __init__(
        self, output_dir: Path, base_url: str, timeout: int = TIMEOUT_API_REQUEST
    ):
        self.output_dir = output_dir
        self.base_url = base_url
        self.timeout = timeout
        self._session_pool = []

    def build_url(
        self,
        event_id: Optional[int],
        event_time: datetime,
        station_code: str,
        network: str,
    ) -> str:
        """Construye URL de descarga"""
        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")
        event_id_str = str(event_id) if event_id else "undefined"
        return f"{self.base_url}/{event_id_str}_{datetime_str}_{station_code}_{network}.txt"

    def download(
        self, session: requests.Session, url: str, filename: str
    ) -> Optional[Path]:
        """Descarga un archivo"""
        try:
            response = session.get(url, timeout=self.timeout, stream=False)
            response.raise_for_status()

            file_path = self.output_dir / filename
            file_path.write_bytes(response.content)
            return file_path

        except requests.RequestException:
            return None


class AccelerationFileParser:
    """Responsable de parsear archivos de aceleración con optimizaciones"""

    __slots__ = (
        "_field_pattern_cache",
        "_section_pattern",
        "_sampling_pattern",
        "_data_start_pattern",
    )

    # Patrones compilados a nivel de clase
    _SECTION_PATTERN = re.compile(r"\d\.\s*")
    _SAMPLING_PATTERN = re.compile(r"(\d+)")
    _DATA_START_PATTERN = re.compile(r"Z\s+N\s+E\s*\n", re.MULTILINE)

    def __init__(self):
        self._field_pattern_cache: Dict[str, re.Pattern] = {}

    def parse(self, file_path: Path) -> Optional[ParsedAccelerationData]:
        """Parsea archivo completo - optimizado"""
        try:
            # Leer una sola vez
            content = file_path.read_text(encoding="utf-8")

            # Extraer datos en una pasada
            acceleration_data = self._extract_acceleration_section(content)
            if not acceleration_data:
                return None

            samples = self._extract_samples(content)
            return ParsedAccelerationData(acceleration_data, samples)

        except Exception:
            return None

    def _extract_acceleration_section(self, content: str) -> Optional[Dict[str, str]]:
        """Extrae sección 3 - REGISTRO con compilación lazy"""
        pattern = re.compile(r"3\.\s*REGISTRO\s", re.IGNORECASE)
        match = pattern.search(content)
        if not match:
            return None

        start_pos = match.end()
        next_section = self._SECTION_PATTERN.search(content, start_pos)
        end_pos = next_section.start() if next_section else len(content)
        section_text = content[start_pos:end_pos]

        # Extrae solo los campos necesarios
        result = {}
        for field in ("NÚMERO DE MUESTRAS", "MUESTREO", "PGA"):
            pattern = self._get_field_pattern(field)
            match = pattern.search(section_text)
            if match:
                result[field] = match.group(1).strip()

        return result if result else None

    def _extract_samples(self, content: str) -> List[Tuple[float, float, float]]:
        """Extrae muestras con parsing optimizado"""
        match = self._DATA_START_PATTERN.search(content)
        if not match:
            return []

        lines = content[match.end() :].split("\n")
        samples = []
        samples_append = samples.append  # Caché de método

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            parts = stripped.split()
            if len(parts) < 3:
                break

            try:
                samples_append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                break

        return samples

    def _get_field_pattern(self, field: str) -> re.Pattern:
        """Obtiene patrón compilado desde cache"""
        if field not in self._field_pattern_cache:
            self._field_pattern_cache[field] = re.compile(
                rf"{field}\s*:\s*(.+?)(?=\n|\r|$)", re.IGNORECASE
            )
        return self._field_pattern_cache[field]


class DatabaseBatch:
    """Batch processor para inserciones eficientes"""

    __slots__ = ("db", "batch_size", "_station_cache", "_lock")

    def __init__(self, db: SeismicRecordsHandler, batch_size: int = 50):
        self.db = db
        self.batch_size = batch_size
        self._station_cache: Dict[str, int] = {}
        self._lock = Lock()

    def get_or_create_station(self, station_info: StationInfo) -> Optional[int]:
        """Obtiene o crea estación con cache local"""
        with self._lock:
            if station_info.code in self._station_cache:
                return self._station_cache[station_info.code]

        try:
            station_id = self.db.insert_or_update_seismic_station(
                code=station_info.code,
                name=station_info.name,
                latitude=station_info.latitude,
                longitude=station_info.longitude,
            )
            if station_id:
                with self._lock:
                    self._station_cache[station_info.code] = station_id
            return station_id
        except Exception:
            return None

    def save_acceleration_record(
        self,
        event_id: str,
        station_id: int,
        parsed_data: ParsedAccelerationData,
        file_path: Path,
    ) -> Optional[int]:
        """Guarda registro de aceleración"""
        try:
            accel_data = parsed_data.acceleration_metadata

            # Extracciones inline para evitar llamadas
            pga_parts = accel_data.get("PGA", "0 0 0").split()
            pga_values = (
                float(pga_parts[0]) if len(pga_parts) > 0 else 0.0,
                float(pga_parts[1]) if len(pga_parts) > 1 else 0.0,
                float(pga_parts[2]) if len(pga_parts) > 2 else 0.0,
            )

            # Frecuencia de muestreo
            muestreo_match = re.search(r"(\d+)", accel_data.get("MUESTREO", "100"))
            sampling_freq = float(muestreo_match.group(1)) if muestreo_match else 100.0

            record_id = self.db.insert_seismic_acceleration_record(
                event_id=event_id,
                station_id=station_id,
                num_samples=int(accel_data.get("NÚMERO DE MUESTRAS", "0")),
                sampling_frequency=sampling_freq,
                pga_vertical=pga_values[0],
                pga_north=pga_values[1],
                pga_east=pga_values[2],
                baseline_correction=True,
                file_path=str(file_path),
            )
            return record_id
        except Exception:
            return None

    def save_samples(self, record_id: int, samples: List[Tuple]) -> bool:
        """Guarda muestras"""
        try:
            self.db.insert_acceleration_samples(record_id, samples)
            return True
        except Exception:
            return False


class StationProcessor:
    """Responsable de procesar estaciones individuales - optimizado"""

    __slots__ = ("downloader", "parser", "batch_db", "_session")

    def __init__(
        self,
        file_downloader: FileDownloader,
        parser: AccelerationFileParser,
        batch_db: DatabaseBatch,
    ):
        self.downloader = file_downloader
        self.parser = parser
        self.batch_db = batch_db
        self._session = self._build_session()

    def process(
        self,
        event_id: str,
        event_time: datetime,
        api_event_id: Optional[int],
        station_info: StationInfo,
    ) -> StationProcessResult:
        """Procesa estación con sesión reutilizada"""
        try:
            # Paso 1: Descargar
            url = self.downloader.build_url(
                api_event_id, event_time, station_info.code, station_info.network
            )
            filename = f"{event_id}_{station_info.code}.txt"
            file_path = self.downloader.download(self._session, url, filename)

            if not file_path:
                return StationProcessResult(
                    station_info.code,
                    StationProcessStatus.FILE_NOT_FOUND,
                    error_detail="Archivo no descargado",
                )

            # Paso 2: Parsear
            parsed_data = self.parser.parse(file_path)
            if not parsed_data:
                return StationProcessResult(
                    station_info.code,
                    StationProcessStatus.PARSE_ERROR,
                    error_detail="Error parseando archivo",
                )

            # Paso 3: Guardar en BD
            station_id = self.batch_db.get_or_create_station(station_info)
            if not station_id:
                return StationProcessResult(
                    station_info.code,
                    StationProcessStatus.DB_STATION_SAVE_ERROR,
                    error_detail="Error guardando estación",
                )

            record_id = self.batch_db.save_acceleration_record(
                event_id, station_id, parsed_data, file_path
            )
            if not record_id:
                return StationProcessResult(
                    station_info.code,
                    StationProcessStatus.DB_RECORD_SAVE_ERROR,
                    station_id=station_id,
                    error_detail="Error guardando registro",
                )

            samples_saved = self.batch_db.save_samples(record_id, parsed_data.samples)
            if not samples_saved:
                return StationProcessResult(
                    station_info.code,
                    StationProcessStatus.DB_SAMPLES_SAVE_ERROR,
                    station_id=station_id,
                    record_id=record_id,
                    samples_count=parsed_data.sample_count,
                    error_detail="Error guardando muestras",
                )

            return StationProcessResult(
                station_info.code,
                StationProcessStatus.SUCCESS,
                station_id=station_id,
                record_id=record_id,
                samples_count=parsed_data.sample_count,
            )

        except Exception as e:
            return StationProcessResult(
                station_info.code,
                StationProcessStatus.DB_STATION_SAVE_ERROR,
                error_detail=str(e),
            )

    @staticmethod
    def _build_session() -> requests.Session:
        """Construye sesión con conexión pooled"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=50, max_retries=1
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def close(self):
        """Cierra sesión"""
        if self._session:
            self._session.close()


class EventAPIClient:
    """Cliente de API optimizado"""

    __slots__ = ("api_url", "timeout", "_session")

    def __init__(self, api_url: str, timeout: int = TIMEOUT_API_REQUEST):
        self.api_url = api_url
        self.timeout = timeout
        self._session = self._build_session()

    def fetch_event_data(self, event_time: datetime) -> Optional[Dict]:
        """Obtiene datos del evento"""
        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")

        try:
            response = self._session.post(
                self.api_url,
                json={"datetime": datetime_str},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Origin": "https://www.igp.gob.pe",
                    "Referer": f"https://www.igp.gob.pe/servicios/aceldat-peru/reportes-registros-acelerometricos?date={datetime_str}",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    @staticmethod
    def _build_session() -> requests.Session:
        """Construye sesión configurada"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10, pool_maxsize=20, max_retries=2
        )
        session.mount("https://", adapter)
        return session

    def close(self):
        """Cierra sesión"""
        if self._session:
            self._session.close()


class StationExtractor:
    """Extractor de estaciones - optimizado"""

    @staticmethod
    def extract(event_data: Dict) -> List[StationInfo]:
        """Extrae estaciones eficientemente"""
        stations = []

        for stat in event_data.get("stats", []):
            code = stat.get("cod")
            if not code:
                continue

            name = stat.get("nom")
            coords = stat.get("pos", {}).get("coordinates", [])

            if name and len(coords) >= 2:
                stations.append(
                    StationInfo(
                        code=code,
                        name=name,
                        latitude=coords[1],
                        longitude=coords[0],
                        network=stat.get("net", "PE"),
                    )
                )

        return stations


class IGPDownloader:
    """Orquestador principal optimizado para velocidad"""

    API_URL = (
        "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/breadcrumbstations2"
    )
    FILE_BASE_URL = "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/file"

    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self.accel_dir = ACCEL_RECORD_STORE / "igp"
        self.accel_dir.mkdir(parents=True, exist_ok=True)

        self.api_client = EventAPIClient(self.API_URL)
        self.file_downloader = FileDownloader(self.accel_dir, self.FILE_BASE_URL)
        self.parser = AccelerationFileParser()
        self.metrics = EventProcessMetrics()

    def process_event(
        self, event_id: str, event_time: datetime, catalog: str = "igp"
    ) -> bool:
        """Procesa evento con máxima eficiencia"""
        self.metrics.total_events_requested += 1

        event_data = self.api_client.fetch_event_data(event_time)
        if not event_data:
            self.metrics.events_failed_download += 1
            return False

        self.metrics.events_downloaded += 1

        stations = StationExtractor.extract(event_data)
        if not stations:
            self.metrics.events_parse_error += 1
            return False

        self.metrics.stations_processed = len(stations)

        # Procesar con batch DB
        batch_db = DatabaseBatch(SeismicRecordsHandler())
        results = self._process_stations_parallel(
            event_id, event_time, event_data.get("_id"), stations, batch_db
        )

        self._update_metrics(results)

        return self.metrics.stations_saved_db > 0

    def _process_stations_parallel(
        self,
        event_id: str,
        event_time: datetime,
        api_event_id: Optional[int],
        stations: List[StationInfo],
        batch_db: DatabaseBatch,
    ) -> List[StationProcessResult]:
        """Procesamiento paralelo con procesador reutilizable"""
        results = []
        processor = StationProcessor(self.file_downloader, self.parser, batch_db)

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(
                        processor.process, event_id, event_time, api_event_id, station
                    )
                    for station in stations
                ]

                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        # Fallback silencioso
                        pass

            return results
        finally:
            processor.close()

    def _update_metrics(self, results: List[StationProcessResult]):
        """Actualiza métricas eficientemente"""
        for result in results:
            if result.success:
                self.metrics.record_success(result.samples_count)
            elif result.status == StationProcessStatus.FILE_NOT_FOUND:
                self.metrics.record_file_not_found(result.station_code, "")
            elif result.status == StationProcessStatus.PARSE_ERROR:
                self.metrics.record_parse_error(result.station_code, "")
            else:
                self.metrics.record_db_error(result.station_code, "")

    @style_metadata_property
    def metadata(self):
        """Resumen tabular"""
        data = {
            "Eventos solicitados": [self.metrics.total_events_requested],
            "Eventos descargados": [self.metrics.events_downloaded],
            "Eventos fallidos (descarga)": [self.metrics.events_failed_download],
            "Eventos fallidos (parseo)": [self.metrics.events_parse_error],
            "Estaciones procesadas": [self.metrics.stations_processed],
            "Estaciones guardadas BD": [self.metrics.stations_saved_db],
            "Estaciones sin archivo": [self.metrics.stations_file_not_found],
            "Estaciones error parseo": [self.metrics.stations_parse_error],
            "Estaciones error BD": [self.metrics.stations_db_error],
            "Total muestras": [self.metrics.total_samples],
        }
        return pd.DataFrame(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api_client.close()
