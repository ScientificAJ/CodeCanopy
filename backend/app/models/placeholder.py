from pydantic import BaseModel


class PlaceholderResponse(BaseModel):
    status: str = "not_implemented"
    message: str
