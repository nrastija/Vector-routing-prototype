import pandas as pd
import osm_data_loader as osm
import analyze

from osm_data_loader import fetch_osm_data
from vector_db import VectorDatabase

def main():
    osm_result = fetch_osm_data(["Varaždin, Croatia", "Čakovec, Croatia"])
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db = VectorDatabase(vector_size=2)  # 2 site: latitute and longitude

    db.create_embeddings(nodes)

    # Step 4: Define coordinates (lat, lon) for route query
    start = (46.3057, 16.3366)  # Varaždin
    end = (46.3843, 16.4337)    # Čakovec

    # Step 5: Find optimal route
    route = db.find_optimal_route(graph, start, end)

    if 'error' in route:
        print(f"Route error: {route['error']}")
        return

    print("Optimal Route:")
    print(f"- Distance: {route['distance_km']:.2f} km")
    print(f"- Path: {route['path']}")
    print(f"- Waypoints: {len(route['waypoints'])} waypoints")




if __name__ == "__main__":
    main()
