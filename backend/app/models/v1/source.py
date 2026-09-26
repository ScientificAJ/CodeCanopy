"""V1 source and capability models."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SourceSlice(BaseModel):
    """A bounded read of source lines from a file in a snapshot.

    Line numbers are 1-based and inclusive.
    """

    schema_version: Literal["1.0"] = "1.0"
    file_id: str
    snapshot_id: str
    path: str
    line_start: int
    line_end: int
    total_lines: int
    content: str
    truncated: bool = False
    content_hash: str  # SHA-256 of *entire* file bytes (not just the slice)


class CapabilityLevel(Enum):
    """Describes what CodeCanopy can do with a given file."""
    FULL = "full"
    TEXT_ONLY = "text_only"
    BINARY = "binary"
    EXCLUDED = "excluded"


class FileCapability(BaseModel):
    file_id: str
    path: str
    language: str
    syntax_extraction: bool = False
    reference_resolution: bool = False
    summary_eligible: bool = False
    level: str = CapabilityLevel.TEXT_ONLY.value
    parser_name: str | None = None
    limitations: list[str] = Field(default_factory=list)


class CapabilityReport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str
    files: list[FileCapability]
    parsed_count: int
    text_only_count: int
    binary_count: int
    excluded_count: int
    limitations: list[str] = Field(default_factory=list)
