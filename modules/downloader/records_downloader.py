import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
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


@dataclass
class CatalogMetrics:
    """Métricas de procesamiento de un catálogo"""

    catalog: str
    total_events: int = 0
    successful_events: int = 0
    failed_events: int = 0
    total_stations: int = 0
    total_samples: int = 0
    total_processing_time: float = 0.0
    sync_id: Optional[int] = None
    status: str = "pending"
    error_summary: str = ""


class SeismicDownloader:
    """
    Orquestador del pipeline ETL para descarga de registros sísmicos
    Maneja múltiples catálogos con procesamiento paralelo
    """

    CATALOG_PROCESSORS = {"igp": IGPDownloader}

    def __init__(self):
        self.db = SeismicRecordsHandler()
        self._metrics: Dict[str, CatalogMetrics] = {}
        self._metadata_cache: Optional[pd.DataFrame] = None

    def _normalize_event_time(self, event_time) -> datetime:
        """Normaliza event_time a datetime"""
        if isinstance(event_time, datetime):
            return event_time

        if isinstance(event_time, str):
            try:
                return datetime.fromisoformat(event_time.strip())
            except ValueError:
                raise ValueError(f"No se pudo parsear event_time: '{event_time}'")

        raise TypeError(
            f"event_time debe ser datetime o str, recibido: {type(event_time)}"
        )

    @log_execution_time
    def process_catalog(
        self,
        catalog: str,
        num_events: int = 10,
        max_workers: int = 1,
        parallel_stations: int = 5,
    ) -> Dict[str, Any]:
        """
        Procesa eventos de un catálogo específico.

        Args:
            catalog: Nombre del catálogo ('igp')
            num_events: Número máximo de eventos a procesar
            max_workers: Workers para procesar eventos en paralelo
            parallel_stations: Workers para procesar estaciones dentro de cada evento

        Returns:
            Diccionario con resultados del procesamiento
        """
        logger.info(f"Procesando catálogo: {catalog.upper()} ({num_events} eventos)")

        if catalog not in self.CATALOG_PROCESSORS:
            return self._build_error_response(f"Catálogo no soportado: {catalog}")

        # Obtener eventos sin registros
        events = self.db.get_events_without_records(catalog, num_events)

        if not events:
            logger.info(f"No hay eventos nuevos en {catalog.upper()}")
            return self._build_no_events_response(catalog)

        # Iniciar sesión de sincronización
        sync_id = self.db.start_sync_session(
            catalog=catalog, year=datetime.now().year, start_time=datetime.utcnow()
        )

        if not sync_id:
            return self._build_error_response(
                "No se pudo iniciar sesión de sincronización"
            )

        # Procesar eventos
        results = self._process_events_parallel(
            catalog, events, max_workers, parallel_stations
        )

        # Calcular métricas
        metrics = self._calculate_metrics(catalog, results, sync_id)

        # Actualizar BD
        self._update_sync_session(metrics)

        # Almacenar métricas
        self._metrics[catalog] = metrics
        self._metadata_cache = None  # Invalidar cache

        logger.info(self._get_summary_message(metrics))

        return self._build_success_response(metrics)

    def _process_events_parallel(
        self, catalog: str, events: List[Dict], max_workers: int, parallel_stations: int
    ) -> List[EventResult]:
        """Procesa eventos en paralelo"""
        results = []
        processor_class = self.CATALOG_PROCESSORS[catalog]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for event in events:
                event_id = event.get("event_id")
                event_time = self._normalize_event_time(event.get("event_time"))

                if not event_id or not event_time:
                    results.append(self._build_invalid_event_result(event))
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
                    result = future.result(timeout=600)
                    results.append(result)
                    self._log_event_result(event_id, result)
                except Exception as e:
                    logger.error(f"Error procesando {event_id}: {e}")
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
        """Procesa un evento individual"""
        import time

        start_time = time.time()

        try:
            processor = processor_class(max_workers=parallel_stations)
            success = processor.process_event(event_id, event_time, catalog)
            processing_time = time.time() - start_time

            if success:
                return EventResult(
                    event_id=event_id,
                    success=True,
                    stations_processed=processor.metrics.stations_saved_db,
                    samples_total=processor.metrics.total_samples,
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
            return EventResult(
                event_id=event_id,
                success=False,
                processing_time=time.time() - start_time,
                error=str(e),
            )

    def _calculate_metrics(
        self, catalog: str, results: List[EventResult], sync_id: int
    ) -> CatalogMetrics:
        """Calcula métricas del procesamiento"""
        processed_events = len(results)
        successful_events = sum(1 for r in results if r.success)
        failed_events = processed_events - successful_events

        # Obtener errores para resumen
        errors = [f"{r.event_id}: {r.error}" for r in results if not r.success]
        error_summary = "; ".join(errors[:5]) + ("..." if len(errors) > 5 else "")

        return CatalogMetrics(
            catalog=catalog,
            total_events=processed_events,
            successful_events=successful_events,
            failed_events=failed_events,
            total_stations=sum(r.stations_processed for r in results),
            total_samples=sum(r.samples_total for r in results),
            total_processing_time=sum(r.processing_time for r in results),
            sync_id=sync_id,
            status="completed" if failed_events == 0 else "completed_with_errors",
            error_summary=error_summary,
        )

    def _update_sync_session(self, metrics: CatalogMetrics):
        """Actualiza sesión de sincronización en BD"""
        self.db.update_sync_session(
            sync_id=metrics.sync_id,
            records_processed=metrics.total_events,
            records_inserted=metrics.successful_events,
            records_updated=0,
            status=metrics.status,
            error_message=metrics.error_summary if metrics.failed_events > 0 else None,
        )

    @log_execution_time
    def process_multiple_catalogs(
        self,
        catalogs: Dict[str, int],
        max_workers: int = 1,
        parallel_stations: int = 5,
    ) -> Dict[str, Any]:
        """
        Procesa múltiples catálogos secuencialmente.

        Args:
            catalogs: Diccionario {nombre_catalogo: num_eventos}
            max_workers: Workers para procesar eventos en paralelo
            parallel_stations: Workers para procesar estaciones

        Returns:
            Diccionario con resultados consolidados
        """
        logger.info(f"Procesando {len(catalogs)} catálogos")
        results = {}

        for catalog, num_events in catalogs.items():
            logger.info(f"  - {catalog.upper()}: {num_events} eventos")
            result = self.process_catalog(
                catalog=catalog,
                num_events=num_events,
                max_workers=max_workers,
                parallel_stations=parallel_stations,
            )
            results[catalog] = result

        return self._build_consolidated_response(results)

    # Métodos auxiliares para respuestas
    def _build_error_response(self, error_msg: str) -> Dict[str, Any]:
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_no_events_response(self, catalog: str) -> Dict[str, Any]:
        return {
            "success": True,
            "catalog": catalog,
            "message": "No hay eventos nuevos",
            "total_events": 0,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_success_response(self, metrics: CatalogMetrics) -> Dict[str, Any]:
        return {
            "success": True,
            "catalog": metrics.catalog,
            "sync_id": metrics.sync_id,
            "status": metrics.status,
            "total_events": metrics.total_events,
            "successful_events": metrics.successful_events,
            "failed_events": metrics.failed_events,
            "total_stations": metrics.total_stations,
            "total_samples": metrics.total_samples,
            "total_processing_time": round(metrics.total_processing_time, 2),
            "avg_processing_time": round(
                metrics.total_processing_time / max(metrics.total_events, 1), 2
            ),
            "error_summary": metrics.error_summary,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_consolidated_response(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """Construye respuesta consolidada para múltiples catálogos"""
        success = all(r.get("success", False) for r in results.values())

        return {
            "success": success,
            "catalogs_processed": len(results),
            "results": results,
            "summary": {
                "total_events": sum(r.get("total_events", 0) for r in results.values()),
                "successful_events": sum(
                    r.get("successful_events", 0) for r in results.values()
                ),
                "failed_events": sum(
                    r.get("failed_events", 0) for r in results.values()
                ),
                "total_stations": sum(
                    r.get("total_stations", 0) for r in results.values()
                ),
                "total_samples": sum(
                    r.get("total_samples", 0) for r in results.values()
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    # Métodos auxiliares para logging
    def _build_invalid_event_result(self, event: Dict) -> EventResult:
        event_id = str(event.get("event_id", "unknown"))
        logger.warning(f"Evento inválido: {event}")
        return EventResult(
            event_id=event_id, success=False, error="Datos de evento incompletos"
        )

    def _log_event_result(self, event_id: str, result: EventResult):
        if result.success:
            logger.info(
                f"{event_id}: {result.stations_processed} estaciones, "
                f"{result.samples_total} muestras en {result.processing_time:.2f}s"
            )
        else:
            logger.warning(f"{event_id}: {result.error}")

    def _get_summary_message(self, metrics: CatalogMetrics) -> str:
        return (
            f"Catálogo {metrics.catalog.upper()}: "
            f"{metrics.successful_events}/{metrics.total_events} eventos, "
            f"{metrics.total_stations} estaciones, {metrics.total_samples} muestras"
        )

    @style_metadata_property
    def metadata(self) -> pd.DataFrame:
        """Devuelve resumen tabulado del procesamiento"""
        if self._metadata_cache is not None:
            return self._metadata_cache

        if not self._metrics:
            self._metadata_cache = pd.DataFrame(
                {"Mensaje": ["No hay datos de procesamiento disponibles"]}
            )
            return self._metadata_cache

        rows = []
        for catalog, metrics in self._metrics.items():
            success_rate = (
                (metrics.successful_events / metrics.total_events * 100)
                if metrics.total_events > 0
                else 0
            )
            avg_time = metrics.total_processing_time / max(metrics.total_events, 1)

            rows.append(
                {
                    "Catálogo": catalog.upper(),
                    "Estado": metrics.status,
                    "Sync ID": metrics.sync_id or "N/A",
                    "Eventos": metrics.total_events,
                    "Exitosos": metrics.successful_events,
                    "Fallidos": metrics.failed_events,
                    "Tasa Éxito (%)": f"{success_rate:.1f}",
                    "Estaciones": metrics.total_stations,
                    "Muestras": metrics.total_samples,
                    "Tiempo Total (s)": f"{metrics.total_processing_time:.1f}",
                    "Tiempo Prom/Evento (s)": f"{avg_time:.2f}",
                    "Errores (resumen)": metrics.error_summary[:100] + "..."
                    if len(metrics.error_summary) > 100
                    else metrics.error_summary,
                }
            )

        df = pd.DataFrame(rows)
        self._metadata_cache = df

        return df

    def close(self):
        """Cierra recursos"""
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
