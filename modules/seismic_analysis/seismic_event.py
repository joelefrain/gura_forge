from datetime import datetime

from typing import Optional

from dataclasses import dataclass


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
