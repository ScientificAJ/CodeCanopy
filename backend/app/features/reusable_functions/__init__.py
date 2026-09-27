"""Conservative, snapshot-scoped cross-file call candidates from cached syntax."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Protocol

from pydantic import BaseModel, Field

from app.features.base import FeatureService
from app.services.snapshot_service import get_syntax_records
from app.services.v1_errors import WorkspaceError


class ReusableFunctionRequest(BaseModel):
    snapshot_id: str
    min_callers: int = Field(default=1, ge=1, le=50)


class CallEvidence(BaseModel):
    file_id: str
    path: str
    line_start: int
    line_end: int


class ReusableGroup(BaseModel):
    function_name: str
    defined_in: str
    defined_file_id: str
    defined_line_start: int
    defined_line_end: int
    called_from: list[str]
    call_sites: list[CallEvidence]


class ReusableFunctionResult(BaseModel):
    snapshot_id: str
    groups: list[ReusableGroup]
    total_reusable: int
    analyzed_files: int
    ambiguous_names: int
    limitations: list[str]


class ReusableFunctionService(FeatureService[ReusableFunctionRequest, ReusableFunctionResult], Protocol):
    """Contract for snapshot-scoped reuse analysis."""


class ConcreteReusableFunctionService:
    async def execute(self, request: ReusableFunctionRequest) -> ReusableFunctionResult:
        return await asyncio.to_thread(self._execute_sync, request)

    def _execute_sync(self, request: ReusableFunctionRequest) -> ReusableFunctionResult:
        try:
            syntax = get_syntax_records(request.snapshot_id)
        except (OSError, ValueError):
            raise WorkspaceError('ANALYSIS_UNAVAILABLE', 'Cached analysis is unavailable. Import the repository again.', 409) from None
        definitions = defaultdict(list)
        callers = defaultdict(list)
        analyzed = 0
        for file_id, file in sorted(syntax.items()):
            # Older snapshots lack call-site evidence; never claim they were assessed.
            if 'call_sites' not in file.model_fields_set:
                continue
            analyzed += 1
            for function in file.functions:
                definitions[(file.language, function.name)].append((file_id, function))
            for call in file.call_sites:
                callers[(file.language, call.callee_name)].append(CallEvidence(
                    file_id=file_id, path=file.path,
                    line_start=call.line_start, line_end=call.line_end,
                ))

        groups = []
        ambiguous = 0
        for key, matches in sorted(definitions.items()):
            # Never overwrite or arbitrarily attribute duplicate names across scopes/files.
            if len(matches) != 1:
                ambiguous += 1
                continue
            file_id, function = matches[0]
            evidence = sorted(
                (call for call in callers[key] if call.file_id != file_id),
                key=lambda call: (call.path, call.line_start, call.line_end),
            )
            paths = sorted({call.path for call in evidence})
            if len(paths) >= request.min_callers:
                groups.append(ReusableGroup(
                    function_name=function.name, defined_in=function.file,
                    defined_file_id=file_id, defined_line_start=function.line_start,
                    defined_line_end=function.line_end, called_from=paths, call_sites=evidence,
                ))
        groups.sort(key=lambda group: (-len(group.called_from), group.defined_in,
                                       group.defined_line_start, group.function_name))
        limitations = [
            'Candidates match call names within the same language; imports, aliases, object types and dynamic calls are not resolved. Review source before reusing code.',
            'Names with multiple definitions are omitted because their callers are ambiguous.',
            'Only successfully parsed files with call-site evidence are assessed; excluded and unsupported files are not covered.',
        ]
        if analyzed < len(syntax):
            limitations.append('Some cached files predate call-site analysis. Import the repository again to refresh coverage.')
        return ReusableFunctionResult(
            snapshot_id=request.snapshot_id, groups=groups, total_reusable=len(groups),
            analyzed_files=analyzed, ambiguous_names=ambiguous, limitations=limitations,
        )
