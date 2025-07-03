from itertools import islice
import os
from pathlib import Path

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from geopy.geocoders import Nominatim
import networkx as nx
import folium
import matplotlib.pyplot as plt
import osmnx as ox


def _convert_to_simple_graph(graph: nx.MultiDiGraph) -> nx.DiGraph:
    simple_graph = nx.DiGraph()

    for node, data in graph.nodes(data=True):
        simple_graph.add_node(node, **data)

    for u, v, data in graph.edges(data=True):
        length = data.get('length', float('inf'))
        if not simple_graph.has_edge(u, v) or length < simple_graph[u][v].get('length', float('inf')):
            simple_graph.add_edge(u, v, **data)

    return simple_graph

def get_routes_dir() -> Path:
    """Returns the absolute path to routes directory"""
    # Adjust this path to match your project structure
    return Path(__file__).parent.parent / "data" / "routes"

def ensure_routes_dir_exists():
    """Creates routes directory if it doesn't exist"""
    routes_dir = get_routes_dir()
    routes_dir.mkdir(parents=True, exist_ok=True)
    return routes_dir

# Standardized speed limits (standard is Croatian)
SPEED_LIMITS = {
    "motorway": 130,
    "trunk": 110,
    "primary": 90,
    "secondary": 80,
    "tertiary": 70,
    "residential": 50,
    "unclassified": 60,
    "service": 30
}


class VectorDatabase:
    def __init__(self, vector_size: int = 64):
        self.client = QdrantClient(":memory:")
        self.vector_size = vector_size
        self.collection_name = "road_network_vectors"
        self.geolocator = Nominatim(user_agent="vector_routing")

        # Create optimized collection
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE
            )
        )

    def create_embeddings(self, nodes: list):
        points = []
        for node in nodes:
            point = PointStruct(
                id=node["id"],
                vector=node["vector"],
                payload={
                    "lat": node["lat"],
                    "lon": node["lon"],
                    "name": node.get("name", "")
                }
            )
            points.append(point)

        self.client.upsert(collection_name=self.collection_name, points=points)

    def find_optimal_route(self, graph: nx.MultiDiGraph, source_coords, dest_coords):
        if 'crs' not in graph.graph or graph.graph['crs'] is None:
            graph.graph['crs'] = 'epsg:4326'

        try:
            # Get nodes and check connectivity
            source_node = ox.distance.nearest_nodes(graph, X=source_coords[1], Y=source_coords[0])
            dest_node = ox.distance.nearest_nodes(graph, X=dest_coords[1], Y=dest_coords[0])

            if not nx.has_path(graph, source_node, dest_node):
                return {"error": "No path exists between these nodes"}

            # Calculate path and metrics
            path = nx.shortest_path(graph, source=source_node, target=dest_node, weight='length')

            total_distance = 0
            ideal_time_min = 0

            for u, v in zip(path[:-1], path[1:]):
                if graph.has_edge(u, v):
                    edges = graph[u][v]
                    best_edge = min(edges.values(), key=lambda e: e.get('length', float('inf')))
                    length_m = best_edge.get('length', 0)
                    total_distance += length_m

                    road_type = best_edge.get('highway', 'unclassified')
                    if isinstance(road_type, list):
                        road_type = road_type[0]

                    speed_kmh = SPEED_LIMITS.get(road_type, 50)
                    edge_km = length_m / 1000
                    ideal_time_min += (edge_km / speed_kmh) * 60

            realistic_time_min = ideal_time_min * 1.3  # 30% buffer
            distance_km = total_distance / 1000
            average_speed_kmh = distance_km / (realistic_time_min / 60)
            waypoints = [[graph.nodes[n]['y'], graph.nodes[n]['x']] for n in path]

            # Set up output directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(current_dir, "..", "data", "routes")
            os.makedirs(output_dir, exist_ok=True)

            # Save static plot
            plot_path = os.path.join(output_dir, "route_static_DB.png")
            fig, ax = ox.plot_graph_route(
                graph,
                path,
                route_linewidth=6,
                node_size=0,
                bgcolor='white',
                show=False,
                close=True  # Changed to True to properly close the figure
            )
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig) 

            # Generate Folium map (save as HTML)
            map_path = os.path.join(output_dir, "route_map_DB.html")  # Changed to HTML
            m = folium.Map(location=source_coords, zoom_start=13)
            folium.PolyLine(waypoints, color='blue', weight=5, opacity=0.7).add_to(m)
            folium.Marker(waypoints[0], popup="Start", icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(waypoints[-1], popup="End", icon=folium.Icon(color='red')).add_to(m)
            m.save(map_path)

            # Return paths relative to web root
            return {
                "path": path,
                "distance_km": distance_km,
                "ideal_time_min": ideal_time_min,
                "realistic_time_min": realistic_time_min,
                "average_speed_kmh": average_speed_kmh,
                "waypoints": waypoints,
            }

        except Exception as e:
            return {"error": f"Routing failed: {str(e)}"}

    def find_alternative_routes(self, graph: nx.MultiDiGraph, source_coords, dest_coords):
        if 'crs' not in graph.graph or graph.graph['crs'] is None:
            graph.graph['crs'] = 'epsg:4326'

        try:
            source_node = ox.distance.nearest_nodes(graph, #Start node
                                                    X=source_coords[1],
                                                    Y=source_coords[0])

            dest_node = ox.distance.nearest_nodes(graph, #End node
                                                  X=dest_coords[1],
                                                  Y=dest_coords[0])

            if not nx.has_path(graph, source_node, dest_node):
                return {"error": "No path exists between these nodes"}

            simplified_graph = _convert_to_simple_graph(graph)

            # Hybrid approach: route 3 - close alternative, route 7 . medium alternative, route 15 - long alternative
            alternative_routes = [2, 6, 14]

            all_paths = list(islice(
                nx.shortest_simple_paths(simplified_graph, source_node, dest_node, weight='length'),
                max(alternative_routes) + 1
            ))

            selected_paths = [all_paths[i] for i in alternative_routes]# Skip optimal path - function find_optimal_route

            routes = []
            for i, path in enumerate(selected_paths):
                total_distance = 0
                ideal_time_min = 0

                for u, v in zip(path[:-1], path[1:]):
                    if graph.has_edge(u, v):
                        edges = graph[u][v]
                        best_edge = min(edges.values(), key=lambda e: e.get('length', float('inf')))
                        length_m = best_edge.get('length', 0)
                        total_distance += length_m

                        road_type = best_edge.get('highway', 'unclassified')
                        if isinstance(road_type, list):
                            road_type = road_type[0]

                        speed_kmh = SPEED_LIMITS.get(road_type, 50)
                        edge_km = length_m / 1000
                        ideal_time_min += (edge_km / speed_kmh) * 60

                realistic_time_min = ideal_time_min * 1.3
                distance_km = total_distance / 1000
                average_speed_kmh = total_distance / (realistic_time_min / 60)
                waypoints = [(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in path]

                current_dir = os.path.dirname(__file__)
                output_dir = os.path.join(current_dir, "data", "routes")
                os.makedirs(output_dir, exist_ok=True)

                # Save map for each route
                map_path = os.path.join(output_dir, f"route_alt_{i + 1}.html")
                m = folium.Map(location=source_coords, zoom_start=12)
                folium.PolyLine(waypoints, color="blue", weight=5, opacity=0.7).add_to(m)
                folium.Marker(waypoints[0], popup="Start", icon=folium.Icon(color='green')).add_to(m)
                folium.Marker(waypoints[-1], popup="End", icon=folium.Icon(color='red')).add_to(m)
                m.save(map_path)

                print(waypoints)

                routes.append({
                    "index": i + 1,
                    "path": path,
                    "distance_km": distance_km,
                    "ideal_time_min": ideal_time_min,
                    "realistic_time_min": realistic_time_min,
                    "average_speed_kmh": average_speed_kmh,
                    "waypoints": waypoints,
                    "map_html": map_path
                })

            return {
                "alternatives": routes
            }

        except Exception as e:
            return {"error": f"Routing failed: {str(e)}"}
