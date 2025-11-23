import requests

from dateutil import parser
from datetime import datetime, timedelta, timezone

from typing import List

from modules.seismic_analysis.seismic_event import SeismicEvent

from libs.config.config_logger import get_logger

logger = get_logger()


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
            for idx, item in enumerate(data):
                try:
                    date_seed = parser.parse(item["fecha_utc"])
                    hour_seed = parser.parse(item["hora_utc"])

                    # Definir la zona horaria (UTC+0)
                    tz_utc_0 = timezone(timedelta(hours=0))

                    # Combinar fecha y hora, manteniendo UTC
                    event_time = date_seed.replace(
                        hour=hour_seed.hour,
                        minute=hour_seed.minute,
                        second=hour_seed.second,
                        microsecond=hour_seed.microsecond,
                        tzinfo=tz_utc_0,
                    )

                    # Generar event_id si no existe
                    event_id = item.get("codigo")
                    if not event_id:
                        # Generar ID único usando timestamp + ubicación + índice
                        timestamp_str = event_time.strftime("%Y%m%d%H%M%S")
                        event_id = f"IGP_{timestamp_str}"
                        logger.warning(
                            f"Evento sin código en IGP, generado ID: {event_id}"
                        )

                    event = SeismicEvent(
                        event_id=event_id,
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
                        mag_type=item.get("tipomagnitud", "ML"),
                    )
                    events.append(event)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parseando evento IGP en índice {idx}: {e}")
                    continue

            return events

        except requests.RequestException as e:
            logger.error(f"Error en IGP para año {year}: {e}")
            raise
