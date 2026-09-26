"""View-only preferences: never written into repository source."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class VirtualGroup(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^group_[a-zA-Z0-9_-]{1,60}$')
    label: str = Field(min_length=1, max_length=60)
    members: list[str] = Field(max_length=500)


class ViewPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.1'] = '1.1'
    labels: dict[str, str] = Field(default_factory=dict, max_length=500)
    groups: list[VirtualGroup] = Field(default_factory=list, max_length=30)
    theme: Literal['light', 'dark'] = 'light'
    order: Literal['folders-first', 'alphabetical'] = 'folders-first'
    focus: str = Field(default='.', max_length=1024)


class MapRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    focus: str = Field(default='.', max_length=1024)
    cursor: int = Field(default=0, ge=0, le=10000)
