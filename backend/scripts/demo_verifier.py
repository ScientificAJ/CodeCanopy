import asyncio, tempfile, pathlib, os, sys
sys.path.insert(0, '.')

tmp = tempfile.mkdtemp()
os.environ['CODECANOPY_SNAPSHOTS_DIR'] = tmp

from app.services.snapshot_service import create_snapshot_from_project
from app.features.dependencies.service import _build_graph_raw
from app.features.dependencies.verifier import verify_dependency_edges
from app.services.inventory_service import entity_id

source = pathlib.Path(tempfile.mkdtemp())
(source / 'pkg').mkdir()
(source / 'pkg' / 'utils.py').write_text('def helper():\n    return 42\n', encoding='utf-8')
(source / 'pkg' / 'main.py').write_text(
    'from .utils import helper\n\ndef run():\n    return helper()\n',
    encoding='utf-8'
)
(source / 'pkg' / 'app.py').write_text(
    'from .main import run\nimport os\n\nrun()\n',
    encoding='utf-8'
)

snap, _ = create_snapshot_from_project('a' * 32, source, 'test', 'demo')

graph, specifier_map, lang_map = _build_graph_raw(snap.id)
print('--- RAW GRAPH ---')
print(f'Edges: {len(graph.edges)}')
for e in graph.edges:
    ev = next((x for x in graph.evidence if x.id == e.evidence_id), None)
    line = ev.range.line_start if ev else '?'
    basis = ev.basis if ev else '?'
    spec = specifier_map[e.id]
    print(f'  {e.source.path} -> {e.target.path} | specifier={spec!r} | line={line} | basis={basis}')

pruned, report = verify_dependency_edges(snap.id, graph, lang_map, specifier_map)
print()
print('--- VERIFIER OUTPUT (real imported repository) ---')
print(f'Verified: {report.verified}  Unverified: {report.unverified}')
for r in report.results:
    status_line = f'  {r.edge_id[:8]}... status={r.status}'
    if r.reason:
        status_line += f' reason={r.reason}'
    print(status_line)

print()
print('Unresolved:')
for u in graph.unresolved:
    print(f'  {u.source_path} -> {u.specifier!r} reason={u.reason}')

print()
print('--- ADVERSARIAL TEST ---')
import uuid as _uuid
from app.features.dependencies.service import (
    DependencyGraph, DependencyEdge, EdgeEndpoint, EvidenceItem, SourceRange, UnresolvedRef
)
from app.services.snapshot_service import get_inventory

records = get_inventory(snap.id, limit=100).files
rec_main = next(r for r in records if r.path == 'pkg/main.py')
rec_utils = next(r for r in records if r.path == 'pkg/utils.py')

# Forge an edge: cite line 3 of main.py ('def run():') which is NOT an import
forged_ev = EvidenceItem(
    id=_uuid.uuid4().hex,
    snapshot_id=snap.id,
    file_id=rec_main.id,
    path=rec_main.path,
    range=SourceRange(line_start=3, line_end=3),  # 'def run():' -- not an import
    content_sha256=rec_main.content_hash,
    basis='resolved',
)
forged_edge_id = _uuid.uuid4().hex
forged_graph = DependencyGraph(
    edges=[DependencyEdge(
        id=forged_edge_id,
        source=EdgeEndpoint(entity_id='src', path='pkg/main.py', file_id=rec_main.id),
        target=EdgeEndpoint(entity_id='tgt', path='pkg/utils.py', file_id=rec_utils.id),
        kind='imports',
        evidence_id=forged_ev.id,
    )],
    unresolved=[],
    evidence=[forged_ev],
)
_, adv_report = verify_dependency_edges(
    snap.id, forged_graph,
    {rec_main.id: 'python'},
    {forged_edge_id: '.utils'},
)
print(f'Forged edge citing line 3 ("def run():") for specifier=".utils":')
print(f'  status={adv_report.results[0].status}')
print(f'  reason={adv_report.results[0].reason}')
