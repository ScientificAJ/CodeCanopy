from fastapi import APIRouter, Depends
from app.api.v1.snapshots import snapshot_access
from app.features.dependencies import analyze
from app.models.v1.dependencies import DependencyResult

router = APIRouter(prefix='/projects', tags=['v1-dependencies'], dependencies=[Depends(snapshot_access)])


@router.get('/{project_id}/snapshots/{snapshot_id}/dependencies', response_model=DependencyResult)
def get_dependencies(project_id: str, snapshot_id: str):
    return analyze(snapshot_id)
