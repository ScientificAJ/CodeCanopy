from __future__ import annotations

import json
from collections import defaultdict

from pydantic import BaseModel

from app.services.snapshot_service import _v1_root, get_snapshot


class ReusableFunctionRequest(BaseModel):
    snapshot_id: str
    min_callers: int = 1


class ReusableGroup(BaseModel):
    function_name: str
    defined_in: str
    defined_line_start: int
    defined_line_end: int
    called_from: list[str]


class ReusableFunctionResult(BaseModel):
    snapshot_id: str
    groups: list[ReusableGroup]
    total_reusable: int


class ConcreteReusableFunctionService:
    async def execute(self, request: ReusableFunctionRequest) -> ReusableFunctionResult:
        get_snapshot(request.snapshot_id)  # auth/existence check
        syntax_path = _v1_root() / request.snapshot_id / "syntax.json"
        try:
            syntax_map: dict = json.loads(syntax_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ReusableFunctionResult(
                snapshot_id=request.snapshot_id, groups=[], total_reusable=0
            )

        definitions: dict[str, dict] = {}  # name -> {file, line_start, line_end}
        callers: dict[str, set[str]] = defaultdict(set)  # name -> set of files that call it

        for file_data in syntax_map.values():
            file_path = file_data.get("path", "")
            for fn in file_data.get("functions", []):
                definitions[fn["name"]] = {
                    "file": file_path,
                    "line_start": fn["line_start"],
                    "line_end": fn["line_end"],
                }
            for cs in file_data.get("call_sites", []):
                callers[cs["callee_name"]].add(file_path)

        groups: list[ReusableGroup] = []
        for name, defn in definitions.items():
            cross_file = callers.get(name, set()) - {defn["file"]}
            if len(cross_file) >= request.min_callers:
                groups.append(
                    ReusableGroup(
                        function_name=name,
                        defined_in=defn["file"],
                        defined_line_start=defn["line_start"],
                        defined_line_end=defn["line_end"],
                        called_from=sorted(cross_file),
                    )
                )

        groups.sort(key=lambda g: len(g.called_from), reverse=True)
        return ReusableFunctionResult(
            snapshot_id=request.snapshot_id,
            groups=groups,
            total_reusable=len(groups),
        )
