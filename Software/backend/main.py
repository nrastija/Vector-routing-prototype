from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import api_router
import logging
app = FastAPI()


logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# 1. First add CORS middleware (THIS MUST COME FIRST)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Exposes all headers
)

app.mount("/data/routes", StaticFiles(directory="backend/data/routes"), name="routes")
app.mount("/data/graphs", StaticFiles(directory="backend/data/OSM graphs"), name="graphs")

app.include_router(api_router)