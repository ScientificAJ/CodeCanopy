"""V1 API router."""
from fastapi import APIRouter

from app.api.v1.imports import router as imports_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.slots import router as slots_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(imports_router)
v1_router.include_router(snapshots_router)
v1_router.include_router(slots_router)

from app.api.v1.session import router as session_router
v1_router.include_router(session_router)
