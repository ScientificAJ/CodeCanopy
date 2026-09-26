from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class SummaryRequest(BaseModel):
    """Placeholder input contract for future summary generation."""


class SummaryResult(BaseModel):
    """Placeholder output contract for future summary generation."""


class SummaryService(FeatureService[SummaryRequest, SummaryResult], Protocol):
    """Interface for a future summary service; no implementation is registered."""