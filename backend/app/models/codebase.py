from pydantic import BaseModel, Field


class Function(BaseModel):
    name: str
    file: str
    line_start: int
    line_end: int


class Class(BaseModel):
    name: str
    file: str
    line_start: int
    line_end: int


class File(BaseModel):
    path: str
    name: str
    language: str
    size: int = Field(ge=0)
    functions: list[Function] = Field(default_factory=list)
    classes: list[Class] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    files: list[File] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    type: str