from geopy.geocoders import Nominatim
import osmnx as ox
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Optional

geolocator = Nominatim(user_agent="vector-planner")

def get_city_name(lat: float, lon: float) -> str:
    location = geolocator.reverse((lat, lon), language='en')

    if not location or not location.raw or "address" not in location.raw:
        raise ValueError("Unable to reverse geocode the coordinates.")

    address = location.raw["address"]
    city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
    country = address.get("country")

    if not city or not country:
        raise ValueError("Could not determine city or country.")

    full_name = f"{city}, {country}"
    return full_name

def is_coords(item):
    return isinstance(item, (list, tuple)) and len(item) == 2 and all(isinstance(i, (int, float)) for i in item)

def safe_geocode(place_name: str):
    try:
        return ox.geocode_to_gdf(place_name)  # default (first result)
    except TypeError:
        print(f"Default geocode failed for: {place_name}, trying with which_result=2")
        return ox.geocode_to_gdf(place_name, which_result=2)


def fetch_osm_data(
        recieved_data: List[str] = ["Varaždin, Croatia", "Čakovec, Croatia"],
        network_type: str = "drive",
        save_to_file: Optional[str] = "backend/data/croatia_cities.graphml",
        padding_km: float = 5
) -> Dict:
    """
    Fetch and merge OSM data for multiple cities using an expanded bounding box.

    Args:
        recieved_data: List of OSM-compatible place names
        network_type: "drive", "walk", "bike"
        save_to_file: Optional path to save the merged graph
        padding_km: Extra distance added to bbox in all directions

    Returns:
        dict with "graph", "nodes", and "edges"
    """

    ox.settings.timeout = 300
    ox.settings.log_console = True

    place_names = []
    for item in recieved_data:
        if is_coords(item):
            name = get_city_name(*item)
            place_names.append(name)
        elif isinstance(item, str):
            place_names.append(item)
        else:
            raise ValueError(f"Unsupported route input: {item}")

    print(f"Fetching {len(place_names)} cities...", flush=True)
    print(place_names[0] + " - " + place_names[1])

    # 1. Fetch city boundaries
    print("Fetching city boundaries...")
    city_boundaries = [safe_geocode(name) for name in place_names]
    city_gdf = gpd.GeoDataFrame(pd.concat(city_boundaries, ignore_index=True))
    city_gdf.crs = "EPSG:4326"

    if city_gdf.empty:
        raise ValueError("Failed to fetch any city boundaries.")

    # 2. Bounding Box
    bounds = city_gdf.total_bounds  # [minx, miny, maxx, maxy] → [W, S, E, N]
    west, south, east, north = bounds
    padding_deg = padding_km / 111

    north += padding_deg
    south -= padding_deg
    east += padding_deg
    west -= padding_deg

    # 3. Download graph from bbox
    print("Downloading OSM graph from bounding box...")
    G = ox.graph_from_bbox(
        bbox=(west, south, east, north),
        network_type=network_type,
        retain_all=True,
        simplify=True,
        truncate_by_edge=True,
        custom_filter='["highway"~"motorway|trunk|primary|secondary|tertiary|residential"]'
    )
    print(f"Graph downloaded with {len(G.nodes())} nodes and {len(G.edges())} edges.")
    G = ox.distance.add_edge_lengths(G)

    if save_to_file:
        ox.save_graphml(G, filepath=save_to_file)
        print(f"Saved merged OSM data to {save_to_file}")

    # 4. Extract nodes
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "lon": data["y"],
            "lat": data["x"],
            "name": data.get("name", ""),
            "vector": [data["y"], data["x"]]
        })

    # 5. Extract edges
    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "from": u,
            "to": v,
            "length": data.get("length", 0),
            "highway": data.get("highway", ""),
            "name": data.get("name", "")
        })

    # Save CSVs
    pd.DataFrame(nodes).to_csv("backend/data/OSMLoader_nodes.csv", index=False)
    pd.DataFrame(edges).to_csv("backend/data/OSMLoader_edges.csv", index=False)
    print("Saved expanded nodes and edges to CSV")

    return {
        "graph": G,
        "nodes": nodes,
        "edges": edges
    }
## NOVI OSM DATA LOADER