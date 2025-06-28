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
            source_node = ox.distance.nearest_nodes(graph, #Start node
                                                    X=source_coords[1],
                                                    Y=source_coords[0])

            dest_node = ox.distance.nearest_nodes(graph, #End node
                                                  X=dest_coords[1],
                                                  Y=dest_coords[0])

            if not nx.has_path(graph, source_node, dest_node):
                return {"error": "No path exists between these nodes"}

            path = nx.shortest_path(graph, #Shortest path calculation
                                    source=source_node,
                                    target=dest_node,
                                    weight='length')

            total_distance = 0
            for u, v in zip(path[:-1], path[1:]):
                if graph.has_edge(u, v):
                    edges = graph[u][v]
                    min_length = min(edge_data.get('length', 0) for edge_data in edges.values())
                    total_distance += min_length

            distance = total_distance / 1000

            waypoints = [(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in path]

            plot_path = "data/routes/route_static_DB.png"
            fig, ax = ox.plot_graph_route(
                graph,
                path,
                route_linewidth=6,
                node_size=0,
                bgcolor='white',
                show=False,
                close=False
            )
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()

            # Generate Folium map
            map_path = "data/routes/route_map_DB.html"
            m = folium.Map(location=source_coords, zoom_start=13)
            folium.PolyLine(
                waypoints,
                color='blue',
                weight=5,
                opacity=0.7
            ).add_to(m)
            folium.Marker(
                waypoints[0],
                popup="Start",
                icon=folium.Icon(color='green')
            ).add_to(m)
            folium.Marker(
                waypoints[-1],
                popup="End",
                icon=folium.Icon(color='red')
            ).add_to(m)
            m.save(map_path)

            return {
                "path": path,
                "distance_km": distance,
                "waypoints": waypoints,
                "map_html": map_path,
                "plot_path": plot_path
            }

        except Exception as e:
            return {"error": f"Routing failed: {str(e)}"}