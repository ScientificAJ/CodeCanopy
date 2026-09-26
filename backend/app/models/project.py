from pydantic import BaseModel


class ProjectUploadResponse(BaseModel):
    project_id: str
    name: str
    status: str = "uploaded"
    file_count: int