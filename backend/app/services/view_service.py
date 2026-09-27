"""Pinned Archify adapter. Fail closed on validation; never serve a stale render."""
from __future__ import annotations
import math
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from app.models.v1.graph import GraphEntity, GraphRelation, EntityKind, RelationKind, RelationBasis
from app.models.v1.view import ViewPreferences, MapRequest
from app.services.inventory_service import entity_id
from app.services.graph_service import build_structural_graph, inventory_entities
from app.services.snapshot_service import _v1_root, _read_json, _write_json, get_snapshot
from app.services.v1_errors import WorkspaceError
from app.services import cloud_storage

REPO = Path(__file__).resolve().parents[3]
ARCHIFY_COMMIT = '9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993'
_render_capacity = threading.BoundedSemaphore(2)


def get_preferences(snapshot_id: str) -> ViewPreferences:
    if cloud_storage.enabled():
        data = cloud_storage.load_view(snapshot_id)
        return ViewPreferences.model_validate(data) if data is not None else ViewPreferences()
    path = _v1_root() / snapshot_id / 'view.json'
    return ViewPreferences.model_validate(_read_json(path)) if path.exists() else ViewPreferences()


def save_preferences(snapshot_id: str, preferences: ViewPreferences) -> ViewPreferences:
    entities = inventory_entities(snapshot_id)
    ids = {entity.id for entity in entities}
    group_ids = [group.id for group in preferences.groups]
    if len(set(group_ids)) != len(group_ids):
        raise WorkspaceError('INVALID_VIEW', 'Group IDs must be unique.', 422)
    for group in preferences.groups:
        if not set(group.members) <= ids or len(set(group.members)) != len(group.members):
            raise WorkspaceError('INVALID_VIEW', 'Group members must be unique entities in this snapshot.', 422)
    if not set(preferences.labels) <= ids | set(group_ids) or any(not label.strip() or len(label) > 60 for label in preferences.labels.values()):
        raise WorkspaceError('INVALID_VIEW', 'Labels must reference this snapshot and contain 1–60 characters.', 422)
    paths = {entity.path for entity in entities}
    if preferences.focus not in paths and preferences.focus not in group_ids:
        raise WorkspaceError('INVALID_VIEW', 'Focus must reference a directory or group in this snapshot.', 422)
    if cloud_storage.enabled():
        cloud_storage.save_view(snapshot_id, preferences.model_dump())
    _write_json(_v1_root() / snapshot_id / 'view.json', preferences.model_dump())
    return preferences


def projection(snapshot_id: str, request: MapRequest, preferences: ViewPreferences):
    entities = inventory_entities(snapshot_id)
    group = next((g for g in preferences.groups if g.id == request.focus), None)
    graph = build_structural_graph(snapshot_id, max_entities=4, focus=None if group else request.focus)
    if group:
        root = GraphEntity(id=group.id, kind=EntityKind.VIRTUAL_GROUP, label=group.label, child_count=len(group.members), metadata={'view_only': True, 'group_color': group.color})
        children = [e for e in entities if e.id in group.members]
    else:
        root = graph.entities[0]
        children = [e for e in entities if e.parent_id == root.id]
    children.sort(key=lambda e: ((e.kind == EntityKind.FILE) if preferences.order == 'folders-first' else False, e.label.casefold(), e.id))
    if request.cursor > len(children):
        raise WorkspaceError('INVALID_CURSOR', 'Map cursor exceeds this view.', 422)
    visible = children[request.cursor:request.cursor + request.page_size]
    graph.entities = [root, *visible]
    graph.relations = [GraphRelation(id=entity_id(snapshot_id, f'{root.id}:{e.id}', 'groups' if group else 'contains'), source_id=root.id, target_id=e.id,
        kind=RelationKind.GROUPS if group else RelationKind.CONTAINS,
        basis=RelationBasis.OBSERVED, evidence_ids=[]) for e in visible]
    graph.focus_path = request.focus
    graph.cursor = request.cursor
    graph.child_total = len(children)
    graph.next_cursor = request.cursor + request.page_size if request.cursor + request.page_size < len(children) else None
    graph.coverage.returned_entities = len(graph.entities)
    graph.coverage.truncated = len(visible) < len(children)
    for entity in graph.entities:
        if entity.id in preferences.labels:
            entity.metadata['original_label'] = entity.label
            entity.metadata['view_only_label'] = True
            entity.label = preferences.labels[entity.id]
    return graph


def compile_spec(graph):
    """Small containment chapters; complete inventory remains in the tree.

    Up to eight siblings use a validated radial overview; smaller chapters retain the compact hierarchy.
    The middle label offset is the diagnosed repair from the pinned showcase
    validator (without it, the automatic label overlaps the parent card).
    """
    nodes = []
    children = graph.entities[1:]
    expanded = len(children) > 3
    slots = [0, 4, 2, 6, 1, 5, 3, 7]
    for index, entity in enumerate(graph.entities):
        if expanded:
            angle = slots[index - 1] * math.pi / 4 if index else 0
            x = 320 + round(290 * math.cos(angle), 2) if index else 320
            y = 170 + round(140 * math.sin(angle), 2) if index else 170
        else:
            x = 200 if index == 0 or len(children) == 1 else 20 + (index - 1) * (360 if len(children) == 2 else 180)
            y = (100 if not children else 20) if index == 0 else 160
        nodes.append({'id': 'n_' + entity.id, 'type': 'external',
            'label': entity.label if len(entity.label) <= 24 else entity.label[:21] + '…',
            'sublabel': 'View-only group' if entity.kind == EntityKind.VIRTUAL_GROUP else entity.kind.value.capitalize(),
            'pos': [x, y], 'size': [160 if expanded else 150, 60]})
    connections = []
    for i, edge in enumerate(graph.relations):
        item = {'id': 'r_' + hashlib.sha256(edge.id.encode()).hexdigest()[:32], 'from': 'n_' + edge.source_id, 'to': 'n_' + edge.target_id}
        if expanded:
            # Every arrow is parent containment/group membership, stated in the
            # view disclosure and manifest. Repeating labels obscures the radial
            # overview; the full relationship remains in the accessible list.
            if nodes[i + 1]['pos'][0] == 320 and nodes[i + 1]['pos'][1] < 170:
                item.update(fromSide='top', toSide='bottom')
        else:
            item['label'] = 'member' if edge.kind == RelationKind.GROUPS else 'contains'
            if nodes[i + 1]['pos'][0] == 200:
                item['labelDy'] = 45
        connections.append(item)
    return {'schema_version': 1, 'diagram_type': 'architecture',
        'meta': {'title': 'Repository structure', 'quality_profile': 'showcase', 'animation': 'none', 'viewBox': [800, 400] if expanded else [550, 260], 'legend': {'mode': 'hidden'}},
        'components': nodes, 'connections': connections}


def _json_safe(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def render_view(snapshot_id: str, request: MapRequest):
    snapshot = get_snapshot(snapshot_id)
    preferences = get_preferences(snapshot_id)
    graph = projection(snapshot_id, request, preferences)
    spec = compile_spec(graph)
    spec_bytes = (_json_safe(spec) + '\n').encode()
    bridge = (REPO / 'backend/app/rendering/bridge.js').read_text(encoding="utf-8")
    license_notice = (REPO / 'vendor/archify/LICENSE').read_text(encoding="utf-8")
    manifest = {'schema_version': '1.1', 'snapshot': snapshot.model_dump(mode='json'), 'graph': graph.model_dump(mode='json'),
        'renderer_ids': {'n_' + entity.id: entity.id for entity in graph.entities}, 'preferences': preferences.model_dump(), 'archify_commit': ARCHIFY_COMMIT, 'source_included': False, 'deferred_capabilities': ['AI summaries', 'proposals and generated documents'], 'export_scope': 'This structural view only; analysis results and source excerpts are not included.'}
    key = hashlib.sha256(b'codecanopy-wrapper-1.1.4' + spec_bytes + _json_safe(manifest).encode() + bridge.encode() + license_notice.encode()).hexdigest()
    manifest['view_id'] = key
    cached = _v1_root() / snapshot_id / 'renders' / key
    if (cached / 'result.json').exists():
        return _read_json(cached / 'result.json')
    if not _render_capacity.acquire(blocking=False):
        raise WorkspaceError('RENDER_BUSY', 'Two maps are rendering. Try again shortly.', 429)
    temporary = None
    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.render-', dir=cached.parent))
        candidate = temporary / 'view.architecture.json'
        output = temporary / 'archify.html'
        candidate.write_bytes(spec_bytes)
        try:
            delivered = subprocess.run([os.environ.get('CODECANOPY_NODE', 'node'), str(REPO / 'vendor/archify/bin/archify.mjs'),
                'deliver', 'architecture', str(candidate), str(output), '--quality', 'showcase', '--json'],
                capture_output=True, text=True, timeout=40, cwd=REPO, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorkspaceError('RENDER_UNAVAILABLE', 'The pinned Archify renderer could not run. Check the Node runtime.', 503) from error
        if delivered.returncode or not output.exists():
            raise WorkspaceError('RENDER_VALIDATION_FAILED', 'Archify rejected this view; no export was produced.', 422)
        receipt = json.loads(delivered.stdout)
        original_bytes = output.read_bytes()
        original = original_bytes.decode('utf-8')
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        manifest['validation'] = {
            **receipt['validation'],
            'specification_sha256': hashlib.sha256(spec_bytes).hexdigest(),
            'upstream_sha256': original_sha256,
        }
        # Never expose temporary server paths in the returned delivery receipt.
        public_receipt = {key: value for key, value in receipt.items() if key not in {'input', 'output'}}
        for field in ('specification', 'artifact'):
            if isinstance(public_receipt.get(field), dict):
                public_receipt[field] = {key: value for key, value in public_receipt[field].items() if key != 'path'}
        csp = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'\">"
        html = original.replace('<head>', '<head><!-- Archify license\n' + license_notice + '\n-->' + csp + "<script>if(window.parent!==window)document.documentElement.setAttribute('data-embed','true')</script>", 1).replace('</body>',
            '<script id="codecanopy-manifest" type="application/json">' + _json_safe(manifest) + '</script><script>' + bridge + '</script>' +
            '<style>html[data-embed="true"] .codecanopy-provenance{display:none}html[data-embed="true"] .diagram-container svg{height:calc(100vh - 20px);width:100%;min-height:0} .codecanopy-provenance{font:11px/1.45 system-ui,sans-serif;color:var(--text-muted);margin:0.25rem 0 0 1.75rem;max-width:75rem} @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}</style></body>', 1)
        result = {'schema_version': '1.1', 'view_id': key, 'graph': graph.model_dump(mode='json'),
            'html': html, 'receipt': public_receipt, 'archify_commit': ARCHIFY_COMMIT,
            'upstream_sha256': original_sha256, 'html_sha256': hashlib.sha256(html.encode()).hexdigest()}
        _write_json(temporary / 'result.json', result)
        (temporary / 'codecanopy.html').write_text(html, encoding='utf-8')
        # Bound per-snapshot artifact storage; regenerated views remain deterministic.
        with _cache_lock:
            for old in sorted((p for p in cached.parent.iterdir() if p.is_dir() and not p.name.startswith('.')), key=lambda p: p.stat().st_mtime)[:-7]:
                shutil.rmtree(old, ignore_errors=True)
            if not cached.exists():
                temporary.rename(cached)
        return result
    finally:
        if temporary and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        _render_capacity.release()


_cache_lock = threading.Lock()
