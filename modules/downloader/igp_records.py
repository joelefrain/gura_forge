import re
import requests

import pandas as pd

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from libs.database.seismic_records import SeismicRecordsHandler

from libs.helpers.metadata_helpers import style_metadata_property
from libs.config.config_logger import get_logger, log_execution_time

from libs.config.config_variables import ACCEL_RECORD_STORE, TIMEOUT_API_REQUEST, MAX_WORKERS

logger = get_logger()


@dataclass
class StationInfo:
    """Información de una estación sísmica"""

    code: str
    name: str
    latitude: float
    longitude: float
    network: str


@dataclass
class ProcessResult:
    """Resultado del procesamiento de una estación"""

    station_code: str
    success: bool
    samples_count: int = 0
    error: Optional[str] = None
    download_time: float = 0.0
    parse_time: float = 0.0
    save_time: float = 0.0


class IGPDownloader:
    """Descargador de registros de aceleración del Instituto Geofísico del Perú"""

    API_URL = (
        "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/breadcrumbstations2"
    )
    FILE_BASE_URL = "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/file"

    # Regex precompilados
    _SECTION_PATTERN = re.compile(r"\d\.\s*")
    _SAMPLING_PATTERN = re.compile(r"(\d+)")
    _DATA_START_PATTERN = re.compile(r"Z\s+N\s+E\s*\n", re.MULTILINE)
    _FIELD_PATTERN_CACHE = {}  # Cache de patrones por campo

    def __init__(self, max_workers: int = MAX_WORKERS):
        """
        Args:
            max_workers: Número de threads para procesamiento paralelo (default: 5)
        """
        self.max_workers = max_workers
        self.accel_dir = ACCEL_RECORD_STORE / "igp"
        self.accel_dir.mkdir(parents=True, exist_ok=True)

        # Métricas de procesamiento
        self.total_stations = 0
        self.successful_stations = 0
        self.failed_stations = 0
        self.total_samples = 0
        self.total_download_time = 0.0
        self.total_parse_time = 0.0
        self.total_save_time = 0.0
        self.failed_station_list = []

    def _get_db_handler(self) -> SeismicRecordsHandler:
        """Obtiene un handler de BD thread-safe"""
        return SeismicRecordsHandler()

    def _get_session(self) -> requests.Session:
        """Obtiene una sesión thread-safe"""
        session = requests.Session()
        # Configurar pool de conexiones para mejor rendimiento
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10, pool_maxsize=20, max_retries=2
        )
        session.mount("https://", adapter)
        return session

    def fetch_event_data(self, event_time: datetime) -> Optional[Dict]:
        """Obtiene los datos del evento desde la API"""
        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.igp.gob.pe",
            "Referer": f"https://www.igp.gob.pe/servicios/aceldat-peru/reportes-registros-acelerometricos?date={datetime_str}",
        }

        session = self._get_session()
        try:
            response = session.post(
                self.API_URL,
                json={"datetime": datetime_str},
                headers=headers,
                timeout=TIMEOUT_API_REQUEST,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Datos obtenidos: {data.get('_id', 'sin ID')}")
            return data

        except (requests.RequestException, ValueError) as e:
            logger.error(f"Error obteniendo datos del evento: {e}")
            return None
        finally:
            session.close()

    def _build_download_url(
        self,
        event_id: Optional[int],
        event_time: datetime,
        station_code: str,
        network: str,
    ) -> str:
        """Construye la URL de descarga"""
        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")
        event_id_str = str(event_id) if event_id else "undefined"
        return f"{self.FILE_BASE_URL}/{event_id_str}_{datetime_str}_{station_code}_{network}.txt"

    def extract_stations(self, event_data: Dict) -> List[StationInfo]:
        """Extrae información de estaciones"""
        stations = []

        for stat in event_data.get("stats", []):
            try:
                code = stat.get("cod")
                name = stat.get("nom")
                coordinates = stat.get("pos", {}).get("coordinates", [])

                if code and name and len(coordinates) >= 2:
                    stations.append(
                        StationInfo(
                            code=code,
                            name=name,
                            latitude=coordinates[1],
                            longitude=coordinates[0],
                            network=stat.get("net", "PE"),
                        )
                    )
            except (KeyError, IndexError, ValueError):
                continue

        logger.info(f"Estaciones encontradas: {len(stations)}")
        return stations

    def _download_file(
        self, session: requests.Session, url: str, filename: str
    ) -> Optional[Path]:
        """Descarga un archivo"""
        try:
            response = session.get(url, timeout=TIMEOUT_API_REQUEST)
            response.raise_for_status()

            file_path = self.accel_dir / filename
            file_path.write_bytes(response.content)
            return file_path

        except requests.RequestException as e:
            logger.error(f"Error descargando {filename}: {e}")
            return None

    def _get_field_pattern(self, field: str) -> re.Pattern:
        """Obtiene patrón compilado desde cache"""
        if field not in self._FIELD_PATTERN_CACHE:
            self._FIELD_PATTERN_CACHE[field] = re.compile(
                rf"{field}\s*:\s*(.+?)(?=\n|\r|$)", re.IGNORECASE
            )
        return self._FIELD_PATTERN_CACHE[field]

    def _extract_section(
        self, content: str, section_pattern: str, fields: List[str]
    ) -> Dict:
        """Extrae una sección del archivo"""
        section_match = re.search(section_pattern, content, re.IGNORECASE)
        if not section_match:
            return {}

        start_pos = section_match.end()
        next_section = self._SECTION_PATTERN.search(content[start_pos:])
        end_pos = start_pos + next_section.start() if next_section else len(content)
        section_text = content[start_pos:end_pos]

        result = {}
        for field in fields:
            match = self._get_field_pattern(field).search(section_text)
            if match:
                result[field] = match.group(1).strip()
        return result

    def _extract_acceleration_samples(
        self, content: str
    ) -> List[Tuple[float, float, float]]:
        """Extrae muestras de aceleración optimizado"""
        match = self._DATA_START_PATTERN.search(content)
        if not match:
            return []

        # Encontrar inicio de datos numéricos
        data_start = match.end()
        lines = content[data_start:].split("\n")

        samples = []
        # Procesar líneas hasta encontrar una inválida
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 3:
                break
            try:
                samples.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                break

        return samples

    def _parse_acceleration_file(self, file_path: Path) -> Optional[Dict]:
        """Parsea archivo de aceleración"""
        try:
            content = file_path.read_text(encoding="utf-8")

            acceleration = self._extract_section(
                content,
                r"3\.\s*REGISTRO DE ACELERACIÓN",
                ["NÚMERO DE MUESTRAS", "MUESTREO", "PGA"],
            )

            if not acceleration:
                return None

            return {
                "acceleration": acceleration,
                "samples": self._extract_acceleration_samples(content),
            }

        except Exception as e:
            logger.error(f"Error parseando {file_path.name}: {e}")
            return None

    def _extract_pga_values(self, pga_str: str) -> Tuple[float, float, float]:
        """Extrae valores PGA"""
        try:
            values = pga_str.split()
            return (float(values[0]), float(values[1]), float(values[2]))
        except (IndexError, ValueError):
            return (0.0, 0.0, 0.0)

    def _extract_sampling_frequency(self, muestreo_str: str) -> float:
        """Extrae frecuencia de muestreo"""
        match = self._SAMPLING_PATTERN.search(muestreo_str)
        return float(match.group(1)) if match else 100.0

    def _save_to_database(
        self,
        db: SeismicRecordsHandler,
        event_id: str,
        station_info: StationInfo,
        parsed_data: Dict,
        file_path: Path,
    ) -> bool:
        """Guarda datos en BD"""
        try:
            station_id = db.insert_or_update_seismic_station(
                code=station_info.code,
                name=station_info.name,
                latitude=station_info.latitude,
                longitude=station_info.longitude,
            )

            if not station_id:
                return False

            accel_data = parsed_data["acceleration"]
            pga_values = self._extract_pga_values(accel_data.get("PGA", ""))

            record_id = db.insert_seismic_acceleration_record(
                event_id=event_id,
                station_id=station_id,
                num_samples=int(accel_data.get("NÚMERO DE MUESTRAS", "0")),
                sampling_frequency=self._extract_sampling_frequency(
                    accel_data.get("MUESTREO", "")
                ),
                pga_vertical=pga_values[0],
                pga_north=pga_values[1],
                pga_east=pga_values[2],
                baseline_correction=True,
                file_path=str(file_path),
            )

            if record_id:
                db.insert_acceleration_samples(record_id, parsed_data["samples"])
                return True

            return False

        except Exception as e:
            logger.error(f"Error guardando {station_info.code}: {e}")
            return False

    def _process_single_station(
        self,
        event_id: str,
        event_time: datetime,
        api_event_id: Optional[int],
        station_info: StationInfo,
    ) -> ProcessResult:
        """Procesa una estación individual (thread-safe)"""
        import time

        session = self._get_session()
        db = self._get_db_handler()

        download_time = parse_time = save_time = 0.0
        samples_count = 0

        try:
            # Construir URL
            download_url = self._build_download_url(
                api_event_id, event_time, station_info.code, station_info.network
            )

            # Descargar archivo
            start = time.time()
            filename = f"{event_id}_{station_info.code}.txt"
            file_path = self._download_file(session, download_url, filename)
            download_time = time.time() - start

            if not file_path:
                return ProcessResult(station_info.code, False, error="Descarga fallida")

            # Parsear archivo
            start = time.time()
            parsed_data = self._parse_acceleration_file(file_path)
            parse_time = time.time() - start

            if not parsed_data:
                return ProcessResult(
                    station_info.code,
                    False,
                    download_time=download_time,
                    error="Parseo fallido",
                )

            samples_count = len(parsed_data["samples"])

            # Guardar en BD
            start = time.time()
            success = self._save_to_database(
                db, event_id, station_info, parsed_data, file_path
            )
            save_time = time.time() - start

            if success:
                logger.info(f"✓ {station_info.code}: {samples_count} muestras")
                return ProcessResult(
                    station_info.code,
                    True,
                    samples_count=samples_count,
                    download_time=download_time,
                    parse_time=parse_time,
                    save_time=save_time,
                )
            else:
                return ProcessResult(
                    station_info.code,
                    False,
                    download_time=download_time,
                    parse_time=parse_time,
                    error="Error guardando en BD",
                )

        except Exception as e:
            logger.error(f"Error procesando {station_info.code}: {e}")
            return ProcessResult(
                station_info.code,
                False,
                download_time=download_time,
                parse_time=parse_time,
                save_time=save_time,
                error=str(e),
            )
        finally:
            session.close()

    @log_execution_time
    def process_event(
        self, event_id: str, event_time: datetime, catalog: str = "igp"
    ) -> bool:
        """Procesa un evento completo con procesamiento paralelo"""
        logger.info(f"Iniciando proceso del evento {event_id} - {catalog}")

        # Obtener datos del evento
        event_data = self.fetch_event_data(event_time)
        if not event_data:
            logger.error(f"No se pudieron obtener datos del evento {event_id}")
            return False

        # Extraer estaciones
        stations = self.extract_stations(event_data)
        if not stations:
            logger.warning(f"No se encontraron estaciones para {event_id}")
            return False

        api_event_id = event_data.get("_id")
        self.total_stations = len(stations)

        # Procesar estaciones en paralelo
        logger.info(
            f"Procesando {len(stations)} estaciones con {self.max_workers} workers..."
        )

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_single_station,
                    event_id,
                    event_time,
                    api_event_id,
                    station,
                ): station
                for station in stations
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    station = futures[future]
                    logger.error(f"Excepción procesando {station.code}: {e}")
                    results.append(ProcessResult(station.code, False, error=str(e)))

        # Calcular métricas
        self._calculate_metrics(results)

        # Resumen
        logger.info(
            f"Proceso completado: {self.successful_stations} exitosos, "
            f"{self.failed_stations} fallidos de {self.total_stations} totales"
        )

        if self.failed_stations > 0:
            logger.warning(
                f"Estaciones fallidas: {', '.join(self.failed_station_list)}"
            )

        return self.successful_stations > 0

    def _calculate_metrics(self, results: List[ProcessResult]):
        """Calcula métricas de procesamiento"""
        self.successful_stations = sum(1 for r in results if r.success)
        self.failed_stations = len(results) - self.successful_stations
        self.total_samples = sum(r.samples_count for r in results if r.success)
        self.total_download_time = sum(r.download_time for r in results)
        self.total_parse_time = sum(r.parse_time for r in results)
        self.total_save_time = sum(r.save_time for r in results)
        self.failed_station_list = [r.station_code for r in results if not r.success]

    @style_metadata_property
    def metadata(self):
        """Devuelve resumen tabulado del procesamiento"""
        success_rate = (
            (self.successful_stations / self.total_stations * 100)
            if self.total_stations > 0
            else 0
        )

        avg_download = (
            self.total_download_time / self.total_stations
            if self.total_stations > 0
            else 0
        )
        avg_parse = (
            self.total_parse_time / self.total_stations
            if self.total_stations > 0
            else 0
        )
        avg_save = (
            self.total_save_time / self.total_stations if self.total_stations > 0 else 0
        )

        data = {
            "Total estaciones": [self.total_stations],
            "Exitosas": [self.successful_stations],
            "Fallidas": [self.failed_stations],
            "Tasa éxito (%)": [f"{success_rate:.1f}"],
            "Total muestras": [self.total_samples],
            "Tiempo descarga (s)": [f"{self.total_download_time:.2f}"],
            "Tiempo parseo (s)": [f"{self.total_parse_time:.2f}"],
            "Tiempo guardado (s)": [f"{self.total_save_time:.2f}"],
            "Promedio/estación (s)": [f"{avg_download + avg_parse + avg_save:.2f}"],
        }
        return pd.DataFrame(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  
