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
    start_coords = data.source_coords
    end_coords = data.dest_coords
    
    print(start_coords, end_coords)

    route_coords = [start_coords, end_coords]

    osm_result = fetch_osm_data(route_coords)
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db.create_embeddings(nodes)

    result = db.find_optimal_route(
        graph=graph,
        source_coords=start_coords,
        dest_coords=end_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    if not result["path"]:
        raise HTTPException(status_code=404, detail="No route found between the specified coordinates.")
    
    return RouteResponse(
        index=None,
        type="optimal",
        path=result["path"],
        distance_km=result["distance_km"],
        ideal_time_min=result["ideal_time_min"],
        realistic_time_min=result["realistic_time_min"],
        average_speed_kmh=result["average_speed_kmh"],
        waypoints=result["waypoints"],
    )

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
