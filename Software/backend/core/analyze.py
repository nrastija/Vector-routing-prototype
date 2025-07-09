import pandas as pd
import folium
from collections import defaultdict
import matplotlib.pyplot as plt
from pyvis.network import Network
import numpy as np
import os
import networkx as nx
import osmnx as ox
import plotly.graph_objects as go
from backend.benchmark import benchmark

@benchmark()
def convert_to_simple_graph(G_multigraph):
    """
    Convert a NetworkX MultiGraph or MultiDiGraph to a simple Graph or DiGraph.
    Keeps the shortest edge between each pair of nodes based on 'length'.
    """
    if G_multigraph.is_directed():
        G_simple = nx.DiGraph()
    else:
        G_simple = nx.Graph()

    for u, v, data in G_multigraph.edges(data=True):
        if G_simple.has_edge(u, v):
            # Keep the shorter edge
            if data.get("length", float("inf")) < G_simple[u][v].get("length", float("inf")):
                G_simple[u][v].update(data)
        else:
            G_simple.add_edge(u, v, **data)

    for node, data in G_multigraph.nodes(data=True):
        G_simple.add_node(node, **data)

    return G_simple


def _get_road_color(road_type):
    return {
        'motorway': 'red',
        'trunk': 'orange',
        'primary': 'blue',
        'secondary': 'green',
        'tertiary': 'purple'
    }.get(road_type, 'gray')

def _get_road_weight(road_type):
    return 3 if road_type in ['motorway', 'trunk'] else 2 if road_type == 'primary' else 1

def analyze_network(multiG):
    try:
        os.makedirs("backend/data/OSM graphs", exist_ok=True)
        G = convert_to_simple_graph(multiG)
        G.graph["crs"] = multiG.graph.get("crs", "epsg:4326")

        # 1. Street Type Distribution
        highway_counts = defaultdict(int)
        for _, _, data in G.edges(data=True):
            highway_type = data.get('highway', 'unknown')
            if isinstance(highway_type, list):
                highway_type = highway_type[0]
            highway_counts[highway_type] += 1

        df_highway = pd.DataFrame.from_dict(highway_counts, orient='index', columns=['count']).sort_values('count',
                                                                                                           ascending=False)
        df_highway.head(15).plot(kind='bar', color='skyblue', figsize=(12, 6))
        plt.title("Most Common Road Types by OSM Tags")
        plt.xlabel("Road Types (OSM)")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha='right')

        for index, value in enumerate(df_highway.head(15)['count']):
            plt.text(
                index, 
                value + (0.01 * max(df_highway['count'])),  
                f'{value:,}',  
                ha='center',   
                va='bottom',   
                fontsize=9
            )

        plt.tight_layout()
        plt.savefig("backend/data/OSM graphs/OSM_street_types.png", dpi=300)
        plt.close()

        # 2. Road Length Distribution
        lengths = [data['length'] for _, _, data in G.edges(data=True)]
        plt.figure(figsize=(10, 6))
        plt.hist(lengths, bins=50, color='salmon', log=True)
        plt.title("Distribution of Road Lengths (meters, log scale)")
        plt.xlabel("Length (meters)")
        plt.ylabel("Frequency (log scale)")
        plt.grid(True, which="both", ls="--")

        max_length = max(lengths)
        xticks = np.arange(0, max_length + 3000, 3000)
        plt.xticks(xticks)

        plt.tight_layout()

        plt.savefig("backend/data/OSM graphs/OSM_road_lengths.png", dpi=300)
        plt.close()

        # 3. Node Degree Distribution
        degrees = [val for (node, val) in G.degree()]
        plt.figure(figsize=(10, 6))
        plt.hist(degrees, bins=range(1, max(degrees) + 1), color='mediumseagreen', align='left')
        plt.title("Node Degree Distribution")
        plt.xlabel("Degree")
        plt.ylabel("Number of Nodes")
        plt.xticks(range(1, max(degrees) + 1))
        plt.grid(True)
        plt.savefig("backend/data/OSM graphs/OSM_node_degrees.png", dpi=300)
        plt.close()

        # 4. Interactive Folium Map
        print("Generating interactive Folium map...")
        center = [45.308, 16.337]
        m = folium.Map(location=center, zoom_start=12, tiles='CartoDB positron')
        for u, v, data in list(G.edges(data=True)):
            if 'geometry' in data:
                coords = list(zip(data['geometry'].xy[1], data['geometry'].xy[0]))
            else:
                u_node = G.nodes[u]
                v_node = G.nodes[v]
                coords = [(u_node['y'], u_node['x']), (v_node['y'], v_node['x'])]
            road_type = data.get('highway', 'unknown')
            if isinstance(road_type, list):
                road_type = road_type[0]
            folium.PolyLine(
                locations=coords,
                color=_get_road_color(road_type),
                weight=_get_road_weight(road_type),
                opacity=0.8,
                popup=folium.Popup(
                    f"<b>Type:</b> {road_type}<br><b>Length:</b> {data['length']:.1f}m<br><b>From:</b> {u}<br><b>To:</b> {v}",
                    max_width=300
                )
            ).add_to(m)
        m.save("backend/data/OSM graphs/OSM_Folium_Map.html")
        print("All visualizations saved to: data/OSM graphs/")

    except Exception as e:
        print(f"❌ Error during graph analysis: {e}")

@benchmark()
def visualize_full_network(G):
    edge_colors = []
    for _, _, data in G.edges(data=True):
        road_type = data.get("highway", "other")
        if isinstance(road_type, list):
            road_type = road_type[0]
        color = {
            'motorway': 'red',
            'trunk': 'orange',
            'primary': 'blue',
            'secondary': 'green',
            'tertiary': 'purple',
            'residential': '#1a9850'
        }.get(road_type, '#999999')
        edge_colors.append(color)

    fig, ax = ox.plot_graph(
        G,
        edge_color=edge_colors,
        edge_linewidth=0.8,
        node_size=5,
        bgcolor="white",
        show=False,
        close=False
    )
    static_output = "backend/data/OSM graphs/OSM_overview_map.png"
    fig.savefig(static_output, dpi=300, bbox_inches='tight')
    print(f"Saved static map to: {static_output}")
    plt.close()

    print("Converting to simple graph for PyVis...")
    G_simple = nx.Graph()
    for u, v, data in G.edges(data=True):
        G_simple.add_edge(u, v)
    for n, data in G.nodes(data=True):
        G_simple.add_node(n, **data)

    # === PyVis Visualization ===
    print("Generating interactive PyVis network")
    G_sample = G_simple.copy()

    net = Network(height='750px', width='100%', bgcolor='white', font_color='black', notebook=False)
    net.from_nx(G_sample)

    net.set_options("""
    {
      "nodes": {
        "shape": "dot",
        "scaling": {
          "min": 1,
          "max": 5
        }
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "springLength": 95
        },
        "minVelocity": 0.75
      }
    }
    """)

    interactive_output = "backend/data/OSM graphs/OSM_PyVis.html"
    net.write_html(interactive_output)
    print(f"Saved interactive map to: {interactive_output}")

    return fig

@benchmark()
def visualize_network_3d(G, output_html="backend/data/OSM graphs/OSM_network_3D.html"):

    G_simple = nx.Graph()
    for u, v, data in G.edges(data=True):
        G_simple.add_edge(u, v)
    for node, data in G.nodes(data=True):
        G_simple.add_node(node, **data)

    pos = nx.spring_layout(G_simple, dim=3, seed=42)

    edge_x = []
    edge_y = []
    edge_z = []
    for u, v in G_simple.edges():
        x0, y0, z0 = pos[u]
        x1, y1, z1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_z += [z0, z1, None]

    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='lightgray', width=1),
        hoverinfo='none'
    )

    node_x = []
    node_y = []
    node_z = []
    text = []

    for node in G_simple.nodes():
        x, y, z = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        text.append(str(node))

    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers',
        marker=dict(size=3, color='blue', opacity=0.8),
        text=text,
        hoverinfo='text'
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title="3D Road Network Graph",
                        showlegend=False,
                        margin=dict(l=0, r=0, b=0, t=30),
                        scene=dict(
                            xaxis=dict(showbackground=False),
                            yaxis=dict(showbackground=False),
                            zaxis=dict(showbackground=False)
                        )
                    ))

    fig.write_html(output_html)
    print(f"3D network graph saved to: {output_html}")
    return fig
