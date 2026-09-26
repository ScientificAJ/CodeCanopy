from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.v1.router import v1_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(projects_router)
api_router.include_router(v1_router)
