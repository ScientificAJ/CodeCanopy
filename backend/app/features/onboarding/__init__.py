from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class OnboardingRequest(BaseModel):
    """Placeholder input contract for future onboarding guidance."""


class OnboardingGuide(BaseModel):
    """Placeholder output contract for future onboarding guidance."""


class OnboardingService(FeatureService[OnboardingRequest, OnboardingGuide], Protocol):
    """Interface for future onboarding guidance; no implementation is registered."""