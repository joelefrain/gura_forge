import sqlite3

from contextlib import contextmanager

from datetime import datetime
from typing import List, Tuple, Optional

from libs.config.config_variables import DATABASE_PATH, BATCH_SIZE_SQL_VAR

from libs.config.config_logger import get_logger

logger = get_logger()


class SeismicCatalogHandler:
    """Gestiona operaciones del catálogo sísmico con connection pooling implícito"""

    def __init__(self):
        self._init_schema()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._get_connection() as conn:
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
            """)

    def bulk_upsert_events(self, events: List) -> Tuple[int, int]:
        if not events:
            return 0, 0

        inserted = updated = 0

        with self._get_connection() as conn:
            for i in range(0, len(events), BATCH_SIZE_SQL_VAR):
                batch = events[i : i + BATCH_SIZE_SQL_VAR]

                # Verificar existentes
                event_ids = [e.event_id for e in batch]
                placeholders = ",".join("?" * len(event_ids))
                existing = {
                    row[0]
                    for row in conn.execute(
                        f"SELECT event_id FROM seismic_events WHERE event_id IN ({placeholders})",
                        event_ids,
                    ).fetchall()
                }

                # Upsert
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO seismic_events 
                    (event_id, agency, catalog, event_time, longitude, latitude, depth, magnitude, mag_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        for e in batch
                    ],
                )

                inserted += len(batch) - len(existing)
                updated += len(existing)

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
        with self._get_connection() as conn:
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


def get_event_times(
    self,
    catalogs: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> List[datetime]:
    """
    Obtiene los event_time de eventos filtrados por catálogo y rango temporal.
    Retorna directamente lista de datetime.

    Params:
        catalogs : lista de catálogos a filtrar (requerido)
        start_time: fecha inicial (inclusive)
        end_time: fecha final (inclusive)
        limit: máximo número de registros

    Returns:
        Lista de objetos datetime ordenados por event_time
    """
    if not catalogs:
        logger.warning("get_event_times: catalogs vacío, retornando lista vacía")
        return []

    # Construir query con placeholders para catalogs
    placeholders = ",".join("?" * len(catalogs))
    sql = f"SELECT event_time FROM seismic_events WHERE catalog IN ({placeholders})"
    params = catalogs[:]  # Copia de la lista de catálogos

    # Filtros temporales - convertir datetime a string para SQLite
    if start_time:
        sql += " AND event_time >= ?"
        params.append(start_time.isoformat())

    if end_time:
        sql += " AND event_time <= ?"
        params.append(end_time.isoformat())

    sql += " ORDER BY event_time"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    logger.debug(
        f"Query: {sql} | Params: catalogs={catalogs}, start={start_time}, end={end_time}, limit={limit}"
    )

    # Ejecutar y convertir
    with self._get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        event_times = []
        for row in rows:
            try:
                # Manejar diferentes formatos de fecha que podría devolver SQLite
                if isinstance(row[0], str):
                    event_times.append(datetime.fromisoformat(row[0]))
                elif isinstance(row[0], (int, float)):
                    # Si está almacenado como timestamp
                    event_times.append(datetime.fromtimestamp(row[0]))
                else:
                    # Si ya es datetime object
                    event_times.append(row[0])
            except (ValueError, TypeError) as e:
                logger.warning(f"Error convirtiendo fecha {row[0]}: {e}")
                continue

    logger.info(f"Obtenidos {len(event_times)} eventos de catálogos {catalogs}")
    return event_times
