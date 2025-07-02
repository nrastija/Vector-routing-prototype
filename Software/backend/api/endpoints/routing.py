from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.vector_db import VectorDatabase

router = APIRouter()
db = VectorDatabase()

# --- Input schema ---
class RouteRequest(BaseModel):
    source_coords: List[float]  # [lat, lon]
    dest_coords: List[float]    # [lat, lon]

# --- Output schema ---
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

# --- Optimal Route ---
@router.post("/route/optimal", tags=["Routing"], response_model=RouteResponse)
def get_optimal_route(data: RouteRequest):
    result = db.find_optimal_route(
        graph=db.graph,
        source_coords=data.source_coords,
        dest_coords=data.dest_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


