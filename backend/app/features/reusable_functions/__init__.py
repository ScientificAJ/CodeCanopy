from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class ReusableFunctionRequest(BaseModel):
    """Placeholder input contract for future reusable-function discovery."""


class ReusableFunctionResult(BaseModel):
    """Placeholder output contract for future reusable-function discovery."""


class ReusableFunctionService(FeatureService[ReusableFunctionRequest, ReusableFunctionResult], Protocol):
    """Interface for future reusable-function discovery; no implementation is registered."""