from fastapi import APIRouter, HTTPException
from backend.models.route import RouteRequest, RouteResponse
from typing import List, Optional, Dict, Any
from backend.core.vector_db import VectorDatabase
from backend.core.osm_data_loader import fetch_osm_data
router = APIRouter()
db = VectorDatabase(vector_size=2)


# --- Optimal Route ---
@router.post("/optimal", tags=["Routing"], response_model=RouteResponse)
def get_optimal_route(data: RouteRequest):
    start_coords = [data.source_coords[0], data.source_coords[1]]
    end_coords = [data.dest_coords[0], data.dest_coords[1]]

    route_coords = [start_coords, end_coords]

    osm_result = fetch_osm_data(route_coords)
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db.create_embeddings(nodes)

    result = db.find_optimal_route(
        graph=graph,
        source_coords=data.source_coords,
        dest_coords=data.dest_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

# --- Alternative Routes ---
@router.post("/alternative", tags=["Routing"], response_model=Dict[str, List[RouteResponse]])
def get_alternative_routes(data: RouteRequest):
    result = db.find_alternative_routes(
        graph=db.graph,
        source_coords=data.source_coords,
        dest_coords=data.dest_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"alternatives": result["alternatives"]}
