from typing import Protocol, TypeVar

from pydantic import BaseModel

RequestT = TypeVar("RequestT", bound=BaseModel, contravariant=True)
ResultT = TypeVar("ResultT", bound=BaseModel, covariant=True)


class FeatureService(Protocol[RequestT, ResultT]):
    async def execute(self, request: RequestT) -> ResultT:
        """Execute a feature request and return its structured result."""