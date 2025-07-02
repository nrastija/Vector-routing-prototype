from pydantic import BaseModel
from typing import List, Optional

class RouteRequest(BaseModel):
    source_coords: List[float]  # [lat, lon]
    dest_coords: List[float]    # [lat, lon]

class RouteResponse(BaseModel):
    index: Optional[int] = None
    type: Optional[str] = None
    path: List[int]
    distance_km: float
    ideal_time_min: float
    realistic_time_min: float
    average_speed_kmh: float
    waypoints: List[List[float]]
    map_html: str