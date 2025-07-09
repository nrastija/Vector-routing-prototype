from fastapi import APIRouter, HTTPException
from backend.models.route import RouteRequest, RouteResponse
from typing import List, Dict
import osmnx as ox
import os
from backend.core.vector_db import VectorDatabase
from backend.core.osm_data_loader import fetch_osm_data
from backend.core.analyze import analyze_network, visualize_full_network, visualize_network_3d
router = APIRouter()

db = VectorDatabase(vector_size=64)

def WriteConsoleOutput(result) -> None:
    print("===================== Optimal Route ====================")
    print("Optimal Result:")
    print(f"Path: {result['path']}")
    print(f"Distance (km): {result['distance_km']:.2f}")
    print(f"Ideal Time (min): {result['ideal_time_min']:.2f}")
    print(f"Realistic Time (min): {result['realistic_time_min']:.2f}")
    print(f"Average Speed (km/h): {result['average_speed_kmh']:.2f}")
    print("Waypoints:")
    for waypoint in result["waypoints"]:
        print(f"  - {waypoint}")
    print("========================================================")


# --- Optimal Route ---
@router.post("/optimal", tags=["Routing"], response_model=RouteResponse)
def get_optimal_route(data: RouteRequest):
    global OSMGraph, OSMNodes 
    try:
        start_coords = data.source_coords
        end_coords = data.dest_coords

        print(start_coords, end_coords)

        route_coords = [start_coords, end_coords]

        osm_result = fetch_osm_data(route_coords)
        OSMGraph = osm_result["graph"]
        OSMNodes = osm_result["nodes"]

        db.create_embeddings(OSMGraph)

        result = db.find_optimal_route(
            source_coords=start_coords,
            dest_coords=end_coords
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        if not result.get("path"):
            raise HTTPException(status_code=404, detail="No route found between the specified coordinates.")

        WriteConsoleOutput(result)

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

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Alternative Routes ---
@router.post("/alternative", tags=["Routing"], response_model=Dict[str, List[RouteResponse]])
def get_alternative_routes(data: RouteRequest):
    global OSMGraph, OSMNodes  # ← ADD THIS

    if OSMGraph is None or OSMNodes is None:
        raise HTTPException(status_code=400, detail="No route has been calculated yet")

    result = db.find_alternative_routes(
        source_coords=data.source_coords,
        dest_coords=data.dest_coords
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"alternatives": result["alternatives"]}


# --- Graphs for optimal route ---
@router.get("/graphs", tags=["Routing"], response_model=Dict[str, str])
def generate_graphs():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Apsolutna putanja do .graphml fajla
        graphml_path = os.path.join(base_dir, "..", "..", "data", "croatia_cities.graphml")
        graphml_path = os.path.normpath(graphml_path)
        graph = ox.load_graphml(graphml_path)
        analyze_network(graph)
        visualize_full_network(graph)
        visualize_network_3d(graph)

        return {"message": "Graphs generated successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

