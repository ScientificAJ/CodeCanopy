from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.features.base import FeatureService


class DuplicateDetectionRequest(BaseModel):
    snapshot_id: str


class FunctionEvidence(BaseModel):
    id: str
    name: str
    file_id: str
    path: str
    line_start: int
    line_end: int


class DuplicateCandidate(BaseModel):
    id: str
    functions: list[FunctionEvidence]
    structural_similarity: float = Field(ge=0, le=1)
    semantic_similarity: float | None = Field(default=None, ge=0, le=1)
    confidence: Literal['high', 'medium', 'low']
    review_recommended: bool = True
    method: str


class PotentiallyUnusedFunction(BaseModel):
    id: str
    function: FunctionEvidence
    status: Literal['potentially_unused'] = 'potentially_unused'
    method: str = 'static_call_reference_graph'
    explanation: str = 'No in-repository call or reference was found; dynamic use may not be visible.'


class AnalysisCoverage(BaseModel):
    inventoried_files: int
    parsed_files: int
    analyzed_functions: int
    unresolved_references: int
    limitations: list[str] = Field(default_factory=list)


class DuplicateDetectionResult(BaseModel):
    schema_version: Literal['1.0'] = '1.0'
    snapshot_id: str
    candidates: list[DuplicateCandidate]
    coverage: AnalysisCoverage


class UnusedDetectionResult(BaseModel):
    schema_version: Literal['1.0'] = '1.0'
    snapshot_id: str
    findings: list[PotentiallyUnusedFunction]
    coverage: AnalysisCoverage


class DuplicateDetectionService(FeatureService[DuplicateDetectionRequest, DuplicateDetectionResult], Protocol):
    """Snapshot-scoped duplicate analysis contract."""