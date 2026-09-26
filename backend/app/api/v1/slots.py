"""Integration slot endpoints.

These routes return explicit NOT_CONNECTED responses for deferred
feature modules.  They are present so the frontend can navigate to
these pages and render an intentional placeholder rather than a 404.

IMPORTANT: Never return HTTP 200 with invented results here.  The
IntegrationSlotResponse schema explicitly signals "not connected".
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from app.api.v1.snapshots import snapshot_access

from app.models.v1.slots import (
    SLOT_ASK,
    SLOT_DEPENDENCIES,
    SLOT_PROPOSALS,
    SLOT_REUSE,
    SLOT_SUMMARIES,
    IntegrationSlotResponse,
)

router = APIRouter(prefix="/projects", tags=["v1-slots"], dependencies=[Depends(snapshot_access)])

_SNAPSHOT_PATH = "/{project_id}/snapshots/{snapshot_id}"


# INTEGRATION_SLOT: summaries.context-panel
@router.get(
    _SNAPSHOT_PATH + "/summaries",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_summaries_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for the AI file/folder summaries feature.

    Returns a NOT_CONNECTED response until the summaries feature is wired in.
    The frontend must render an explicit placeholder, not treat this as empty success.
    """
    return SLOT_SUMMARIES


# INTEGRATION_SLOT: dependencies.workspace
@router.get(
    _SNAPSHOT_PATH + "/dependencies",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_dependencies_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for the connections/change-impact feature."""
    return SLOT_DEPENDENCIES


# INTEGRATION_SLOT: reuse.findings
@router.get(
    _SNAPSHOT_PATH + "/findings/reuse",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_reuse_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for reusable/shared function discovery."""
    return SLOT_REUSE


# INTEGRATION_SLOT: ask.workspace
@router.get(
    _SNAPSHOT_PATH + "/ask",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_ask_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for the Ask CodeCanopy conversational feature."""
    return SLOT_ASK


@router.post(
    _SNAPSHOT_PATH + "/answers",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def post_answer_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for answer generation – not connected."""
    return SLOT_ASK


# INTEGRATION_SLOT: proposals.detail
@router.get(
    _SNAPSHOT_PATH + "/proposals",
    response_model=IntegrationSlotResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def get_proposals_slot(project_id: str, snapshot_id: str) -> IntegrationSlotResponse:
    """Slot endpoint for the proposals feature."""
    return SLOT_PROPOSALS
