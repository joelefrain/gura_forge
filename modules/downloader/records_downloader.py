import pandas as pd

from datetime import datetime
from typing import List, Dict, Optional

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.downloader.igp_records import IGPDownloader
from libs.database.seismic_records import SeismicRecordsHandler

from libs.helpers.metadata_helpers import style_metadata_property
from libs.config.config_logger import get_logger, log_execution_time

logger = get_logger()


@dataclass
class EventResult:
    """Resultado del procesamiento de un evento"""

    event_id: str
    success: bool
    stations_processed: int = 0
    samples_total: int = 0
    processing_time: float = 0.0
    error: Optional[str] = None


class SeismicDownloader:
    """
    Orquestador del pipeline ETL para descarga de registros sísmicos
    Maneja múltiples catálogos con procesamiento paralelo y métricas detalladas
    """

    # Mapeo de catálogos a sus procesadores
    CATALOG_PROCESSORS = {
        "igp": IGPDownloader,
        # 'usgs': USGSDownloader,
        # 'emsc': EMSCDownloader,
    }

    def __init__(self):
        self.db = SeismicRecordsHandler()
        self._reset_metrics()
        self.catalog_results = {}

    def _reset_metrics(self):
        """Reinicia métricas de procesamiento"""
        self.total_events = 0
        self.processed_events = 0
        self.successful_events = 0
        self.failed_events = 0
        self.total_stations = 0
        self.total_samples = 0
        self.total_processing_time = 0.0
        self.failed_event_list = []
        self.sync_id = None
        self.catalog_name = None
        self.start_time = None
        self.end_time = None

    def _normalize_event_time(self, event_time) -> datetime:
        """Normaliza event_time a datetime"""
        if isinstance(event_time, datetime):
            return event_time

        if isinstance(event_time, str):
            s = event_time.strip().rstrip("Z")

            for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    return (
                        datetime.fromisoformat(s)
                        if fmt is None
                        else datetime.strptime(s, fmt)
                    )
                except Exception:
                    continue

        logger.warning(f"No se pudo parsear event_time '{event_time}', usando now()")
        return datetime.now()

    @log_execution_time
    def process_catalog(
        self,
        catalog: str,
        events: List[Dict],
        max_workers: int = 1,
        parallel_stations: int = 5,
    ) -> Dict:
        """
        Procesa un catálogo completo de eventos.

        Args:
            catalog: Nombre del catálogo ('igp', 'usgs', etc.)
            events: Lista de eventos con estructura {'event_id', 'event_time', ...}
            max_workers: Número de eventos procesados en paralelo (recomendado: 1-3)
            parallel_stations: Workers para procesar estaciones dentro de cada evento

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        self._reset_metrics()
        self.catalog_name = catalog
        self.start_time = datetime.now()
        self.total_events = len(events)

        logger.info(
            f"Iniciando procesamiento: {catalog.upper()} - {len(events)} eventos"
        )

        # Validar catálogo
        if catalog not in self.CATALOG_PROCESSORS:
            error_msg = f"Catálogo no soportado: {catalog}"
            logger.error(error_msg)
            return self._build_error_response(error_msg)

        # Iniciar sesión de sincronización
        self.sync_id = self.db.start_sync_session(
            catalog=catalog, year=datetime.now().year, start_time=datetime.utcnow()
        )

        if not self.sync_id:
            error_msg = "No se pudo iniciar sesión de sincronización"
            logger.error(error_msg)
            return self._build_error_response(error_msg)

        try:
            # Procesar eventos
            results = self._process_events_parallel(
                catalog, events, max_workers, parallel_stations
            )

            # Calcular métricas
            self._calculate_metrics(results)

            # Actualizar sesión de sincronización
            status = "completed" if self.failed_events == 0 else "completed_with_errors"
            self.db.update_sync_session(
                sync_id=self.sync_id,
                records_processed=self.processed_events,
                records_inserted=self.successful_events,
                records_updated=0,
                status=status,
                error_message="; ".join(self.failed_event_list[:10])
                if self.failed_event_list
                else None,
            )

            self.end_time = datetime.now()

            logger.info(
                f"Procesamiento completado: {self.successful_events}/{self.total_events} eventos, "
                f"{self.total_stations} estaciones, {self.total_samples} muestras"
            )

            return self._build_success_response(status)

        except Exception as e:
            logger.exception(f"Error crítico en procesamiento: {e}")
            self._handle_critical_error(str(e))
            return self._build_error_response(str(e))

    def _process_events_parallel(
        self, catalog: str, events: List[Dict], max_workers: int, parallel_stations: int
    ) -> List[EventResult]:
        """Procesa eventos en paralelo"""
        if max_workers > 1:
            logger.warning(
                f"Procesamiento paralelo con {max_workers} workers. "
                "Verifique límites de rate-limiting del servidor."
            )

        results = []
        processor_class = self.CATALOG_PROCESSORS[catalog]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for event in events:
                event_id = event.get("event_id")
                event_time = self._normalize_event_time(event.get("event_time"))

                if not event_id or not event_time:
                    logger.warning(f"Evento inválido: {event}")
                    results.append(
                        EventResult(
                            event_id=str(event.get("event_id", "unknown")),
                            success=False,
                            error="Datos de evento incompletos",
                        )
                    )
                    continue

                future = executor.submit(
                    self._process_single_event,
                    processor_class,
                    event_id,
                    event_time,
                    catalog,
                    parallel_stations,
                )
                futures[future] = event_id

            # Recolectar resultados
            for future in as_completed(futures):
                event_id = futures[future]
                try:
                    result = future.result(timeout=600)  # 10 min timeout
                    results.append(result)

                    if result.success:
                        logger.info(
                            f"{event_id}: {result.stations_processed} estaciones, "
                            f"{result.samples_total} muestras en {result.processing_time:.2f}s"
                        )
                    else:
                        logger.warning(f"{event_id}: {result.error}")

                except Exception as e:
                    logger.error(f"Excepción procesando {event_id}: {e}")
                    results.append(
                        EventResult(event_id=event_id, success=False, error=str(e))
                    )

        return results

    def _process_single_event(
        self,
        processor_class,
        event_id: str,
        event_time: datetime,
        catalog: str,
        parallel_stations: int,
    ) -> EventResult:
        """Procesa un evento individual con métricas"""
        import time

        start_time = time.time()
        processor = processor_class(max_workers=parallel_stations)

        try:
            success = processor.process_event(event_id, event_time, catalog)
            processing_time = time.time() - start_time

            if success:
                return EventResult(
                    event_id=event_id,
                    success=True,
                    stations_processed=processor.successful_stations,
                    samples_total=processor.total_samples,
                    processing_time=processing_time,
                )
            else:
                return EventResult(
                    event_id=event_id,
                    success=False,
                    processing_time=processing_time,
                    error="Procesamiento fallido",
                )

        except Exception as e:
            processing_time = time.time() - start_time
            return EventResult(
                event_id=event_id,
                success=False,
                processing_time=processing_time,
                error=str(e),
            )

    def _calculate_metrics(self, results: List[EventResult]):
        """Calcula métricas agregadas"""
        self.processed_events = len(results)
        self.successful_events = sum(1 for r in results if r.success)
        self.failed_events = self.processed_events - self.successful_events
        self.total_stations = sum(r.stations_processed for r in results)
        self.total_samples = sum(r.samples_total for r in results)
        self.total_processing_time = sum(r.processing_time for r in results)
        self.failed_event_list = [
            f"{r.event_id}: {r.error}" for r in results if not r.success
        ]

    def _build_success_response(self, status: str) -> Dict:
        """Construye respuesta exitosa"""
        return {
            "success": True,
            "catalog": self.catalog_name,
            "sync_id": self.sync_id,
            "status": status,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
            "successful_events": self.successful_events,
            "failed_events": self.failed_events,
            "total_stations": self.total_stations,
            "total_samples": self.total_samples,
            "processing_time": self.total_processing_time,
            "errors": self.failed_event_list[:10],  # Primeros 10 errores
        }

    def _build_error_response(self, error_msg: str) -> Dict:
        """Construye respuesta de error"""
        return {
            "success": False,
            "catalog": self.catalog_name,
            "sync_id": self.sync_id,
            "error": error_msg,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
        }

    def _handle_critical_error(self, error_msg: str):
        """Maneja error crítico actualizando BD"""
        if self.sync_id:
            self.db.update_sync_session(
                sync_id=self.sync_id,
                records_processed=self.processed_events,
                records_inserted=self.successful_events,
                records_updated=0,
                status="failed",
                error_message=error_msg,
            )

    def get_events_to_process(
        self,
        catalog: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Obtiene eventos del catálogo que no tienen registros descargados
        """
        return self.db.get_events_without_records(
            catalog,
            limit,
        )

    @log_execution_time
    def process_events(
        self,
        catalog: str,
        num_events: int = 10,
        max_workers: int = 1,
        parallel_stations: int = 5,
    ) -> Dict:
        """
        Descarga eventos recientes de un catálogo específico

        Args:
            catalog: Nombre del catálogo
            num_events: Número de eventos a procesar
            max_workers: Workers para procesar eventos en paralelo
            parallel_stations: Workers para procesar estaciones dentro de cada evento
        """
        events = self.get_events_to_process(catalog, num_events)
        logger.info(f"Eventos a procesar en {catalog.upper()}: {len(events)}")

        if not events:
            self._reset_metrics()
            self.catalog_name = catalog
            logger.info(f"No hay eventos nuevos en {catalog.upper()}")
            return {
                "success": True,
                "catalog": catalog,
                "message": "No hay eventos nuevos",
                "total_events": 0,
            }

        return self.process_catalog(catalog, events, max_workers, parallel_stations)

    @log_execution_time
    def process_multiple_catalogs(
        self,
        catalogs: Dict[str, int],
        max_workers: int = 1,
        parallel_stations: int = 5,
    ) -> Dict:
        """
        Procesa múltiples catálogos secuencialmente y almacena resultados

        Args:
            catalogs: Diccionario con {nombre_catalogo: num_eventos}
            max_workers: Workers para procesar eventos en paralelo
            parallel_stations: Workers para procesar estaciones

        Returns:
            Diccionario con resultados consolidados de todos los catálogos
        """
        self.catalog_results = {}
        logger.info(f"Iniciando procesamiento de {len(catalogs)} catálogos")

        for catalog, num_events in catalogs.items():
            logger.info(
                f"Procesando catálogo: {catalog.upper()} ({num_events} eventos)"
            )

            result = self.process_events(
                catalog=catalog,
                num_events=num_events,
                max_workers=max_workers,
                parallel_stations=parallel_stations,
            )

            # Almacenar métricas actuales para este catálogo
            self.catalog_results[catalog] = {
                "result": result,
                "total_events": self.total_events,
                "processed_events": self.processed_events,
                "successful_events": self.successful_events,
                "failed_events": self.failed_events,
                "total_stations": self.total_stations,
                "total_samples": self.total_samples,
                "processing_time": self.total_processing_time,
            }

        logger.info("Procesamiento de todos los catálogos completado")

        return {
            "success": True,
            "catalogs_processed": len(catalogs),
            "results": self.catalog_results,
        }

    @style_metadata_property
    def metadata(self):
        """Devuelve resumen tabulado del procesamiento de los downloaders"""
        if not self.catalog_results:
            return pd.DataFrame(
                {"Mensaje": ["No hay datos de procesamiento disponibles"]}
            )

        df = pd.DataFrame.from_dict(self.catalog_results, orient="index")
        df.reset_index(inplace=True)
        df.rename(columns={"index": "Catalogo"}, inplace=True)

        return df

    def close(self):
        """Cierra recursos"""
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
