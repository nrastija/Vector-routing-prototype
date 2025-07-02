from fastapi import APIRouter, HTTPException
from backend.models.route import RouteRequest, RouteResponse
from typing import List, Optional, Dict, Any
from backend.core.vector_db import VectorDatabase

router = APIRouter()
db = VectorDatabase()

# --- Optimal Route ---
@router.post("/optimal", tags=["Routing"], response_model=RouteResponse)
def get_optimal_route(data: RouteRequest):
    result = db.find_optimal_route(
        graph=db.graph,
        source_coords=data.source_coords,
        dest_coords=data.dest_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

