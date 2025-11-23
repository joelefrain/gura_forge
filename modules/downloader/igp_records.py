import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from libs.database.seismic_records import SeismicRecordsHandler
from libs.config.config_variables import ACCEL_RECORD_STORE, TIMEOUT_API_REQUEST
from libs.config.config_logger import get_logger

logger = get_logger()


@dataclass
class StationInfo:
    """Información de una estación sísmica"""

    code: str
    name: str
    latitude: float
    longitude: float
    network: str


class IGPDownloader:
    """Descargador de registros de aceleración del Instituto Geofísico del Perú"""

    API_URL = (
        "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/breadcrumbstations2"
    )
    FILE_BASE_URL = "https://www.igp.gob.pe/servicios/api-acelerometrica/ran/file"

    def __init__(self):
        self.db = SeismicRecordsHandler()
        self.session = requests.Session()
        self.accel_dir = ACCEL_RECORD_STORE / "igp"
        self.accel_dir.mkdir(parents=True, exist_ok=True)

    def fetch_event_data(self, event_time: datetime) -> Optional[Dict]:
        """Obtiene los datos del evento desde la API de breadcrumbs"""

        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.igp.gob.pe",
            "Referer": f"https://www.igp.gob.pe/servicios/aceldat-peru/reportes-registros-acelerometricos?date={datetime_str}",
        }

        body = f'{{"datetime":"{datetime_str}"}}'

        try:
            response = self.session.post(
                self.API_URL, data=body, headers=headers, timeout=TIMEOUT_API_REQUEST
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Datos del evento obtenidos: {data.get('_id', 'sin ID')}")
            return data

        except requests.RequestException as e:
            logger.error(f"Error obteniendo datos del evento: {e}")
            return None
        except ValueError as e:
            logger.error(f"Error parseando JSON: {e}")
            return None

    def build_download_url(
        self,
        event_id: Optional[int],
        event_time: datetime,
        station_code: str,
        network: str,
    ) -> str:
        """Construye la URL de descarga del archivo TXT"""

        datetime_str = event_time.strftime("%Y%m%d_%H%M%S")

        if event_id is None:
            event_id_str = "undefined"
        else:
            event_id_str = str(event_id)

        filename = f"{event_id_str}_{datetime_str}_{station_code}_{network}.txt"
        return f"{self.FILE_BASE_URL}/{filename}"

    def extract_stations(self, event_data: Dict) -> List[StationInfo]:
        """Extrae información de estaciones desde los datos del evento"""

        stations = []

        stats_list = event_data.get("stats", [])

        for stat in stats_list:
            try:
                code = stat.get("cod")
                name = stat.get("nom")
                network = stat.get("net", "PE")
                pos = stat.get("pos", {})
                coordinates = pos.get("coordinates", [])

                if not code or not name or len(coordinates) < 2:
                    logger.warning(f"Datos incompletos para estación: {stat}")
                    continue

                # coordinates es [longitude, latitude]
                longitude, latitude = coordinates[0], coordinates[1]

                station = StationInfo(
                    code=code,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    network=network,
                )

                stations.append(station)
                logger.info(f"Estación encontrada: {code} - {name}")

            except (KeyError, IndexError, ValueError) as e:
                logger.warning(f"Error procesando estación: {e}")
                continue

        return stations

    def download_file(self, url: str, filename: str) -> Optional[Path]:
        """Descarga un archivo y lo guarda localmente"""
        try:
            response = self.session.get(url, timeout=TIMEOUT_API_REQUEST)
            response.raise_for_status()

            file_path = self.accel_dir / filename
            file_path.write_bytes(response.content)

            logger.info(f"Archivo descargado: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Error descargando archivo {url}: {e}")
            return None

    def parse_acceleration_file(self, file_path: Path) -> Optional[Dict]:
        """Parsea un archivo TXT de aceleración y extrae su información"""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            data = {
                "station": self._extract_section(
                    content,
                    r"1\.\s*ESTACIÓN SÍSMICA",
                    ["NOMBRE", "CÓDIGO", "LATITUD", "LONGITUD"],
                ),
                "event": self._extract_section(
                    content,
                    r"2\.\s*SISMO",
                    [
                        "FECHA LOCAL",
                        "HORA LOCAL",
                        "LATITUD",
                        "LONGITUD",
                        "PROFUNDIDAD",
                        "MAGNITUD",
                    ],
                ),
                "acceleration": self._extract_section(
                    content,
                    r"3\.\s*REGISTRO DE ACELERACIÓN",
                    [
                        "TIEMPO DE INICIO",
                        "NÚMERO DE MUESTRAS",
                        "MUESTREO",
                        "CORRECCIÓN POR LÍNEA BASE",
                        "UNIDADES",
                        "PGA",
                    ],
                ),
                "samples": self._extract_acceleration_samples(content),
            }
            return (
                data
                if data["station"] and data["event"] and data["acceleration"]
                else None
            )

        except Exception as e:
            logger.error(f"Error parseando archivo {file_path}: {e}")
            return None

    def _extract_section(
        self, content: str, section_pattern: str, fields: List[str]
    ) -> Dict:
        """Extrae una sección del archivo de texto"""
        section_match = re.search(section_pattern, content, re.IGNORECASE)
        if not section_match:
            return {}

        start_pos = section_match.end()
        next_section = re.search(r"\d\.\s*", content[start_pos:])
        end_pos = start_pos + next_section.start() if next_section else len(content)
        section_text = content[start_pos:end_pos]

        result = {}
        for field in fields:
            pattern = rf"{field}\s*:\s*(.+?)(?=\n|\r|$)"
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
        return result

    def _extract_acceleration_samples(
        self, content: str
    ) -> List[Tuple[float, float, float]]:
        """Extrae las muestras de aceleración (Z, N, E)"""
        start_match = re.search(
            r"REGISTROS POR COMPONENTE.*?\n(.*?)Z\s+N\s+E", content, re.DOTALL
        )
        if not start_match:
            return []

        data_start = content.find(start_match.group(0)) + len(start_match.group(0))
        remaining = content[data_start:]

        samples = []
        lines = remaining.strip().split("\n")

        for line in lines:
            values = line.split()
            if len(values) >= 3:
                try:
                    z, n, e = float(values[0]), float(values[1]), float(values[2])
                    samples.append((z, n, e))
                except ValueError:
                    break

        return samples

    def process_event(
        self, event_id: str, event_time: datetime, catalog: str = "igp"
    ) -> bool:
        """
        Procesa un evento completo: obtiene datos de la API, descarga archivos,
        parsea y guarda en BD
        """
        logger.info(f"Iniciando proceso del evento {event_id} - {catalog}")

        # Obtener datos del evento desde la API
        event_data = self.fetch_event_data(event_time)
        if not event_data:
            logger.error(f"No se pudieron obtener datos del evento {event_id}")
            return False

        # Extraer información de estaciones
        stations = self.extract_stations(event_data)
        if not stations:
            logger.warning(f"No se encontraron estaciones para el evento {event_id}")
            return False

        logger.info(
            f"Se encontraron {len(stations)} estaciones para el evento {event_id}"
        )

        # Obtener el ID del evento desde la API (puede ser None)
        api_event_id = event_data.get("_id")

        # Procesar cada estación
        processed_count = 0
        for station_info in stations:
            # Construir URL de descarga
            download_url = self.build_download_url(
                api_event_id, event_time, station_info.code, station_info.network
            )

            logger.info(f"URL de descarga: {download_url}")

            # Descargar archivo
            filename = f"{event_id}_{station_info.code}.txt"
            file_path = self.download_file(download_url, filename)

            if not file_path:
                continue

            try:
                parsed_data = self.parse_acceleration_file(file_path)
                self._save_to_database(event_id, station_info, parsed_data, file_path)
                processed_count += 1

            except Exception as e:
                logger.exception(f"Error al parsear archivo {filename}: {e}")
                continue

        logger.info(
            f"Proceso completado: {processed_count}/{len(stations)} estaciones procesadas"
        )
        return processed_count > 0

    def _save_to_database(
        self,
        event_id: str,
        station_info: StationInfo,
        parsed_data: Dict,
        file_path: Path,
    ) -> bool:
        """Guarda los datos parseados en la base de datos"""
        try:
            # Parsear información del evento
            station_id = self.db.insert_or_update_seismic_station(
                code=station_info.code,
                name=station_info.name,
                latitude=station_info.latitude,
                longitude=station_info.longitude,
            )

            if not station_id:
                return False

            # Insertar registro de aceleración
            num_samples = parsed_data["acceleration"].get("NÚMERO DE MUESTRAS", "0")
            sampling_freq = self._extract_sampling_frequency(
                parsed_data["acceleration"].get("MUESTREO", "")
            )
            pga_values = self._extract_pga_values(
                parsed_data["acceleration"].get("PGA", "")
            )

            # start_time se obtiene desde la tabla seismic_events dentro del handler
            record_id = self.db.insert_seismic_acceleration_record(
                event_id=event_id,
                station_id=station_id,
                num_samples=int(num_samples),
                sampling_frequency=sampling_freq,
                pga_vertical=pga_values[0],
                pga_north=pga_values[1],
                pga_east=pga_values[2],
                baseline_correction=True,
                file_path=str(file_path),
            )

            if not record_id:
                return False

            # Insertar muestras de aceleración
            samples = parsed_data["samples"]
            self.db.insert_acceleration_samples(record_id, samples)

            logger.info(
                f"Datos guardados para estación {station_info.code}: {len(samples)} muestras"
            )
            return True

        except Exception as e:
            logger.error(f"Error guardando en base de datos: {e}")
            return False

    def _build_event_info(self, parsed_data: Dict) -> Dict:
        """Construye información del evento desde datos parseados"""
        event_section = parsed_data.get("event", {})

        # Parsear fecha y hora
        fecha_str = event_section.get("FECHA LOCAL", "")
        hora_str = event_section.get("HORA LOCAL", "")

        try:
            datetime_str = f"{fecha_str} {hora_str}"
            event_time = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error parseando event time: {e}")

        return event_time

    def _extract_sampling_frequency(self, muestreo_str: str) -> float:
        """Extrae frecuencia de muestreo de string como '200 muestras/segundo'"""
        match = re.search(r"(\d+)", muestreo_str)
        return float(match.group(1)) if match else 100.0

    def _extract_pga_values(self, pga_str: str) -> Tuple[float, float, float]:
        """Extrae valores PGA (Z, N, E) del string"""
        values = pga_str.split()
        try:
            return (float(values[0]), float(values[1]), float(values[2]))
        except (IndexError, ValueError):
            return (0.0, 0.0, 0.0)

    def cleanup(self):
        """Cierra conexiones y limpia recursos"""
        self.session.close()
