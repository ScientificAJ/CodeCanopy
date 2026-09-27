from __future__ import annotations

import asyncio
import uuid as _uuid

import pytest

from app.features.dependencies.service import (
    DependencyGraph,
    DependencyOverlay,
    EvidenceItem,
    SourceRange,
    DependencyEdge,
    EdgeEndpoint,
    IMPACT_WALK_CAP,
    _build_graph_raw,
    _resolve_js_specifier,
    _resolve_python_specifier,
    build_dependencies,
    compute_impact,
)
from app.features.dependencies.verifier import (
    verify_dependency_edges,
)
from app.services.snapshot_service import create_snapshot_from_project, get_inventory
from app.services.inventory_service import entity_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_snapshot(tmp_path, monkeypatch, files: dict[str, str]):
    monkeypatch.setenv('CODECANOPY_SNAPSHOTS_DIR', str(tmp_path / 'snapshots'))
    source = tmp_path / 'source'
    source.mkdir(exist_ok=True)
    for name, text in files.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    snap, _ = create_snapshot_from_project('a' * 32, source, 'test', 'test-project')
    return snap


def get_record(snap_id, path):
    records = get_inventory(snap_id, limit=10000).files
    return next(r for r in records if r.path == path)


# ---------------------------------------------------------------------------
# Resolution unit tests (no snapshot needed)
# ---------------------------------------------------------------------------

def test_relative_python_import_resolves():
    path_set = {'pkg/utils.py', 'pkg/main.py'}
    result = _resolve_python_specifier('.utils', 'pkg/main.py', path_set)
    assert result == 'pkg/utils.py'


def test_relative_python_import_resolves_with_suffix():
    """An import specifier without extension resolves when the .py file exists."""
    path_set = {'utils.py'}
    result = _resolve_python_specifier('.utils', 'main.py', path_set)
    assert result == 'utils.py'


def test_absolute_python_import_resolves_in_snapshot():
    path_set = {'mylib/helper.py'}
    result = _resolve_python_specifier('mylib.helper', 'main.py', path_set)
    assert result == 'mylib/helper.py'


def test_bare_python_package_not_in_snapshot_returns_none():
    path_set = {'myfile.py'}
    result = _resolve_python_specifier('os', 'myfile.py', path_set)
    assert result is None


def test_js_relative_import_resolves():
    path_set = {'src/utils.js', 'src/main.js'}
    result = _resolve_js_specifier('./utils', 'src/main.js', path_set)
    assert result == 'src/utils.js'


def test_js_relative_import_resolves_with_ts_suffix():
    path_set = {'src/utils.ts', 'src/main.ts'}
    result = _resolve_js_specifier('./utils', 'src/main.ts', path_set)
    assert result == 'src/utils.ts'


def test_js_bare_package_returns_none():
    path_set = {'src/main.js'}
    result = _resolve_js_specifier('react', 'src/main.js', path_set)
    assert result is None


# ---------------------------------------------------------------------------
# Graph builder integration tests
# ---------------------------------------------------------------------------

def test_relative_import_produces_resolved_edge(tmp_path, monkeypatch):
    """A relative import that resolves to an in-snapshot file creates an edge."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'pkg/utils.py': 'def helper(): pass\n',
        'pkg/main.py': 'from .utils import helper\n',
    })
    graph, specifier_map, _ = _build_graph_raw(snap.id)
    edges = [e for e in graph.edges if 'main.py' in e.source.path and 'utils.py' in e.target.path]
    assert edges, f'Expected edge main→utils, got edges: {[(e.source.path, e.target.path) for e in graph.edges]}'
    edge = edges[0]
    assert edge.kind == 'imports'
    assert edge.evidence_id is not None
    assert specifier_map.get(edge.id) is not None


def test_import_with_different_suffix_resolves(tmp_path, monkeypatch):
    """A JS import without extension resolves when the .ts file exists."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'src/utils.ts': 'export function foo() {}\n',
        'src/main.ts': "import { foo } from './utils'\n",
    })
    graph, _, _ = _build_graph_raw(snap.id)
    edges = [e for e in graph.edges if 'utils' in e.target.path]
    assert edges, f'Expected edge to utils.ts, got: {[(e.source.path, e.target.path) for e in graph.edges]}'


def test_bare_package_import_is_unresolved(tmp_path, monkeypatch):
    """A bare package name (e.g. 'os', 'react') creates no edge and is unresolved."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'main.py': 'import os\nimport pathlib\n',
    })
    graph, _, _ = _build_graph_raw(snap.id)
    assert not graph.edges, f'Expected no edges, got: {graph.edges}'
    assert any(u.reason == 'bare_package' for u in graph.unresolved)


def test_nonexistent_path_is_unresolved(tmp_path, monkeypatch):
    """An import that looks relative but points to a nonexistent path is unresolved."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'main.py': 'from .nonexistent import foo\n',
    })
    graph, _, _ = _build_graph_raw(snap.id)
    assert not graph.edges
    not_found = [u for u in graph.unresolved if u.reason == 'not_found']
    assert not_found


def test_call_edges_not_fabricated(tmp_path, monkeypatch):
    """The builder only emits import edges; no fabricated call edges appear."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'a.py': 'def foo(): pass\n',
        'b.py': 'from . import a\na.foo()\n',
    })
    graph, _, _ = _build_graph_raw(snap.id)
    call_edges = [e for e in graph.edges if e.kind == 'calls']
    assert not call_edges, 'No call edges should be fabricated'


# ---------------------------------------------------------------------------
# Change impact tests
# ---------------------------------------------------------------------------

def test_impact_returns_importing_files(tmp_path, monkeypatch):
    """Files that import the subject appear in impact_subject_ids."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    graph, _, _ = _build_graph_raw(snap.id)
    affected, truncated = compute_impact(snap.id, graph, 'utils.py')
    utils_eid = entity_id(snap.id, 'utils.py', 'file')
    main_eid = entity_id(snap.id, 'main.py', 'file')
    assert main_eid in affected
    assert utils_eid not in affected
    assert not truncated


def test_impact_truncation_is_reported(tmp_path, monkeypatch, monkeypatch_walk_cap):
    """When the walk hits the cap, truncated=True is returned."""
    # monkeypatch_walk_cap is defined below
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'x=1\n',
        'main.py': 'from .utils import x\n',
        'other.py': 'from .utils import x\n',
    })
    graph, _, _ = _build_graph_raw(snap.id)
    affected, truncated = compute_impact(snap.id, graph, 'utils.py')
    # With cap=1, second importer should cause truncation
    assert truncated


@pytest.fixture
def monkeypatch_walk_cap(monkeypatch):
    import app.features.dependencies.service as svc
    monkeypatch.setattr(svc, 'IMPACT_WALK_CAP', 1)


# ---------------------------------------------------------------------------
# Full build_dependencies async tests
# ---------------------------------------------------------------------------

def test_build_dependencies_returns_overlay(tmp_path, monkeypatch):
    snap = make_snapshot(tmp_path, monkeypatch, {
        'pkg/utils.py': 'def helper(): pass\n',
        'pkg/main.py': 'from .utils import helper\n',
    })
    overlay = asyncio.run(build_dependencies(snap.id, None, None))
    assert isinstance(overlay, DependencyOverlay)
    assert overlay.schema_version == '1.1'
    assert overlay.snapshot_id == snap.id


def test_no_subject_returns_empty_impact_with_limitation(tmp_path, monkeypatch):
    """path=None returns an empty impact list and a limitation disclosing why."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    overlay = asyncio.run(build_dependencies(snap.id, None, None))
    assert overlay.impact_subject_ids == []
    assert any('select' in lim.lower() for lim in overlay.limitations), overlay.limitations


def test_dot_subject_returns_empty_impact_with_limitation(tmp_path, monkeypatch):
    """path='.' behaves identically to path=None."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    overlay = asyncio.run(build_dependencies(snap.id, '.', None))
    assert overlay.impact_subject_ids == []
    assert any('select' in lim.lower() for lim in overlay.limitations), overlay.limitations


def test_folder_subject_returns_only_external_importers(tmp_path, monkeypatch):
    """path='pkg' returns files outside pkg that import something inside pkg."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'pkg/utils.py': 'def helper(): pass\n',
        'pkg/main.py': 'from .utils import helper\n',
        'main.py': 'from .pkg.utils import helper\n',
        'other.py': 'x = 1\n',
    })
    overlay = asyncio.run(build_dependencies(snap.id, 'pkg', None))
    main_eid = entity_id(snap.id, 'main.py', 'file')
    other_eid = entity_id(snap.id, 'other.py', 'file')
    pkg_utils_eid = entity_id(snap.id, 'pkg/utils.py', 'file')
    pkg_main_eid = entity_id(snap.id, 'pkg/main.py', 'file')
    # Files inside pkg must not appear
    assert pkg_utils_eid not in overlay.impact_subject_ids
    assert pkg_main_eid not in overlay.impact_subject_ids
    # other.py has no imports so it must not appear
    assert other_eid not in overlay.impact_subject_ids
    # main.py imports pkg.utils so it must appear
    assert main_eid in overlay.impact_subject_ids


def test_full_repo_subject_returns_empty_with_limitation(tmp_path, monkeypatch):
    """When the subject covers every file in the snapshot, impact is empty + limitation."""
    # A snapshot where a single folder 'root' contains every file.
    snap = make_snapshot(tmp_path, monkeypatch, {
        'root/a.py': 'x = 1\n',
        'root/b.py': 'y = 2\n',
    })
    overlay = asyncio.run(build_dependencies(snap.id, 'root', None))
    # 'root' covers every file in the snapshot so impact is meaningless
    assert overlay.impact_subject_ids == []
    assert any('select' in lim.lower() for lim in overlay.limitations), overlay.limitations


def test_build_dependencies_404_for_unknown_path(tmp_path, monkeypatch):
    from app.services.v1_errors import WorkspaceError
    snap = make_snapshot(tmp_path, monkeypatch, {'a.py': 'x=1\n'})
    with pytest.raises(WorkspaceError) as exc_info:
        asyncio.run(build_dependencies(snap.id, 'nonexistent/path.py', None))
    assert exc_info.value.status == 404


# ---------------------------------------------------------------------------
# Verifier tests
# ---------------------------------------------------------------------------

def test_verifier_passes_correct_edge(tmp_path, monkeypatch):
    """A correctly built edge is verified."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    graph, specifier_map, lang_map = _build_graph_raw(snap.id)
    pruned, report = verify_dependency_edges(snap.id, graph, lang_map, specifier_map)
    assert report.unverified == 0, [r for r in report.results if r.status == 'unverified']
    assert report.verified == len(graph.edges)


def test_citation_past_end_of_file_is_unverified(tmp_path, monkeypatch):
    """An evidence item whose line_end exceeds file length is unverified."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'x = 1\n',
        'main.py': 'from .utils import x\n',
    })
    rec_main = get_record(snap.id, 'main.py')
    rec_utils = get_record(snap.id, 'utils.py')
    source_eid = entity_id(snap.id, 'main.py', 'file')
    target_eid = entity_id(snap.id, 'utils.py', 'file')

    bad_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec_main.id,
        path=rec_main.path,
        range=SourceRange(line_start=1, line_end=999),  # past end
        content_sha256=rec_main.content_hash,
        basis='resolved',
    )
    edge_id = _uuid.uuid4().hex
    bad_graph = DependencyGraph(
        edges=[DependencyEdge(
            id=edge_id,
            source=EdgeEndpoint(entity_id=source_eid, path='main.py', file_id=rec_main.id),
            target=EdgeEndpoint(entity_id=target_eid, path='utils.py', file_id=rec_utils.id),
            kind='imports',
            evidence_id=bad_ev.id,
        )],
        unresolved=[],
        evidence=[bad_ev],
    )
    _, report = verify_dependency_edges(
        snap.id, bad_graph,
        {rec_main.id: 'python'},
        {edge_id: '.utils'},
    )
    assert report.unverified == 1
    assert 'exceed' in report.results[0].reason.lower() or 'line_end' in report.results[0].reason.lower()


def test_file_id_from_another_snapshot_is_rejected(tmp_path, monkeypatch):
    """A file_id from a different snapshot is rejected by the verifier."""
    snap1 = make_snapshot(tmp_path, monkeypatch, {'a.py': 'x = 1\n'})
    source2 = tmp_path / 'src2'
    source2.mkdir()
    (source2 / 'b.py').write_text('y = 2\n', encoding='utf-8')
    snap2, _ = create_snapshot_from_project('b' * 32, source2, 'test2', 'proj2')

    snap2_rec = get_record(snap2.id, 'b.py')
    snap1_rec = get_record(snap1.id, 'a.py')

    ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap1.id,
        file_id=snap2_rec.id,  # wrong snapshot
        path='b.py',
        range=SourceRange(line_start=1, line_end=1),
        content_sha256=snap2_rec.content_hash,
        basis='resolved',
    )
    edge_id = _uuid.uuid4().hex
    bad_graph = DependencyGraph(
        edges=[DependencyEdge(
            id=edge_id,
            source=EdgeEndpoint(entity_id='src', path='a.py', file_id=snap1_rec.id),
            target=EdgeEndpoint(entity_id='tgt', path='b.py', file_id=snap2_rec.id),
            kind='imports',
            evidence_id=ev.id,
        )],
        unresolved=[],
        evidence=[ev],
    )
    _, report = verify_dependency_edges(
        snap1.id, bad_graph,
        {snap2_rec.id: 'python'},
        {edge_id: '.b'},
    )
    assert report.unverified == 1
    assert 'not found' in report.results[0].reason.lower()


def test_real_line_not_importing_target_is_unverified(tmp_path, monkeypatch):
    """The adversarial test: a hand-forged edge whose cited line exists but
    does NOT import the claimed target comes back unverified (Guard 5)."""
    # line 1 of main.py is 'x = 1' — not an import of utils
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'x = 1\nfrom .utils import helper\n',
    })
    rec_main = get_record(snap.id, 'main.py')
    rec_utils = get_record(snap.id, 'utils.py')
    source_eid = entity_id(snap.id, 'main.py', 'file')
    target_eid = entity_id(snap.id, 'utils.py', 'file')

    # Forge evidence pointing at line 1 ('x = 1'), which is NOT an import
    forged_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec_main.id,
        path=rec_main.path,
        range=SourceRange(line_start=1, line_end=1),  # real line, but not an import
        content_sha256=rec_main.content_hash,
        basis='resolved',
    )
    edge_id = _uuid.uuid4().hex
    forged_graph = DependencyGraph(
        edges=[DependencyEdge(
            id=edge_id,
            source=EdgeEndpoint(entity_id=source_eid, path='main.py', file_id=rec_main.id),
            target=EdgeEndpoint(entity_id=target_eid, path='utils.py', file_id=rec_utils.id),
            kind='imports',
            evidence_id=forged_ev.id,
        )],
        unresolved=[],
        evidence=[forged_ev],
    )
    _, report = verify_dependency_edges(
        snap.id, forged_graph,
        {rec_main.id: 'python'},
        {edge_id: '.utils'},  # specifier being 'verified'
    )
    assert report.unverified == 1
    result = report.results[0]
    assert result.status == 'unverified'
    assert 'import' in result.reason.lower() or 'does not contain' in result.reason.lower()


def test_forged_target_file_id_is_unverified(tmp_path, monkeypatch):
    """Guard 0: a valid citation but a target file_id that does not exist in
    this snapshot is rejected, and the reason names the target."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    rec_main = get_record(snap.id, 'main.py')
    source_eid = entity_id(snap.id, 'main.py', 'file')

    # Legitimate evidence (real file, real line, correct hash, import statement)
    good_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec_main.id,
        path=rec_main.path,
        range=SourceRange(line_start=1, line_end=1),
        content_sha256=rec_main.content_hash,
        basis='resolved',
    )
    fictional_target_file_id = _uuid.uuid4().hex  # does not exist
    edge_id = _uuid.uuid4().hex
    forged_graph = DependencyGraph(
        edges=[DependencyEdge(
            id=edge_id,
            source=EdgeEndpoint(entity_id=source_eid, path='main.py', file_id=rec_main.id),
            target=EdgeEndpoint(
                entity_id='fictional',
                path='fictional/target.py',
                file_id=fictional_target_file_id,
            ),
            kind='imports',
            evidence_id=good_ev.id,
        )],
        unresolved=[],
        evidence=[good_ev],
    )
    _, report = verify_dependency_edges(
        snap.id, forged_graph,
        {rec_main.id: 'python'},
        {edge_id: '.utils'},
    )
    assert report.unverified == 1
    result = report.results[0]
    assert result.status == 'unverified'
    # Reason must identify the fictional target
    assert fictional_target_file_id in result.reason or 'fictional/target.py' in result.reason


def test_target_with_null_file_id_is_unverified(tmp_path, monkeypatch):
    """Guard 0: an edge whose target.file_id is None is unverified."""
    snap = make_snapshot(tmp_path, monkeypatch, {
        'utils.py': 'def helper(): pass\n',
        'main.py': 'from .utils import helper\n',
    })
    rec_main = get_record(snap.id, 'main.py')
    source_eid = entity_id(snap.id, 'main.py', 'file')

    good_ev = EvidenceItem(
        id=_uuid.uuid4().hex,
        snapshot_id=snap.id,
        file_id=rec_main.id,
        path=rec_main.path,
        range=SourceRange(line_start=1, line_end=1),
        content_sha256=rec_main.content_hash,
        basis='resolved',
    )
    edge_id = _uuid.uuid4().hex
    null_target_graph = DependencyGraph(
        edges=[DependencyEdge(
            id=edge_id,
            source=EdgeEndpoint(entity_id=source_eid, path='main.py', file_id=rec_main.id),
            target=EdgeEndpoint(entity_id='ext', path='external.py', file_id=None),
            kind='imports',
            evidence_id=good_ev.id,
        )],
        unresolved=[],
        evidence=[good_ev],
    )
    _, report = verify_dependency_edges(
        snap.id, null_target_graph,
        {rec_main.id: 'python'},
        {edge_id: '.utils'},
    )
    assert report.unverified == 1
    assert report.results[0].status == 'unverified'
