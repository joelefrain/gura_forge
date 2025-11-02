import sqlite3
import requests

from dateutil import parser
from datetime import datetime, timedelta, timezone

from typing import List, Dict, Optional, Tuple

from dataclasses import dataclass
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

from libs.config.config_logger import get_logger, log_execution_time

logger = get_logger()


@dataclass
class SeismicEvent:
    """Modelo de datos para eventos sísmicos"""

    event_id: str
    agency: str
    catalog: str
    event_time: datetime
    longitude: float
    latitude: float
    depth: Optional[float] = None
    magnitude: Optional[float] = None
    mag_type: Optional[str] = None


class DatabaseManager:
    """Gestiona conexiones y operaciones de base de datos"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager para conexiones thread-safe"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute(
            "PRAGMA journal_mode=WAL"
        )  # Write-Ahead Logging para mejor concurrencia
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance entre seguridad y velocidad
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Inicializa el esquema de la base de datos"""
        with self.get_connection() as conn:
            conn.executescript("""
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
                
                CREATE INDEX IF NOT EXISTS idx_event_time ON seismic_events(event_time);
                CREATE INDEX IF NOT EXISTS idx_catalog ON seismic_events(catalog);
                CREATE INDEX IF NOT EXISTS idx_magnitude ON seismic_events(magnitude);
                CREATE INDEX IF NOT EXISTS idx_location ON seismic_events(latitude, longitude);
                
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
            """)

    def bulk_upsert_events(self, events: List[SeismicEvent]) -> Tuple[int, int]:
        """Inserta o actualiza eventos en lote. Retorna (insertados, actualizados)"""
        if not events:
            return 0, 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verificar cuáles eventos ya existen (para contar)
            event_ids = [e.event_id for e in events]
            placeholders = ",".join("?" * len(event_ids))
            cursor.execute(
                f"SELECT event_id FROM seismic_events WHERE event_id IN ({placeholders})",
                event_ids,
            )
            existing_ids = {row[0] for row in cursor.fetchall()}

            # Usar INSERT OR REPLACE para manejar race conditions automáticamente
            cursor.executemany(
                """
                INSERT OR REPLACE INTO seismic_events 
                (event_id, agency, catalog, event_time, longitude, latitude, depth, magnitude, mag_type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                [
                    (
                        e.event_id,
                        e.agency,
                        e.catalog,
                        e.event_time,
                        e.longitude,
                        e.latitude,
                        e.depth,
                        e.magnitude,
                        e.mag_type,
                    )
                    for e in events
                ],
            )

            inserted = len(events) - len(existing_ids)
            updated = len(existing_ids)

            return inserted, updated

    def log_sync(
        self,
        catalog: str,
        year: int,
        status: str,
        processed: int = 0,
        inserted: int = 0,
        updated: int = 0,
        error: Optional[str] = None,
    ):
        """Registra el estado de sincronización"""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_catalog 
                (catalog, year, start_time, end_time, records_processed, 
                 records_inserted, records_updated, status, error_message)
                VALUES (?, ?, 
                    COALESCE((SELECT start_time FROM sync_catalog WHERE catalog=? AND year=?), CURRENT_TIMESTAMP),
                    CASE WHEN ? IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE NULL END,
                    ?, ?, ?, ?, ?)
            """,
                (
                    catalog,
                    year,
                    catalog,
                    year,
                    status,
                    processed,
                    inserted,
                    updated,
                    status,
                    error,
                ),
            )


class USGSExtractor:
    """Extractor para el catálogo USGS"""

    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    @staticmethod
    def fetch_events(
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_date: str,
        end_date: str,
        timeout: int = 120,
    ) -> List[SeismicEvent]:
        """Extrae eventos directamente desde la API de USGS"""
        params = {
            "format": "geojson",
            "minlatitude": min_lat,
            "maxlatitude": max_lat,
            "minlongitude": min_lon,
            "maxlongitude": max_lon,
            "starttime": start_date,
            "endtime": end_date,
            "eventtype": "earthquake",
        }

        try:
            response = requests.get(
                USGSExtractor.BASE_URL, params=params, timeout=timeout
            )
            response.raise_for_status()
            data = response.json()

            events = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [])

                if len(coords) < 3 or not props.get("time"):
                    continue

                timestamp_s = props["time"] / 1000
                event_time = datetime(1970, 1, 1) + timedelta(seconds=timestamp_s)

                event = SeismicEvent(
                    event_id=props.get(
                        "ids", props.get("id", f"usgs_{props.get('code')}")
                    ),
                    agency=props.get("net", "USGS"),
                    catalog="usgs",
                    event_time=event_time,
                    longitude=float(coords[0]),
                    latitude=float(coords[1]),
                    depth=float(coords[2]) if coords[2] else None,
                    magnitude=float(props["mag"]) if props.get("mag") else None,
                    mag_type=props.get("magType", ""),
                )
                events.append(event)

            return events

        except requests.RequestException as e:
            logger.error(f"Error en USGS para {start_date} a {end_date}: {e}")
            raise


class ISCExtractor:
    """Extractor para el catálogo ISC"""

    BASE_URL = "http://www.isc.ac.uk/cgi-bin/web-db-run"

    @staticmethod
    def fetch_events(
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_date: str,
        end_date: str,
        timeout: int = 180,
    ) -> List[SeismicEvent]:
        """Extrae eventos directamente desde la API de ISC"""
        start_year, start_month, start_day = start_date.split("-")
        end_year, end_month, end_day = end_date.split("-")

        params = {
            "request": "COMPREHENSIVE",
            "out_format": "CATCSV",
            "searchshape": "RECT",
            "bot_lat": min_lat,
            "top_lat": max_lat,
            "left_lon": min_lon,
            "right_lon": max_lon,
            "start_year": start_year,
            "start_month": start_month,
            "start_day": start_day,
            "start_time": "00:00:00",
            "end_year": end_year,
            "end_month": end_month,
            "end_day": end_day,
            "end_time": "23:59:59",
        }

        try:
            response = requests.get(
                ISCExtractor.BASE_URL, params=params, timeout=timeout
            )
            response.raise_for_status()

            events = []
            lines = response.text.split("\n")
            start_processing = False

            for line in lines:
                if "No events were found." in line:
                    return events

                if "EVENTID" in line:
                    start_processing = True
                    continue

                if "STOP" in line:
                    break

                if not start_processing or not line.strip():
                    continue

                columns = [col.strip() for col in line.split(",")]
                if len(columns) < 12:
                    continue

                try:
                    date_str, time_str = columns[3], columns[4]
                    # Intentar parsear con y sin fracciones de segundo
                    try:
                        event_time = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                        )
                    except ValueError:
                        event_time = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"
                        )

                    event = SeismicEvent(
                        event_id=columns[0],
                        agency=columns[2],
                        catalog="isc",
                        event_time=event_time,
                        longitude=float(columns[6]) if columns[6] else None,
                        latitude=float(columns[5]) if columns[5] else None,
                        depth=float(columns[7]) if columns[7] else None,
                        magnitude=float(columns[11]) if columns[11] else None,
                        mag_type=columns[10] if len(columns) > 10 else "",
                    )
                    events.append(event)

                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parseando línea ISC: {e}")
                    continue

            return events

        except requests.RequestException as e:
            logger.error(f"Error en ISC para {start_date} a {end_date}: {e}")
            raise


class IGPExtractor:
    """Extractor para el catálogo IGP"""

    BASE_URL = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb"

    @staticmethod
    def fetch_events(year: int, timeout: int = 60) -> List[SeismicEvent]:
        """Extrae eventos directamente desde la API de IGP"""
        try:
            response = requests.get(f"{IGPExtractor.BASE_URL}/{year}", timeout=timeout)

            response.raise_for_status()
            data = response.json()

            events = []
            for item in data:
                try:
                    date_seed = parser.parse(item["fecha_local"])
                    hour_seed = parser.parse(item["hora_local"])

                    # Definir la zona horaria local (UTC−5)
                    tz_local = timezone(timedelta(hours=-5))

                    # Combinar fecha y hora, manteniendo UTC
                    event_time = date_seed.replace(
                        hour=hour_seed.hour,
                        minute=hour_seed.minute,
                        second=hour_seed.second,
                        microsecond=hour_seed.microsecond,
                        tzinfo=tz_local,
                    )

                    event = SeismicEvent(
                        event_id=item["codigo"],
                        agency="IGP",
                        catalog="igp",
                        event_time=event_time,
                        longitude=float(item["longitud"]),
                        latitude=float(item["latitud"]),
                        depth=float(item["profundidad"])
                        if item.get("profundidad")
                        else None,
                        magnitude=float(item["magnitud"])
                        if item.get("magnitud")
                        else None,
                        mag_type=item.get("tipomagnitud", "M"),
                    )
                    events.append(event)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parseando evento IGP: {e}")
                    continue

            return events

        except requests.RequestException as e:
            logger.error(f"Error en IGP para año {year}: {e}")
            raise


class SeismicScraper:
    """Orquestador principal del scraping sísmico"""

    def __init__(self, db_path: str, max_workers: int = 5):
        self.db = DatabaseManager(db_path)
        self.max_workers = max_workers

    def scrape_catalog(
        self,
        catalog: str,
        year: int,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
    ) -> Dict[str, int]:
        """Scrape un catálogo para un año específico"""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        logger.info(f"Iniciando scraping: {catalog.upper()} - {year}")
        self.db.log_sync(catalog, year, "running")

        try:
            # Extraer eventos según el catálogo
            if catalog == "usgs":
                events = USGSExtractor.fetch_events(
                    min_lat, max_lat, min_lon, max_lon, start_date, end_date
                )
            elif catalog == "isc":
                events = ISCExtractor.fetch_events(
                    min_lat, max_lat, min_lon, max_lon, start_date, end_date
                )
            elif catalog == "igp":
                events = IGPExtractor.fetch_events(year)
            else:
                raise ValueError(f"Catálogo desconocido: {catalog}")

            # Guardar en base de datos
            inserted, updated = self.db.bulk_upsert_events(events)

            # Registrar éxito
            self.db.log_sync(
                catalog,
                year,
                "completed",
                processed=len(events),
                inserted=inserted,
                updated=updated,
            )

            logger.info(
                f"{catalog.upper()} {year}: {len(events)} eventos "
                f"({inserted} nuevos, {updated} actualizados)"
            )

            return {"processed": len(events), "inserted": inserted, "updated": updated}

        except Exception as e:
            error_msg = str(e)
            self.db.log_sync(catalog, year, "failed", error=error_msg)
            logger.exception(f"{catalog.upper()} {year}: {error_msg}")
            return {"processed": 0, "inserted": 0, "updated": 0, "error": error_msg}

    @log_execution_time
    def scrape_events(
        self,
        start_year: int,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        catalogs: List[str] = None,
    ) -> Dict[str, Dict]:
        """Scrape todos los catálogos con procesamiento concurrente"""
        if catalogs is None:
            catalogs = ["usgs", "isc", "igp"]

        current_year = datetime.now().year
        years = range(start_year, current_year + 1)

        # Crear tareas
        tasks = []
        for catalog in catalogs:
            for year in years:
                tasks.append((catalog, year))

        logger.info(
            f"Iniciando scraping: {len(tasks)} tareas con {self.max_workers} workers"
        )

        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.scrape_catalog,
                    catalog,
                    year,
                    min_lat,
                    max_lat,
                    min_lon,
                    max_lon,
                ): (catalog, year)
                for catalog, year in tasks
            }

            for future in as_completed(future_to_task):
                catalog, year = future_to_task[future]
                key = f"{catalog}_{year}"
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = {"error": str(e)}
                    logger.error(f"Error en tarea {key}: {e}")

        # Resumen
        total_processed = sum(r.get("processed", 0) for r in results.values())
        total_inserted = sum(r.get("inserted", 0) for r in results.values())
        total_updated = sum(r.get("updated", 0) for r in results.values())
        total_errors = sum(1 for r in results.values() if "error" in r)

        logger.info(f"{'=' * 40}")
        logger.info(f"Total procesado: {total_processed} eventos")
        logger.info(f"Nuevos: {total_inserted} | Actualizados: {total_updated}")
        logger.info(f"Errores: {total_errors}/{len(tasks)} tareas")
        logger.info(f"{'=' * 40}")

        return results
