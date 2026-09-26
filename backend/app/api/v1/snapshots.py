"""Authorized project, inventory, source and structural graph routes."""
from fastapi import APIRouter, Depends, Query

from app.api.v1.session import workspace_session
from app.models.v1.graph import Graph
from app.models.v1.snapshot import FilePage, Project, Snapshot
from app.models.v1.source import CapabilityReport, SourceSlice
from app.services.graph_service import build_structural_graph
from app.services.snapshot_service import (
    authorized_snapshot, build_capability_report, get_inventory, get_project,
    get_project_snapshots, read_source_lines, list_projects, delete_project,
)

router = APIRouter(prefix='/projects', tags=['v1-snapshots'])


def snapshot_access(project_id: str, snapshot_id: str, workspace: str = Depends(workspace_session)) -> Snapshot:
    return authorized_snapshot(project_id, snapshot_id, workspace)


@router.get('', response_model=list[Project])
def projects(workspace: str = Depends(workspace_session)):
    return list_projects(workspace)


@router.get('/{project_id}', response_model=Project)
def project(project_id: str, workspace: str = Depends(workspace_session)):
    return get_project(project_id, workspace)


@router.delete('/{project_id}', status_code=204)
def remove_project(project_id: str, workspace: str = Depends(workspace_session)):
    delete_project(project_id, workspace)


@router.get('/{project_id}/snapshots', response_model=list[Snapshot])
def snapshots(project_id: str, workspace: str = Depends(workspace_session)):
    return get_project_snapshots(project_id, workspace)


@router.get('/{project_id}/snapshots/{snapshot_id}', response_model=Snapshot)
def snapshot(snap: Snapshot = Depends(snapshot_access)):
    return snap


@router.get('/{project_id}/snapshots/{snapshot_id}/files', response_model=FilePage)
def files(snap: Snapshot = Depends(snapshot_access), cursor: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return get_inventory(snap.id, cursor, limit)


@router.get('/{project_id}/snapshots/{snapshot_id}/source/{file_id}', response_model=SourceSlice)
def source(file_id: str, snap: Snapshot = Depends(snapshot_access), line_start: int = Query(1, ge=1),
           line_end: int | None = Query(None, ge=1), max_lines: int = Query(500, ge=1, le=2000)):
    return read_source_lines(snap.id, file_id, line_start, line_end, max_lines)


@router.get('/{project_id}/snapshots/{snapshot_id}/capabilities', response_model=CapabilityReport)
def capabilities(snap: Snapshot = Depends(snapshot_access)):
    return build_capability_report(snap.id)


@router.get('/{project_id}/snapshots/{snapshot_id}/graph', response_model=Graph)
def graph(snap: Snapshot = Depends(snapshot_access), max_entities: int = Query(250, ge=1, le=500),
          focus: str | None = None, cursor: int = Query(0, ge=0)):
    return build_structural_graph(snap.id, max_entities=max_entities, focus=focus, cursor=cursor)


from app.models.v1.view import ViewPreferences, MapRequest
from app.services.view_service import get_preferences, save_preferences, render_view


@router.get('/{project_id}/snapshots/{snapshot_id}/view', response_model=ViewPreferences)
def view_preferences(snap: Snapshot = Depends(snapshot_access)):
    return get_preferences(snap.id)


@router.patch('/{project_id}/snapshots/{snapshot_id}/view', response_model=ViewPreferences)
def update_view(preferences: ViewPreferences, snap: Snapshot = Depends(snapshot_access)):
    return save_preferences(snap.id, preferences)


@router.post('/{project_id}/snapshots/{snapshot_id}/map')
def map_artifact(request: MapRequest, snap: Snapshot = Depends(snapshot_access)):
    return render_view(snap.id, request)


@router.get('/{project_id}/snapshots/{snapshot_id}/entities')
def entities(snap: Snapshot = Depends(snapshot_access)):
    from app.services.graph_service import inventory_entities
    return inventory_entities(snap.id)


from app.features.reusable_functions import (
    ConcreteReusableFunctionService,
    ReusableFunctionRequest,
    ReusableFunctionResult,
)


@router.get(
    '/{project_id}/snapshots/{snapshot_id}/reusable-functions',
    response_model=ReusableFunctionResult,
)
async def reusable_functions(
    snap: Snapshot = Depends(snapshot_access),
    min_callers: int = Query(1, ge=1, le=50),
):
    service = ConcreteReusableFunctionService()
    return await service.execute(
        ReusableFunctionRequest(snapshot_id=snap.id, min_callers=min_callers)
    )
