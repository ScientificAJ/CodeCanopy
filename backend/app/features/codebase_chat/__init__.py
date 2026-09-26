from typing import Protocol

from pydantic import BaseModel

from app.features.base import FeatureService


class CodebaseQuestion(BaseModel):
    """Placeholder input contract for future codebase questions."""


class CodebaseAnswer(BaseModel):
    """Placeholder output contract for future codebase answers."""


class CodebaseChatService(FeatureService[CodebaseQuestion, CodebaseAnswer], Protocol):
    """Interface for future codebase chat; no implementation is registered."""