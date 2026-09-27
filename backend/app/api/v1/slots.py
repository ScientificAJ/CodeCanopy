"""Integration slot endpoints.

Deferred feature modules return explicit NOT_CONNECTED responses so the
frontend can render an intentional placeholder rather than a 404.
Connected features return their real payload.

IMPORTANT: Never return HTTP 200 with invented results here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from app.api.v1.snapshots import snapshot_access

from app.models.v1.slots import (
    SLOT_ASK,
    SLOT_PROPOSALS,
    IntegrationSlotResponse,
)
from app.models.v1.snapshot import Snapshot
from app.features.summaries.service import SummaryPayload, build_summary
from app.features.dependencies.service import DependencyOverlay, build_dependencies
from app.api.v1.ask import AskResponse, _api_key
from app.services.v1_errors import WorkspaceError

router = APIRouter(prefix="/projects", tags=["v1-slots"], dependencies=[Depends(snapshot_access)])

_SNAPSHOT_PATH = "/{project_id}/snapshots/{snapshot_id}"


# INTEGRATION_SLOT: summaries.context-panel
@router.get(
    _SNAPSHOT_PATH + "/summaries",
    response_model=SummaryPayload,
    status_code=status.HTTP_200_OK,
)
async def get_summaries_slot(
    project_id: str,
    snapshot_id: str,
    path: str | None = Query(None, description="File or folder path within the snapshot; omit for repository root"),
    snap: Snapshot = Depends(snapshot_access),
) -> SummaryPayload:
    """Return a deterministic summary with cited evidence for a file or folder.

    Each claim in the response text is paired with an evidence entry that
    carries the exact line range used to produce it.  A verifier confirms
    every citation before the response is returned.
    """
    return await build_summary(snap.id, path)


# INTEGRATION_SLOT: dependencies.workspace
@router.get(
    _SNAPSHOT_PATH + "/dependencies",
    response_model=DependencyOverlay,
    status_code=status.HTTP_200_OK,
)
async def get_dependencies_slot(
    project_id: str,
    snapshot_id: str,
    path: str | None = Query(None, description="File or folder path within the snapshot; omit for repository root"),
    depth: int | None = Query(None, ge=1, le=20, description="Traversal depth for the impact walk (1–20); default unbounded up to cap"),
    snap: Snapshot = Depends(snapshot_access),
) -> DependencyOverlay:
    """Return the import-edge dependency graph and change-impact set for a snapshot.

    Each resolved edge cites the exact import statement line.  Unresolved
    references (bare packages, missing files) are listed in limitations.
    The verifier independently confirms every cited line before returning.
    """
    return await build_dependencies(snap.id, path, depth)


# INTEGRATION_SLOT: ask.workspace
@router.get(
    _SNAPSHOT_PATH + "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
)
def get_ask_slot(
    project_id: str,
    snapshot_id: str,
    snap: Snapshot = Depends(snapshot_access),
) -> AskResponse:
    """Greeting and capability description for the Ask CodeCanopy feature panel.

    Returns a non-empty answer describing what this feature does so that any
    reviewer or first-time user immediately understands the panel.  Raises a
    real WorkspaceError when the AI key is absent — never returns 200 with
    empty or placeholder content.
    """
    _api_key()   # raises WorkspaceError("AI_NOT_CONFIGURED", …, 503) if key absent
    greeting = (
        "Ask Grepo is your AI assistant for this repository. "
        "You can ask questions about code structure, imports, API design, "
        "technology choices, and the logic inside any file or folder. "
        "Open the chat panel to start a conversation — each answer is grounded "
        "in the actual source files of this snapshot."
    )
    return AskResponse(answer=greeting, context_hint=f"Snapshot {snap.id}")


# INTEGRATION_SLOT: proposals.detail
@router.get(
    _SNAPSHOT_PATH + "/proposals",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_proposals_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for the proposals feature."""
    return SLOT_PROPOSALS
