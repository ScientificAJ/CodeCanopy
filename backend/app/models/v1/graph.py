"""V1 structural graph model.

The graph returned here is a *structural containment* graph derived from
the file/directory hierarchy and any available import relationships.
It is NOT a semantic dependency graph; edges only represent observed
structural facts (containment, imports where resolved).

This model is the shared contract that the Map and future Dependencies
features consume.  The Dependencies feature will add its own relation
kinds and overlay data through its integration slot.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EntityKind(str, Enum):
    REPOSITORY = "repository"
    DIRECTORY = "folder"
    FILE = "file"
    # VIRTUAL_GROUP is user-created; it maps to real underlying entities
    VIRTUAL_GROUP = "virtual_group"


class RelationKind(str, Enum):
    GROUPS = "groups"  # explicit view-only membership, not a source relationship
    CONTAINS = "contains"
    IMPORTS = "imports"       # observed import statement (may be unresolved)
    CALLS = "calls"           # future: resolved call site
    DECLARES_DEPENDENCY = "declares_dependency"  # manifest entry


class RelationBasis(str, Enum):
    OBSERVED = "observed"
    RESOLVED = "resolved"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class GraphEntity(BaseModel):
    id: str
    kind: EntityKind
    label: str
    path: str | None = None   # present for files and directories
    file_id: str | None = None  # present for FILE entities; links to FileRecord
    parent_id: str | None = None
    child_count: int = 0
    metadata: dict = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class GraphRelation(BaseModel):
    id: str
    source_id: str
    target_id: str
    kind: RelationKind
    basis: RelationBasis
    evidence_ids: list[str] = Field(default_factory=list)
    unresolved: bool = False


class GraphCoverage(BaseModel):
    inventoried_files: int
    parsed_files: int
    unresolved_references: int
    excluded_paths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    truncated: bool = False
    total_entities: int = 0
    returned_entities: int = 0


class Graph(BaseModel):
    """Bounded structural graph for a snapshot.

    Clients should inspect `coverage.truncated` and `coverage.limitations`
    before presenting this as a complete picture of the repository.
    """

    schema_version: Literal["1.1"] = "1.1"
    snapshot_id: str
    fixture_only: bool = False
    entities: list[GraphEntity]
    relations: list[GraphRelation]
    coverage: GraphCoverage
    evidence: list[dict] = Field(default_factory=list)
    focus_path: str = "."
    cursor: int = 0
    next_cursor: int | None = None
    child_total: int = 0


class ViewState(BaseModel):
    """User-local view preferences stored separately from source facts."""

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str
    # Virtual group definitions created by the user
    virtual_groups: list[dict] = Field(default_factory=list)
    # Entity display overrides (label renames, color choices)
    display_overrides: dict[str, dict] = Field(default_factory=dict)
    # Last camera state for the map
    camera: dict = Field(default_factory=dict)
