"""Reproduce the verifier attack table shown in the README.

Each case constructs a real dependency edge by hand and runs it through the
real verifier. Nothing here is mocked: every result is the verifier's own
answer to a graph it was actually given.

Run from the backend directory:

    .venv/bin/python scripts/demo_verifier.py
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ['CODECANOPY_SNAPSHOTS_DIR'] = tempfile.mkdtemp() + '/snapshots'

from app.features.dependencies.service import (  # noqa: E402
    DependencyEdge,
    DependencyGraph,
    DependencyOverlay,
    EdgeEndpoint,
    EvidenceItem,
    SourceRange,
    _build_graph_raw,
    build_dependencies,
)
from app.features.dependencies.verifier import verify_dependency_edges  # noqa: E402
from app.services.inventory_service import entity_id  # noqa: E402
from app.services.snapshot_service import (  # noqa: E402
    create_snapshot_from_project,
    get_inventory,
)

SNAPSHOT_FILES = {
    'pkg/utils.py': 'def helper():\n    return 42\n',
    'pkg/main.py': 'from .utils import helper\n\ndef run():\n    return helper()\n',
    'pkg/app.py': 'from .main import run\nimport os\n\nrun()\n',
}


def make_snapshot():
    root = pathlib.Path(tempfile.mkdtemp())
    source = root / 'source'
    source.mkdir()
    for name, text in SNAPSHOT_FILES.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    snap, _ = create_snapshot_from_project('a' * 32, source, 'test', 'verifier-demo')
    return snap


def build_edge(snap, main_rec, spec, line, target_file_id, target_path):
    """An edge whose citation is always legitimate, with a caller-chosen target."""
    evidence = EvidenceItem(
        id=uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=main_rec.id,
        path=main_rec.path,
        range=SourceRange(line_start=line, line_end=line),
        content_sha256=main_rec.content_hash,
        basis='resolved',
    )
    edge_id = uuid.uuid4().hex
    graph = DependencyGraph(
        edges=[
            DependencyEdge(
                id=edge_id,
                source=EdgeEndpoint(
                    entity_id=entity_id(snap.id, 'pkg/main.py', 'file'),
                    path='pkg/main.py',
                    file_id=main_rec.id,
                ),
                target=EdgeEndpoint(
                    entity_id=entity_id(snap.id, target_path, 'file'),
                    path=target_path,
                    file_id=target_file_id,
                ),
                kind='imports',
                evidence_id=evidence.id,
            )
        ],
        unresolved=[],
        evidence=[evidence],
    )
    return graph, {edge_id: spec}, {main_rec.id: 'python'}


def main() -> None:
    snap = make_snapshot()
    records = {r.path: r for r in get_inventory(snap.id, limit=100).files}
    main_rec = records['pkg/main.py']
    utils_rec = records['pkg/utils.py']

    print(f'Snapshot {snap.id}')
    print()

    raw, spec_map, lang_map = _build_graph_raw(snap.id)
    print('Honest graph, built from real import statements')
    for edge in raw.edges:
        evidence = next(e for e in raw.evidence if e.id == edge.evidence_id)
        print(
            f'  {edge.source.path:14} -> {edge.target.path:14} '
            f'line {evidence.range.line_start}  specifier {spec_map[edge.id]!r}'
        )
    _, report = verify_dependency_edges(snap.id, raw, lang_map, spec_map)
    print(f'  verifier: {report.verified} verified, {report.unverified} unverified')
    print()

    ghost = 'f' * 32
    other_snapshot_rec = records['pkg/app.py']
    cases = [
        (
            'Citation entirely valid, target file does not exist',
            build_edge(snap, main_rec, '.utils', 1, ghost, 'fictional/target.py'),
        ),
        (
            'Null target (external or unresolved)',
            build_edge(snap, main_rec, '.utils', 1, None, 'external/package'),
        ),
        (
            'Citation on a real line that is not an import',
            build_edge(snap, main_rec, '.utils', 3, utils_rec.id, 'pkg/utils.py'),
        ),
        (
            'Citation pointing past end of file',
            build_edge(snap, main_rec, '.utils', 999, utils_rec.id, 'pkg/utils.py'),
        ),
    ]

    print('Forged edges, each through the same verifier')
    print('-' * 74)
    for label, (graph, specifiers, languages) in cases:
        _, outcome = verify_dependency_edges(snap.id, graph, languages, specifiers)
        result = outcome.results[0]
        status = 'VERIFIED  ' if result.status == 'verified' else 'unverified'
        print(f'{status}  {label}')
        if result.reason:
            print(f'            {result.reason}')
    print('-' * 74)
    print()

    overlay = asyncio.run(build_dependencies(snap.id, None, None))
    assert isinstance(overlay, DependencyOverlay)
    print('Unresolved references, reported with a reason instead of drawn:')
    for item in overlay.graph.unresolved:
        print(f'  {item.source_path} -> {item.specifier!r}  ({item.reason})')
    print()
    for line in overlay.limitations:
        print(f'  limitation: {line}')


if __name__ == '__main__':
    main()
