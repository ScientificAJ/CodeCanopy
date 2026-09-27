from pydantic import BaseModel, Field


class Function(BaseModel):
    name: str
    file: str
    line_start: int
    line_end: int
    calls: list[str] = Field(default_factory=list, exclude=True)
    structural_hash: str | None = Field(default=None, exclude=True)
    structural_signature: list[str] = Field(default_factory=list, exclude=True)

    @property
    def id(self) -> str:
        return f"{self.file}:{self.name}:{self.line_start}"


class CallSite(BaseModel):
    callee_name: str
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
    call_sites: list[CallSite] = Field(default_factory=list)
    dependency_syntax: dict | None = Field(default=None, exclude=True)
    references: list[str] = Field(default_factory=list, exclude=True)


class Project(BaseModel):
    id: str
    name: str
    files: list[File] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    type: str