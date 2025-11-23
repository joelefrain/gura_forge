from typing import List
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.downloader.igp_records import IGPDownloader
from libs.database.seismic_records import SeismicRecordsHandler

from libs.config.config_logger import get_logger

logger = get_logger()


class SeismicDownloader:
    """
    Orquestador del pipeline ETL para descarga de registros sísmicos
    Maneja múltiples catálogos de forma independiente
    """

    # Mapeo de catálogos a sus procesadores
    CATALOG_PROCESSORS = {
        "igp": IGPDownloader,
        # 'usgs': USGSDownloader,
        # 'emsc': EMSCDownloader,
    }

    def __init__(self):
        self.db = SeismicRecordsHandler()

    def _normalize_event_time(self, event_time):
        """Acepta datetime o string ISO/ISOz/otros y devuelve datetime."""
        if isinstance(event_time, datetime):
            return event_time
        if isinstance(event_time, str):
            s = event_time.strip()
            # manejar 'Z' final
            if s.endswith("Z"):
                s = s[:-1]
            for fmt_try in (None, "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    if fmt_try is None:
                        return datetime.fromisoformat(s)
                    return datetime.strptime(s, fmt_try)
                except Exception:
                    continue
        # fallback
        logger.warning(f"No se pudo parsear event_time '{event_time}', usando now()")
        return datetime.now()

    def process_catalog(
        self, catalog: str, events: List[dict], max_workers: int = 1
    ) -> dict:
        """
        Procesa un catálogo completo de eventos de forma independiente.

        Args:
            catalog: nombre del catálogo ('igp', 'usgs', etc.)
            events: lista de eventos con estructura {'event_id', 'event_time', ...}
            max_workers: número máximo de workers paralelos (recomendado 1 para
                        descargas de sitios web)

        Returns:
            diccionario con estadísticas del procesamiento
        """
        logger.info(f"Iniciando procesamiento del catálogo: {catalog}")

        # Validar que el catálogo existe
        if catalog not in self.CATALOG_PROCESSORS:
            logger.error(f"Catálogo no soportado: {catalog}")
            return {
                "success": False,
                "catalog": catalog,
                "error": f"Catálogo no soportado: {catalog}",
            }

        # Inicializar sesión de sincronización
        sync_id = self.db.start_sync_session(
            catalog=catalog, year=datetime.now().year, start_time=datetime.utcnow()
        )

        if not sync_id:
            logger.error("No se pudo iniciar sesión de sincronización")
            return {
                "success": False,
                "catalog": catalog,
                "error": "No se pudo iniciar sesión de sincronización",
            }

        # Inicializar procesador
        processor_class = self.CATALOG_PROCESSORS[catalog]
        processor = processor_class()

        # Estadísticas
        stats = {
            "total_events": len(events),
            "processed_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "total_stations": 0,
            "errors": [],
        }

        try:
            # Procesar eventos
            stats = self._process_parallel(processor, events, stats, max_workers)

            # Actualizar sesión de sincronización
            status = (
                "completed" if stats["failed_events"] == 0 else "completed_with_errors"
            )
            self.db.update_sync_session(
                sync_id=sync_id,
                records_processed=stats["processed_events"],
                records_inserted=stats["successful_events"],
                records_updated=0,
                status=status,
                error_message="; ".join(stats["errors"][:10])
                if stats["errors"]
                else None,
            )

            stats["sync_id"] = sync_id
            stats["status"] = status

        except Exception as e:
            logger.error(f"Error crítico en procesamiento: {e}", exc_info=True)
            self.db.update_sync_session(
                sync_id=sync_id,
                records_processed=stats["processed_events"],
                records_inserted=stats["successful_events"],
                records_updated=0,
                status="failed",
                error_message=str(e),
            )
            stats["status"] = "failed"
            stats["errors"].append(str(e))

        finally:
            processor.cleanup()
            logger.info(
                f"Procesamiento completado: {stats['successful_events']}/{stats['total_events']} "
                f"eventos procesados exitosamente"
            )

        return stats

    def _process_parallel(
        self, processor, events: List[dict], stats: dict, max_workers: int
    ) -> dict:
        """Procesa eventos en paralelo (uso cuidadoso con scrapers web)"""
        logger.warning(
            f"Procesamiento paralelo con {max_workers} workers. "
            "Asegúrese de respetar los términos de servicio del sitio web."
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for event in events:
                event_id = event.get("event_id")
                event_time = self._normalize_event_time(event.get("event_time"))

                if not event_id or not event_time:
                    logger.warning(f"Evento inválido: {event}")
                    stats["failed_events"] += 1
                    continue

                future = executor.submit(
                    processor.process_event,
                    event_id=event_id,
                    event_time=event_time,
                    catalog=event.get("catalog", "igp"),
                )
                futures[future] = event_id

            # Recolectar resultados
            for future in as_completed(futures):
                event_id = futures[future]
                try:
                    success = future.result(timeout=600)  # 10 minutos timeout
                    if success:
                        stats["successful_events"] += 1
                    else:
                        stats["failed_events"] += 1
                        stats["errors"].append(f"Fallo procesando {event_id}")
                except Exception as e:
                    logger.error(f"Error en worker para {event_id}: {e}", exc_info=True)
                    stats["failed_events"] += 1
                    stats["errors"].append(f"{event_id}: {str(e)}")
                finally:
                    stats["processed_events"] += 1

        return stats

    def get_events_to_process(self, catalog: str, limit: int = 10) -> List[dict]:
        """
        Obtiene eventos del catálogo que no tienen registros descargados
        """
        return self.db.get_events_without_records(catalog, limit)

    def process_recent_events(
        self, catalog: str, num_events: int = 10, max_workers: int = 1
    ) -> dict:
        """
        Descarga eventos recientes de un catálogo específico
        """
        events = self.get_events_to_process(catalog, limit=num_events)
        logger.info(f"Eventos a procesar en {catalog}: {len(events)}")

        if not events:
            return {
                "success": True,
                "catalog": catalog,
                "message": "No hay eventos nuevos",
                "total_events": 0,
            }

        return self.process_catalog(catalog, events, max_workers)

    def close(self):
        """Cierra recursos"""
        self.db.close()
