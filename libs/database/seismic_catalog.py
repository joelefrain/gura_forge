import sqlite3

from contextlib import contextmanager

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
