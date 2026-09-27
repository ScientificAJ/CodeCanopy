"""Source-grounded dependency contracts, separate from the containment map."""
from typing import Literal
from pydantic import BaseModel


class DependencyNode(BaseModel):
    id: str
    kind: Literal['file', 'function']
    label: str
    path: str
    file_id: str
    line_start: int = 1
    line_end: int = 1


class DependencyEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    kind: Literal['imports', 'calls']
    file_id: str
    line_start: int
    line_end: int
    basis: Literal['static_binding'] = 'static_binding'


class UnresolvedDependency(BaseModel):
    source_id: str
    name: str
    kind: Literal['imports', 'calls']
    file_id: str
    line_start: int
    reason: str


class DependencyCoverage(BaseModel):
    inventoried_files: int
    analyzed_files: int
    unsupported_files: int
    unresolved_count: int
    truncated: bool
    limitations: list[str]


class DependencyResult(BaseModel):
    schema_version: Literal['1.0'] = '1.0'
    snapshot_id: str
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    unresolved: list[UnresolvedDependency]
    coverage: DependencyCoverage
