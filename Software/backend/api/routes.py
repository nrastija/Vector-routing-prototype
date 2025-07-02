from fastapi import APIRouter
from .endpoints import routing

api_router = APIRouter()
api_router.include_router(routing.router, prefix="/routing", tags=["Routing"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
