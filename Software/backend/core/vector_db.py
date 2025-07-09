from itertools import islice
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue
from geopy.geocoders import Nominatim
import networkx as nx
import folium
import matplotlib.pyplot as plt
import osmnx as ox

from backend.benchmark import benchmark

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
    return Path(__file__).parent.parent / "data" / "routes"

def ensure_routes_dir_exists():
    routes_dir = get_routes_dir()
    routes_dir.mkdir(parents=True, exist_ok=True)
    return routes_dir

# Standardized speed limits (Croatian standards)
SPEED_LIMITS = {
    "motorway": 130, "trunk": 110, "primary": 90, "secondary": 80,
    "tertiary": 70, "residential": 50, "unclassified": 60, "service": 30
}

class VectorDatabase:
    def __init__(self, vector_size: int = 64):
        self.client = QdrantClient(":memory:")
        self.vector_size = vector_size
        self.collection_name = "road_network"
        self.geolocator = Nominatim(user_agent="vector_routing")
        self.graph = None 
        
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE
            )
        )

    def _coords_to_vector(self, lat: float, lon: float) -> List[float]:
        return [
            lat, lon, 
            np.sin(lat), np.cos(lat), 
            np.sin(lon), np.cos(lon)
        ] + [0.0] * (self.vector_size - 6)

    @benchmark()
    def create_embeddings(self, graph: nx.MultiDiGraph):
        self.graph = graph
        points = []

        # Node embeddings
        for node, data in graph.nodes(data=True):
            vector = self._coords_to_vector(data['y'], data['x'])
            points.append(PointStruct(
                id=node,
                vector=vector,
                payload={
                    "type": "node",
                    "lat": data['y'],
                    "lon": data['x'],
                    "name": data.get('name', "")
                }
            ))
        
        # Edge embeddings
        edge_id = len(graph.nodes()) + 1  
        for u, v, data in graph.edges(data=True):
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]
            highway_type = data.get('highway', 'unclassified')
            if isinstance(highway_type, list):
                highway_type = highway_type[0]
                
            edge_vec = self._coords_to_vector(
                (u_data['y'] + v_data['y'])/2,
                (u_data['x'] + v_data['x'])/2
            )
            
            points.append(PointStruct(
                id=edge_id,
                vector=edge_vec,
                payload={
                    "type": "edge",
                    "u": u,
                    "v": v,
                    "length": data.get('length', 0),
                    "highway": highway_type,
                    "speed_limit": SPEED_LIMITS.get(highway_type, 50)
                }
            ))
            edge_id += 1

        self.client.upsert(collection_name=self.collection_name, points=points)

    @benchmark()
    def find_optimal_route(self, source_coords, dest_coords, k: int = 3):
        try:
            source_vec = self._coords_to_vector(source_coords[0], source_coords[1])
            dest_vec = self._coords_to_vector(dest_coords[0], dest_coords[1])
            
            source_nodes = self.client.search(
                collection_name=self.collection_name,
                query_vector=source_vec,
                query_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="node"))]
                ),
                limit=k
            )
            
            dest_nodes = self.client.search(
                collection_name=self.collection_name,
                query_vector=dest_vec,
                query_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="node"))]
                ),
                limit=k
            )
            
            best_path = None
            min_length = float('inf')
            
            for src_node in source_nodes:
                for dst_node in dest_nodes:
                    if nx.has_path(self.graph, src_node.id, dst_node.id):
                        path = nx.shortest_path(
                            self.graph, 
                            source=src_node.id, 
                            target=dst_node.id, 
                            weight='length'
                        )
                        path_length = sum(
                            self.graph[u][v][0]['length'] 
                            for u,v in zip(path[:-1], path[1:])
                        )

                        if path_length < min_length:
                            min_length = path_length
                            best_path = path
            
            if not best_path:
                return {"error": "No path found between nearest vector nodes"}
            
            total_distance = 0
            ideal_time_min = 0
            path_details = []
            
            for u, v in zip(best_path[:-1], best_path[1:]):
                edge_data = self.graph[u][v][0]
                length_m = edge_data.get('length', 0)
                total_distance += length_m
                
                road_type = edge_data.get('highway', 'unclassified')
                if isinstance(road_type, list):
                    road_type = road_type[0]
                
                speed_kmh = SPEED_LIMITS.get(road_type, 50)
                edge_km = length_m / 1000
                ideal_time_min += (edge_km / speed_kmh) * 60
                path_details.append({
                    "from": u,
                    "to": v,
                    "length_m": length_m,
                    "road_type": road_type,
                    "speed_kmh": speed_kmh
                })
            
            waypoints = [[self.graph.nodes[n]['y'], self.graph.nodes[n]['x']] for n in best_path]
            output_dir = ensure_routes_dir_exists()
            
            plot_path = os.path.join(output_dir, "route_static.png")
            fig, ax = ox.plot_graph_route(
                self.graph, best_path,
                route_linewidth=6, node_size=0, bgcolor='white',
                show=False, close=True
            )
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            map_path = os.path.join(output_dir, "route_map.html")
            m = folium.Map(location=source_coords, zoom_start=13)
            folium.PolyLine(waypoints, color='blue', weight=5, opacity=0.7).add_to(m)
            folium.Marker(waypoints[0], popup="Start", icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(waypoints[-1], popup="End", icon=folium.Icon(color='red')).add_to(m)
            m.save(map_path)
            
            return {
                "path": best_path,
                "distance_km": total_distance / 1000,
                "ideal_time_min": ideal_time_min,
                "realistic_time_min": ideal_time_min * 1.3,
                "average_speed_kmh": (total_distance / 1000) / ((ideal_time_min * 1.3) / 60),
                "waypoints": waypoints,
                "path_details": path_details,
                "visualizations": {
                    "static_map": plot_path,
                    "interactive_map": map_path
                }
            }
            
        except Exception as e:
            return {"error": f"Routing failed: {str(e)}"}

    @benchmark()
    def find_alternative_routes(self, source_coords, dest_coords, k: int = 3, n_routes: int = 3):
        try:
            source_vec = self._coords_to_vector(source_coords[0], source_coords[1])
            dest_vec = self._coords_to_vector(dest_coords[0], dest_coords[1])
            
            source_nodes = self.client.search(
                collection_name=self.collection_name,
                query_vector=source_vec,
                query_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="node"))]
                ),
                limit=k*2
            )
            
            dest_nodes = self.client.search(
                collection_name=self.collection_name,
                query_vector=dest_vec,
                query_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="node"))]
                ),
                limit=k*2
            )
            
            routes = []
            seen_paths = set()
            
            simplified_graph = _convert_to_simple_graph(self.graph)
            
            for src_node in source_nodes:
                for dst_node in dest_nodes:
                    if len(routes) >= n_routes:
                        break
                        
                    if nx.has_path(simplified_graph, src_node.id, dst_node.id):
                        paths = list(islice(
                            nx.shortest_simple_paths(
                                simplified_graph,
                                source=src_node.id,
                                target=dst_node.id,
                                weight='length'
                            ),
                            n_routes
                        ))
                        
                        for path in paths:
                            path_tuple = tuple(path)
                            if path_tuple not in seen_paths:
                                seen_paths.add(path_tuple)
                                routes.append(path)
                                if len(routes) >= n_routes:
                                    break
            
            if not routes:
                return {"error": "No alternative routes found"}
            
            results = []
            for i, path in enumerate(routes):
                total_distance = 0
                ideal_time_min = 0
                
                for u, v in zip(path[:-1], path[1:]):
                    edge_data = self.graph[u][v][0]
                    length_m = edge_data.get('length', 0)
                    total_distance += length_m
                    
                    road_type = edge_data.get('highway', 'unclassified')
                    if isinstance(road_type, list):
                        road_type = road_type[0]
                    
                    speed_kmh = SPEED_LIMITS.get(road_type, 50)
                    edge_km = length_m / 1000
                    ideal_time_min += (edge_km / speed_kmh) * 60
                
                waypoints = [(self.graph.nodes[n]['y'], self.graph.nodes[n]['x']) for n in path]
                output_dir = ensure_routes_dir_exists()
                map_path = os.path.join(output_dir, f"route_alt_{i+1}.html")
                
                m = folium.Map(location=source_coords, zoom_start=12)
                folium.PolyLine(waypoints, color="blue", weight=5, opacity=0.7).add_to(m)
                folium.Marker(waypoints[0], popup="Start", icon=folium.Icon(color='green')).add_to(m)
                folium.Marker(waypoints[-1], popup="End", icon=folium.Icon(color='red')).add_to(m)
                m.save(map_path)
                
                results.append({
                    "index": i + 1,
                    "path": path,
                    "distance_km": total_distance / 1000,
                    "ideal_time_min": ideal_time_min,
                    "realistic_time_min": ideal_time_min * 1.3,
                    "average_speed_kmh": (total_distance / 1000) / ((ideal_time_min * 1.3) / 60),
                    "waypoints": waypoints,
                    "map_html": map_path
                })
            
            return {"alternatives": results}
            
        except Exception as e:
            return {"error": f"Alternative routing failed: {str(e)}"}