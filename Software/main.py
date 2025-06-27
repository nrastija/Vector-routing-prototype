import pandas as pd
import osm_data_loader as osm

if __name__ == "__main__":
    try:
        data = osm.fetch_osm_data()
        print(f"Fetched {len(data['nodes'])} nodes and {len(data['edges'])} edges.")
        print("Sample node:", data["nodes"][0])

        pd.DataFrame(data["nodes"]).to_csv("data/croatia_nodes.csv", index=False)
        print("Saved nodes to data/croatia_nodes.csv")

    except Exception as e:
        print(f"Error in main execution: {str(e)}")