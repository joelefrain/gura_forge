import pandas as pd

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from concurrent.futures import ThreadPoolExecutor, as_completed

from libs.helpers.metadata_helpers import style_metadata_property

from libs.database.seismic_catalog import SeismicCatalogHandler
from modules.catalog_scraper.csv_extractor import CSVExtractor
from modules.catalog_scraper.api_extractor import (
    USGSExtractor,
    ISCExtractor,
    IGPExtractor,
)
from libs.config.config_variables import TIMEOUT_API_REQUEST, MAX_WORKERS

from libs.config.config_logger import get_logger, log_execution_time

logger = get_logger()


class SeismicScraper:
    """Orquestador principal del scraping sísmico"""

    def __init__(
        self,
        max_workers: int = MAX_WORKERS,
        timeout: int = TIMEOUT_API_REQUEST,
        csv_base_path: Optional[Path] = None,
    ):
        self.db = SeismicCatalogHandler()
        self.max_workers = max_workers
        self.timeout = timeout
        self.csv_base_path = csv_base_path

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
                    min_lat,
                    max_lat,
                    min_lon,
                    max_lon,
                    start_date,
                    end_date,
                    timeout=self.timeout,
                )
            elif catalog == "isc":
                events = ISCExtractor.fetch_events(
                    min_lat,
                    max_lat,
                    min_lon,
                    max_lon,
                    start_date,
                    end_date,
                    timeout=self.timeout,
                )
            elif catalog == "igp":
                events = IGPExtractor.fetch_events(year, timeout=self.timeout)
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

    def scrape_catalog_from_csv(
        self,
        catalog: str,
        csv_path: Path,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        year_filter: Optional[int] = None,
    ) -> Dict[str, int]:
        """Scrape un catálogo desde un archivo CSV específico"""
        logger.info(f"Iniciando carga desde CSV: {catalog.upper()} - {csv_path.name}")

        try:
            # Extraer eventos desde CSV
            events = CSVExtractor.fetch_events(
                csv_path=csv_path,
                year=year_filter,
                min_lat=min_lat,
                max_lat=max_lat,
                min_lon=min_lon,
                max_lon=max_lon,
            )

            if not events:
                logger.warning(f"No se encontraron eventos en {csv_path.name}")
                return {"processed": 0, "inserted": 0, "updated": 0}

            # Guardar en base de datos
            inserted, updated = self.db.bulk_upsert_events(events)

            logger.info(
                f"{catalog.upper()} - {csv_path.name}: {len(events)} eventos "
                f"({inserted} nuevos, {updated} actualizados)"
            )

            return {"processed": len(events), "inserted": inserted, "updated": updated}

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"{catalog.upper()} - {csv_path.name}: {error_msg}")
            return {"processed": 0, "inserted": 0, "updated": 0, "error": error_msg}

    @log_execution_time
    def scrape_events_from_csv(
        self,
        catalogs: List[str],
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        start_year: Optional[int] = None,
    ) -> Dict[str, Dict]:
        """
        Carga eventos desde archivos CSV para los catálogos especificados.

        Cada catálogo puede tener uno o múltiples archivos CSV. Los archivos pueden
        contener datos de múltiples años.

        Estructura esperada:
        data/catalogs/
            ├── usgs/
            │   ├── catalog_complete.csv
            │   ├── additional_data.csv
            │   └── ...
            ├── isc/
            │   ├── isc_catalog.csv
            │   └── ...
            └── igp/
                ├── igp_full.csv
                └── ...

        Args:
            catalogs: Lista de nombres de catálogos (ej: ['usgs', 'isc', 'igp'])
            min_lat, max_lat, min_lon, max_lon: Filtros de coordenadas opcionales
            start_year: Si se especifica, solo carga eventos desde este año en adelante

        Returns:
            Diccionario con resultados por cada archivo CSV procesado
        """
        # Recopilar todos los archivos CSV por catálogo
        tasks = []
        for catalog in catalogs:
            catalog_dir = self.csv_base_path / catalog

            if not catalog_dir.exists():
                logger.warning(f"Directorio no encontrado: {catalog_dir}")
                continue

            # Buscar todos los archivos CSV en el directorio del catálogo
            csv_files = list(catalog_dir.glob("*.csv"))

            if not csv_files:
                logger.warning(f"No se encontraron archivos CSV en {catalog_dir}")
                continue

            logger.info(
                f"Encontrados {len(csv_files)} archivos CSV para {catalog.upper()}"
            )

            for csv_file in csv_files:
                tasks.append((catalog, csv_file))

        if not tasks:
            logger.error("No se encontraron archivos CSV para procesar")
            return {}

        logger.info(
            f"Iniciando carga desde CSV: {len(tasks)} archivos con {self.max_workers} workers"
        )

        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.scrape_catalog_from_csv,
                    catalog,
                    csv_path,
                    min_lat,
                    max_lat,
                    min_lon,
                    max_lon,
                    start_year,
                ): (catalog, csv_path.stem)
                for catalog, csv_path in tasks
            }

            for future in as_completed(future_to_task):
                catalog, filename = future_to_task[future]
                key = f"{catalog}_{filename}"
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = {"error": str(e)}
                    logger.error(f"Error en tarea {key}: {e}")

        # Resumen
        self._calculate_totals(results)
        return results

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
        """Scrape todos los catálogos con procesamiento concurrente desde APIs"""
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
        self._calculate_totals(results)
        return results

    def _calculate_totals(self, results: Dict):
        """Calcula totales de procesamiento"""
        self.total_processed = sum(r.get("processed", 0) for r in results.values())
        self.total_inserted = sum(r.get("inserted", 0) for r in results.values())
        self.total_updated = sum(r.get("updated", 0) for r in results.values())
        self.total_errors = sum(1 for r in results.values() if "error" in r)

    @style_metadata_property
    def metadata(self):
        """Devuelve resumen tabulado de scraping"""
        data = {
            "Total procesado": [self.total_processed],
            "Nuevos": [self.total_inserted],
            "Actualizados": [self.total_updated],
            "Errores": [self.total_errors],
        }
        return pd.DataFrame(data)
