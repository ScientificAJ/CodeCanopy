"""V1 snapshot and project identity models.

These are the canonical shared identities for the GREPO v1 API.
All feature modules must reference these types rather than defining
their own parallel project/snapshot concepts.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Source kinds
# ---------------------------------------------------------------------------

class SourceKind(str, Enum):
    ZIP = "zip"
    GITHUB = "github"


# ---------------------------------------------------------------------------
# Project and Snapshot
# ---------------------------------------------------------------------------

class Project(BaseModel):
    """Minimal mutable display metadata for a project (workspace-scoped)."""

    schema_version: Literal["1.0"] = "1.0"
    id: str
    name: str
    created_at: datetime
    snapshot_ids: list[str] = Field(default_factory=list)


class SnapshotSource(BaseModel):
    """Describes the immutable origin of a snapshot."""

    kind: SourceKind
    # GitHub-specific fields
    owner: str | None = None
    repo: str | None = None
    resolved_commit: str | None = None
    # ZIP-specific fields
    archive_digest: str | None = None
    # Shared
    display_ref: str | None = None  # branch/tag as supplied by the user


class Snapshot(BaseModel):
    """Immutable record of a single repository import.

    Content never mutates after creation.  View preferences and analysis
    results are stored separately and reference this ID.
    """

    schema_version: Literal["1.0"] = "1.0"
    id: str
    project_id: str
    source: SnapshotSource
    manifest_hash: str  # SHA-256 of the accepted file inventory
    policy_version: str = "1.0"
    created_at: datetime
    # status of attached analysis run (if any)
    analysis_run_id: str | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# File inventory
# ---------------------------------------------------------------------------

class FileRecord(BaseModel):
    """One accepted file in a snapshot."""

    schema_version: Literal["1.0"] = "1.0"
    id: str
    snapshot_id: str
    path: str          # normalized POSIX relative path
    name: str
    size: int = Field(ge=0)
    content_hash: str  # SHA-256 of file bytes
    is_text: bool
    encoding: str | None = None
    language: str = "unknown"
    language_basis: str = "extension"
    excluded: bool = False
    exclusion_reason: str | None = None


class FilePage(BaseModel):
    """Paginated file inventory response."""

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str
    files: list[FileRecord]
    total: int
    cursor: str | None = None
    truncated: bool = False


# ---------------------------------------------------------------------------
# Analysis run / job
# ---------------------------------------------------------------------------

class RunStage(str, Enum):
    VALIDATE = "validate"
    SNAPSHOT = "snapshot"
    INVENTORY = "inventory"
    PARSE = "parse"
    RESOLVE = "resolve"
    MAP = "map"
    AI = "ai"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunDiagnostic(BaseModel):
    file_path: str | None = None
    stage: str
    message: str
    severity: Literal["warning", "error"] = "warning"


class AnalysisRun(BaseModel):
    schema_version: Literal["1.1"] = "1.1"
    id: str
    project_id: str
    snapshot_id: str | None = None  # set once snapshot is committed
    status: RunStatus
    stage: RunStage | None = None
    stage_progress: float | None = None  # 0..1 when denominator is known
    event_sequence: int = 0
    diagnostics: list[RunDiagnostic] = Field(default_factory=list)
    cancel_requested: bool = False
    started_at: datetime
    completed_at: datetime | None = None
    result_snapshot_id: str | None = None


class ImportAccepted(BaseModel):
    """Immediate 202 response for an import request."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    project_id: str
    status: Literal["accepted"] = "accepted"
