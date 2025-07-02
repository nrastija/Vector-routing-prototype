from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.api.routes import api_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Exposes all headers
)


app.mount("/routes", StaticFiles(directory="backend/data/routes"), name="routes")
app.mount("/graphs", StaticFiles(directory="backend/data/OSM graphs"), name="graphs")

app.include_router(api_router)

