from fastapi import APIRouter
from .endpoints import routing

api_router = APIRouter()
api_router.include_router(routing.router, prefix="/route", tags=["Routing"])

