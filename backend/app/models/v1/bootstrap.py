"""Initial workspace payload; individual resources remain available."""
from pydantic import BaseModel

from app.models.v1.graph import GraphEntity
from app.models.v1.snapshot import FilePage, Project, Snapshot
from app.models.v1.source import CapabilityReport
from app.models.v1.view import ViewPreferences


class WorkspaceBootstrap(BaseModel):
    project: Project
    snapshot: Snapshot
    files: FilePage
    entities: list[GraphEntity]
    capabilities: CapabilityReport
    preferences: ViewPreferences
