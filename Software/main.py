from geopy.geocoders import Nominatim
from osm_data_loader import fetch_osm_data
from vector_db import VectorDatabase

def main():
    osm_result = fetch_osm_data(["Zagreb, Croatia", "Pécs, Hungary"]) # Will need to be altered for dynamic implementation
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db = VectorDatabase(vector_size=2)  # 2 site: latitute and longitude

    db.create_embeddings(nodes)

    # Step 4: Define coordinates (lat, lon) for route query

    geolocator = Nominatim(user_agent="vector_routing")

    start_location = geolocator.geocode("Zagreb, Croatia") # Will need to be altered for dynamic implementation
    end_location = geolocator.geocode("Pécs, Hungary") # Will need to be altered for dynamic implementation

    if not start_location or not end_location:
        print("ERROR: Could not geocode one or both locations.")
        return

    start = (start_location.latitude, start_location.longitude)
    end = (end_location.latitude, end_location.longitude)

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
