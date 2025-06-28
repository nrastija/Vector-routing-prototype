import networkx as nx
import osmnx as ox
import pandas as pd
import geopandas as gpd
import os
from typing import Dict, List, Optional


def fetch_osm_data(
        place_names: List[str] = ["Varaždin, Croatia", "Čakovec, Croatia"],
        network_type: str = "drive",
        save_to_file: Optional[str] = "data/croatia_cities.graphml",
        buffer_m: float = 5000
) -> Dict:
    """
    Module info (Phase 1):

    Fetch OSM data for multiple cities and merge their networks.

    Args:
        place_names: List of OSM-compatible place names - IMPORTANT! In the thesis the focus is on Varaždin and Čakovec in the Varaždin province.
        network_type: "drive", "walk", "bike" - IMPORTANT! Development is integrated with the "drive" type.
        save_to_file: Save merged graph to this path. This is used for post run graph generation and data analysis.

    Returns:
        {"graph": merged NetworkX graph (.GRAPHML file), "nodes": list, "edges": list}
    """
    os.makedirs("data", exist_ok=True)

    ox.settings.timeout = 300
    ox.settings.log_console = True

    print("Fetching city boundaries...")
    city_boundaries = [ox.geocode_to_gdf(name) for name in place_names]
    city_gdf = gpd.GeoDataFrame(pd.concat(city_boundaries, ignore_index=True))
    city_gdf.crs = "EPSG:4326"

    if city_gdf.empty:
        raise ValueError("Failed to fetch any city boundaries.")

    combined_geom = city_gdf.unary_union

    print("Buffering combined area...")
    combined_gdf = gpd.GeoDataFrame(geometry=[combined_geom], crs=city_gdf.crs)
    combined_proj = combined_gdf.to_crs(epsg=3857)  # Project to meters
    buffered_proj = combined_proj.buffer(buffer_m)
    buffered = gpd.GeoSeries(buffered_proj).set_crs(3857).to_crs(epsg=4326).iloc[0]

    print("Downloading OSM graph from buffered area...")
    G = ox.graph_from_polygon(
        buffered,
        network_type=network_type,
        retain_all=True,
        simplify=True,
        truncate_by_edge=True,
        custom_filter='["highway"~"motorway|trunk|primary|secondary|tertiary|residential"]' # Added new filter to remove unwanted roads
    )

    print(f"Graph downloaded with {len(G.nodes())} nodes and {len(G.edges())} edges.")

    G = ox.distance.add_edge_lengths(G)

    if save_to_file:
        ox.save_graphml(G, filepath=save_to_file)
        print(f"Saved merged OSM data to {save_to_file}")

    nodes = [] # Nodes extraction
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "lon": data["y"],
            "lat": data["x"],
            "name": data.get("name", ""),
            "vector": [data["y"], data["x"]]
        })

    edges = [] # Edges extraction
    for u, v, data in G.edges(data=True):
        edges.append({
            "from": u,
            "to": v,
            "length": data.get("length", 0),
            "highway": data.get("highway", ""),
            "name": data.get("name", "")
        })

    # Save CSVs
    pd.DataFrame(nodes).to_csv("data/OSMLoader_nodes.csv", index=False)
    pd.DataFrame(edges).to_csv("data/OSMLoader_edges.csv", index=False)
    print("Saved expanded nodes and edges to CSV")

    return {
        "graph": G,
        "nodes": nodes,
        "edges": edges
    }