from geopy.geocoders import Nominatim
from backend.core.osm_data_loader import fetch_osm_data
from backend.core.vector_db import VectorDatabase

def test_varazdin_cakovec():
    city_data = ["Varaždin, Croatia", "Čakovec, Croatia"]
    osm_result = fetch_osm_data(city_data)
    graph = osm_result["graph"]
    nodes = osm_result["nodes"]

    db = VectorDatabase(vector_size=2)
    db.create_embeddings(nodes)

    geolocator = Nominatim(user_agent="vector_routing")
    start_location = geolocator.geocode(city_data[0])
    end_location = geolocator.geocode(city_data[1])

    if not start_location or not end_location:
        print("ERROR: Could not geocode one or both locations.")
        return

    start = (start_location.latitude, start_location.longitude)
    end = (end_location.latitude, end_location.longitude)

    route = db.find_optimal_route(graph, start, end)
    if 'error' in route:
        print(f"Route error: {route['error']}")
        return

    print("Optimal Route:")
    print(f"- Distance: {route['distance_km']:.2f} km")
    print(f"- Realistic Time: {route['realistic_time_min']:.1f} min")

    route_data = db.find_alternative_routes(graph, start, end)
    if 'error' in route_data:
        print(route_data['error'])
    else:
        for alt in route_data['alternatives']:
            print(f"Alt {alt['index']}: {alt['distance_km']:.2f} km, ~{alt['realistic_time_min']:.1f} min")


test_varazdin_cakovec()
