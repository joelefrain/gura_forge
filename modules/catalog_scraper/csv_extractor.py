import pandas as pd

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from libs.helpers.df_helpers import read_df_from_csv

from modules.seismic_analysis.seismic_event import SeismicEvent

from libs.config.config_logger import get_logger

logger = get_logger()


class CSVExtractor:
    """Extractor para catálogos en formato CSV"""

    REQUIRED_COLUMNS = [
        "event_id",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "latitude",
        "longitude",
        "depth",
        "magnitude",
        "magType",
        "catalog",
    ]

    @staticmethod
    def fetch_events(
        csv_path: Path,
        year: Optional[int] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
    ) -> List[Dict]:
        """
        Lee eventos desde un archivo CSV
        """
        try:
            df = read_df_from_csv(csv_path)

            # Validar columnas requeridas
            missing_cols = set(CSVExtractor.REQUIRED_COLUMNS) - set(df.columns)
            if missing_cols:
                raise ValueError(
                    f"Columnas faltantes en {csv_path.name}: {missing_cols}"
                )

            # Filtrar por año si se especifica
            if year is not None:
                df = df[df["year"] >= year]

            # Filtrar por coordenadas si se especifican
            if min_lat is not None:
                df = df[df["latitude"] >= min_lat]
            if max_lat is not None:
                df = df[df["latitude"] <= max_lat]
            if min_lon is not None:
                df = df[df["longitude"] >= min_lon]
            if max_lon is not None:
                df = df[df["longitude"] <= max_lon]

            events = []

            for _, row in df.iterrows():
                try:
                    # Validar que los campos mínimos existan
                    if (
                        pd.isnull(row["latitude"])
                        or pd.isnull(row["longitude"])
                        or pd.isnull(row["year"])
                    ):
                        continue

                    # Construir la fecha y hora del evento
                    event_time = datetime(
                        int(row["year"]),
                        int(row["month"]),
                        int(row["day"]),
                        int(row["hour"]),
                        int(row["minute"]),
                        int(row["second"]),
                    )

                    # Crear instancia del evento
                    event = SeismicEvent(
                        event_id=row["event_id"],
                        agency=row["catalog"],
                        catalog=row["catalog"],
                        event_time=event_time,
                        longitude=float(row["longitude"]),
                        latitude=float(row["latitude"]),
                        depth=float(row["depth"])
                        if not pd.isnull(row["depth"])
                        else None,
                        magnitude=float(row["magnitude"])
                        if not pd.isnull(row["magnitude"])
                        else None,
                        mag_type=row.get("magType", ""),
                    )

                    events.append(event)

                except Exception as e:
                    logger.warning(f"Error procesando evento en fila {row.name}: {e}")
                    continue

            logger.info(f"Leídos {len(events)} eventos desde {csv_path.name}")
            return events

        except Exception as e:
            logger.error(f"Error leyendo CSV {csv_path}: {e}")
            return []
