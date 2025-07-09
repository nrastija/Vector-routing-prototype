from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import api_router
import logging
app = FastAPI()


logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Okay for development
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
    expose_headers=["*"]  
)

app.mount("/data/routes", StaticFiles(directory="backend/data/routes"), name="routes")
app.mount("/data/graphs", StaticFiles(directory="backend/data/OSM graphs"), name="graphs")

app.include_router(api_router)