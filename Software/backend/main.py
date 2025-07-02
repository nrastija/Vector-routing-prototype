from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.api.routes import api_router
app = FastAPI()

app.mount("/routes", StaticFiles(directory="backend/data/routes"), name="routes")
app.mount("/graphs", StaticFiles(directory="backend/data/OSM graphs"), name="graphs")

app.include_router(api_router)

