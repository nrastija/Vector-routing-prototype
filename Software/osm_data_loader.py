import networkx as nx
import osmnx as ox
import pandas as pd
import os
from typing import Dict, List, Optional


def fetch_osm_data(
        place_names: List[str] = ["Varaždin, Croatia", "Čakovec, Croatia"],
        network_type: str = "drive",
        save_to_file: Optional[str] = "data/croatia_cities.graphml"
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

    merged_graph = None

    for name in place_names:
        try:
            print(f"Processing: {name}")

            G = ox.graph_from_place(
                name,
                network_type=network_type,
                which_result=1,
                retain_all=True,
                truncate_by_edge=True
            )


            if merged_graph is None:
                merged_graph = G
            else:
                merged_graph = nx.compose(merged_graph, G)

            print(f"Added {len(G.nodes())} nodes from {name}")

        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            continue

    if merged_graph is None:
        raise ValueError("No valid graphs were created for the given locations")

    merged_graph = ox.distance.add_edge_lengths(merged_graph)

    if save_to_file:
        ox.save_graphml(merged_graph, filepath=save_to_file)
        print(f"Saved merged OSM data to {save_to_file}")

    nodes = [] # Node extraction
    for node_id, data in merged_graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            "lon": data["y"],
            "lat": data["x"],
            "name": data.get("name", ""),
            "vector": [data["y"], data["x"]]
        })

    edges = [] # Edges extraction
    for u, v, data in merged_graph.edges(data=True):
        edges.append({
            "from": u,
            "to": v,
            "length": data["length"],  # meters
            "highway": data.get("highway", ""),
            "name": data.get("name", "")
        })

    # Save nodes to CSV for inspection - TBD if this needs to be removed.
    pd.DataFrame(nodes).to_csv("data/croatia_nodes.csv", index=False)
    print("Saved nodes to data/croatia_nodes.csv")

    return {
        "graph": merged_graph,
        "nodes": nodes,
        "edges": edges
    }