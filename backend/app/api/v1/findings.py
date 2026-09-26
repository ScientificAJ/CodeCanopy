"""Authorized duplicate and potentially-unused finding endpoints."""
from fastapi import APIRouter, Depends

from app.api.v1.snapshots import snapshot_access
from app.features.duplicate_detection import DuplicateDetectionResult, UnusedDetectionResult
from app.features.duplicate_detection.analysis import get_duplicate_findings, get_unused_findings
from app.models.v1.snapshot import Snapshot

router = APIRouter(prefix='/projects', tags=['v1-findings'], dependencies=[Depends(snapshot_access)])


@router.get('/{project_id}/snapshots/{snapshot_id}/findings/duplicates', response_model=DuplicateDetectionResult)
async def duplicate_findings(snap: Snapshot = Depends(snapshot_access)):
    return await get_duplicate_findings(snap.id)


@router.get('/{project_id}/snapshots/{snapshot_id}/findings/unused', response_model=UnusedDetectionResult)
def unused_findings(snap: Snapshot = Depends(snapshot_access)):
    return get_unused_findings(snap.id)