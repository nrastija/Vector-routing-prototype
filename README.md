# Vector-Based Route Optimization Prototype

This project explores the use of **vector databases** in optimizing user travel routes using geographic data from **OpenStreetMap (OSM)**. The core goal is to demonstrate how vector embeddings and similarity-based search can assist in planning efficient and interpretable travel paths between locations. This project is made as part of my **Bachelor's thesis** on the theme of **Vector Databases in Route Optimization**

---

##  Project Phases Overview

### Phase 1: Data Preparation & Vectorization
- Extract cities and geographic coordinates from OSM data.
- Represent each city as a vector `[longitude, latitude]`.
- Store vectors and metadata in a vector database -- TBD.

### Phase 2: Backend & Search Logic
- Set up a backend API 
- Implement optimal route search as well as alternative route search.
- Simulate route traversal from point A to B using vector chaining (OSM vectors).
- Return a detailed route: waypoints, distance, estimated duration.

### Phase 3: Frontend 
- Implement frontend app via HTML, Tailwind CSS and LeafletJS
- Integrate Flask for serving HTML templates and handling basic routing (in frontend)
- Integrate frontend with backend APIs

### Phase 4: Testing & Thesis Integration

---

##  Tools & Technologies

| Component       | Tool Suggestion              |
|----------------|------------------------------|
| Vector DB       | Qdrant     |
| Backend         | FastAPI (Python)   |
| Data Source     | osmnx (Python) + Overpass API |
| Routing Engine  | networkx  |
| Frontend | HTML + Tailwind CSS + Leaflet.js + Flask  |
| Deployment | Out of scope of the project |

---

## 💡 Use Case

User inputs two locations. The app retrieves vector representations of each and performs a vector search to return the most efficient travel route, represented as a chain of similar vectors (cities) between A and B.

---

