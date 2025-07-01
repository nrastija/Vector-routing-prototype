from geopy.geocoders import Nominatim
from osm_data_loader import fetch_osm_data
from vector_db import VectorDatabase

def main():
    city_data = ["Varaždin, Croatia", "Čakovec, Croatia"]
    osm_result = fetch_osm_data(city_data) # Will need to be altered for dynamic implementation
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db = VectorDatabase(vector_size=2)  # 2 site: latitute and longitude

    db.create_embeddings(nodes)

    # Step 4: Define coordinates (lat, lon) for route query

    geolocator = Nominatim(user_agent="vector_routing")

    start_location = geolocator.geocode(city_data[0]) # Will need to be altered for dynamic implementation
    end_location = geolocator.geocode(city_data[1]) # Will need to be altered for dynamic implementation

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
    print(f"- From: {city_data[0]}")
    print(f"- To: {city_data[1]}")
    print(f"- Distance: {route['distance_km']:.2f} km")
    print(f"- Estimated Ideal Time: {route['ideal_time_min']:.1f} minutes")
    print(f"- Estimated Realistic Time: {route['realistic_time_min']:.1f} minutes")
    print(f"- Average speed: {route['average_speed_kmh']:.2f} km/h")
    print(f"- Path: {route['path']}")
    print(f"- Waypoints: {len(route['waypoints'])} waypoints")

    route_data = db.find_alternative_routes(graph, start, end)

    if 'error' in route_data:
        print(route_data['error'])
    else:
        print("\nAlternative routes:")
        for alt in route_data['alternatives']:
            print(f"Alt {alt['index']}: {alt['distance_km']:.2f} km, ~{alt['realistic_time_min']:.1f} min")

if __name__ == "__main__":
    main()
