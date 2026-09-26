from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class DuplicateDetectionRequest(BaseModel):
    """Placeholder input contract for future duplicate detection."""


class DuplicateDetectionResult(BaseModel):
    """Placeholder output contract for future duplicate detection."""


class DuplicateDetectionService(FeatureService[DuplicateDetectionRequest, DuplicateDetectionResult], Protocol):
    """Interface for a future duplicate detector; no implementation is registered."""