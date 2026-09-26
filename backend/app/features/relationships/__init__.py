from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class RelationshipRequest(BaseModel):
    """Placeholder input contract for future relationship analysis."""


class RelationshipResult(BaseModel):
    """Placeholder output contract for future relationship analysis."""


class RelationshipService(FeatureService[RelationshipRequest, RelationshipResult], Protocol):
    """Interface for a future relationship service; no implementation is registered."""