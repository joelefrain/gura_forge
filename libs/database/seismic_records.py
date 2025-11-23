import sqlite3

from datetime import datetime
from typing import List, Optional, Tuple

from libs.config.config_variables import DATABASE_PATH, BATCH_SIZE_SQL_VAR

from libs.config.config_logger import get_logger

from libs.database.base import DatabaseManager

logger = get_logger()


class SeismicRecordsHandler:
    """
    Manager de base de datos con soporte para operaciones ETL de registros sísmicos.
    Usa DatabaseManager para conexiones/transactions.
    """

    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path

    # ==================== ESTACIONES SÍSMICAS ====================

    def insert_or_update_seismic_station(
        self, code: str, name: str, latitude: float, longitude: float
    ) -> Optional[int]:
        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute("SELECT id FROM seismic_station WHERE code = ?", (code,))
                result = cursor.fetchone()

                now = datetime.utcnow()
                if result:
                    station_id = result["id"]
                    cursor.execute(
                        """
                        UPDATE seismic_station 
                        SET name = ?, latitude = ?, longitude = ?, updated_at = ?
                        WHERE id = ?
                    """,
                        (name, latitude, longitude, now, station_id),
                    )
                    logger.info(f"Estación actualizada: {code}")
                else:
                    cursor.execute(
                        """
                        INSERT INTO seismic_station 
                        (code, name, latitude, longitude, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (code, name, latitude, longitude, now, now),
                    )
                    station_id = cursor.lastrowid
                    logger.info(f"Estación insertada: {code} (ID: {station_id})")

                return station_id

        except sqlite3.Error as e:
            logger.error(f"Error en insert_or_update_seismic_station: {e}")
            return None

    def get_seismic_station(self, code: str) -> Optional[dict]:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, code, name, latitude, longitude FROM seismic_station WHERE code = ?",
                    (code,),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estación: {e}")
            return None

    # ==================== EVENTOS SÍSMICOS ====================

    def insert_or_update_seismic_event(
        self,
        event_id: str,
        agency: str,
        catalog: str,
        event_time: datetime,
        longitude: float,
        latitude: float,
        depth: Optional[float] = None,
        magnitude: Optional[float] = None,
        mag_type: Optional[str] = None,
    ) -> bool:
        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute(
                    "SELECT event_id FROM seismic_events WHERE event_id = ?",
                    (event_id,),
                )
                exists = cursor.fetchone() is not None

                now = datetime.utcnow()
                if exists:
                    cursor.execute(
                        """
                        UPDATE seismic_events 
                        SET agency = ?, catalog = ?, event_time = ?, longitude = ?, latitude = ?,
                            depth = ?, magnitude = ?, mag_type = ?, updated_at = ?
                        WHERE event_id = ?
                    """,
                        (
                            agency,
                            catalog,
                            event_time,
                            longitude,
                            latitude,
                            depth,
                            magnitude,
                            mag_type,
                            now,
                            event_id,
                        ),
                    )
                    logger.info(f"Evento actualizado: {event_id}")
                else:
                    cursor.execute(
                        """
                        INSERT INTO seismic_events
                        (event_id, agency, catalog, event_time, longitude, latitude, 
                         depth, magnitude, mag_type, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event_id,
                            agency,
                            catalog,
                            event_time,
                            longitude,
                            latitude,
                            depth,
                            magnitude,
                            mag_type,
                            now,
                            now,
                        ),
                    )
                    logger.info(f"Evento insertado: {event_id}")

                return True

        except sqlite3.Error as e:
            logger.error(f"Error en insert_or_update_seismic_event: {e}")
            return False

    def get_seismic_event(self, event_id: str) -> Optional[dict]:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM seismic_events WHERE event_id = ?", (event_id,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo evento: {e}")
            return None

    # ==================== REGISTROS DE ACELERACIÓN ====================

    def insert_seismic_acceleration_record(
        self,
        event_id: str,
        station_id: int,
        num_samples: int,
        sampling_frequency: float,
        pga_vertical: float,
        pga_north: float,
        pga_east: float,
        baseline_correction: bool = True,
        file_path: Optional[str] = None,
    ) -> Optional[int]:
        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute(
                    "SELECT event_time FROM seismic_events WHERE event_id = ?",
                    (event_id,),
                )
                evt = cursor.fetchone()
                start_time_val = evt["event_time"] if evt and evt["event_time"] else datetime.utcnow()

                cursor.execute(
                    "SELECT id FROM seismic_acceleration_record WHERE event_id = ? AND station_id = ?",
                    (event_id, station_id),
                )
                result = cursor.fetchone()

                now = datetime.utcnow()
                if result:
                    record_id = result["id"]
                    cursor.execute(
                        """
                        UPDATE seismic_acceleration_record
                        SET start_time = ?, num_samples = ?, sampling_frequency = ?,
                            pga_vertical = ?, pga_north = ?, pga_east = ?,
                            baseline_correction = ?, file_path = ?, 
                            downloaded_at = ?, updated_at = ?
                        WHERE id = ?
                    """,
                        (
                            start_time_val,
                            num_samples,
                            sampling_frequency,
                            pga_vertical,
                            pga_north,
                            pga_east,
                            baseline_correction,
                            file_path,
                            now,
                            now,
                            record_id,
                        ),
                    )
                    logger.info(f"Registro de aceleración actualizado: {record_id}")
                else:
                    cursor.execute(
                        """
                        INSERT INTO seismic_acceleration_record
                        (event_id, station_id, start_time, num_samples, sampling_frequency,
                         pga_vertical, pga_north, pga_east, baseline_correction, 
                         file_path, downloaded_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event_id,
                            station_id,
                            start_time_val,
                            num_samples,
                            sampling_frequency,
                            pga_vertical,
                            pga_north,
                            pga_east,
                            baseline_correction,
                            file_path,
                            now,
                            now,
                            now,
                        ),
                    )
                    record_id = cursor.lastrowid
                    logger.info(f"Registro de aceleración insertado: {record_id}")

                return record_id

        except sqlite3.Error as e:
            logger.error(f"Error en insert_seismic_acceleration_record: {e}")
            return None

    # ==================== MUESTRAS DE ACELERACIÓN ====================

    def insert_acceleration_samples(
        self,
        record_id: int,
        samples: List[Tuple[float, float, float]],
        batch_size: int = BATCH_SIZE_SQL_VAR,
    ) -> bool:
        if not samples:
            logger.warning("No hay muestras para insertar")
            return False

        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute(
                    "DELETE FROM acceleration_sample WHERE record_id = ?", (record_id,)
                )

                for i in range(0, len(samples), batch_size):
                    batch = samples[i : i + batch_size]
                    data = [
                        (record_id, idx + i, z, n, e)
                        for idx, (z, n, e) in enumerate(batch)
                    ]

                    cursor.executemany(
                        """
                        INSERT INTO acceleration_sample
                        (record_id, sample_index, accel_vertical, accel_north, accel_east)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        data,
                    )

                logger.info(f"Insertadas {len(samples)} muestras para registro {record_id}")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error en insert_acceleration_samples: {e}")
            return False

    def get_acceleration_record(self, event_id: str, station_id: int) -> Optional[dict]:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT * FROM seismic_acceleration_record 
                    WHERE event_id = ? AND station_id = ?
                """,
                    (event_id, station_id),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo registro: {e}")
            return None

    def get_acceleration_samples(self, record_id: int) -> List[dict]:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT sample_index, accel_vertical, accel_north, accel_east
                    FROM acceleration_sample
                    WHERE record_id = ?
                    ORDER BY sample_index
                """,
                    (record_id,),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo muestras: {e}")
            return []

    # ==================== CONTROL DE SINCRONIZACIÓN ====================

    def start_sync_session(
        self, catalog: str, year: int, start_time: datetime
    ) -> Optional[int]:
        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute(
                    "SELECT id FROM sync_catalog WHERE catalog = ? AND year = ?",
                    (catalog, year),
                )
                row = cursor.fetchone()
                now = datetime.utcnow()
                if row:
                    catalog_id = row["id"]
                else:
                    cursor.execute(
                        """
                        INSERT INTO sync_catalog
                        (catalog, year, start_time, status, created_at, updated_at)
                        VALUES (?, ?, ?, 'running', ?, ?)
                        """,
                        (catalog, year, start_time, now, now),
                    )
                    catalog_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO sync_record
                    (sync_catalog_id, start_time, status, created_at, updated_at)
                    VALUES (?, ?, 'running', ?, ?)
                    """,
                    (catalog_id, start_time, now, now),
                )
                record_id = cursor.lastrowid
                logger.info(f"Inicio de sesión de sincronización (record_id={record_id}, catalog_id={catalog_id})")
                return record_id
        except sqlite3.Error as e:
            logger.error(f"Error iniciando sesión de sincronización: {e}")
            return None

    def update_sync_session(
        self,
        sync_id: int,
        records_processed: int,
        records_inserted: int,
        records_updated: int,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> bool:
        try:
            with DatabaseManager.transaction(self.db_path) as cursor:
                cursor.execute(
                    """
                    UPDATE sync_record
                    SET records_processed = ?, records_inserted = ?,
                        records_updated = ?, status = ?, end_time = ?,
                        error_message = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        records_processed,
                        records_inserted,
                        records_updated,
                        status,
                        datetime.utcnow(),
                        error_message,
                        datetime.utcnow(),
                        sync_id,
                    ),
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error actualizando sesión: {e}")
            return False

    # ==================== QUERIES ÚTILES ====================

    def get_events_without_records(self, catalog: str, limit: int = 10) -> List[dict]:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT DISTINCT se.* FROM seismic_events se
                    WHERE se.catalog = ? AND se.event_id NOT IN (
                        SELECT DISTINCT event_id FROM seismic_acceleration_record
                    )
                    LIMIT ?
                """,
                    (catalog, limit),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error en get_events_without_records: {e}")
            return []

    def count_records_by_event(self, event_id: str) -> int:
        try:
            with DatabaseManager.get_connection(self.db_path) as conn:
                result = conn.execute(
                    "SELECT COUNT(*) as cnt FROM seismic_acceleration_record WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                return result["cnt"] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error contando registros: {e}")
            return 0

    def close(self):
        """No-op: DatabaseManager usa conexiones por uso"""
        logger.debug("SeismicRecordsHandler.close() no necesita cerrar conexiones persistentes")
