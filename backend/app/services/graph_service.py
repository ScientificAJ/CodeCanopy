"""Real containment inventory with bounded, pageable folder projections."""
from __future__ import annotations

from app.models.v1.graph import EntityKind, Graph, GraphCoverage, GraphEntity, GraphRelation, RelationBasis, RelationKind
from app.services.inventory_service import entity_id
from app.services.snapshot_service import get_inventory, build_capability_report, get_project, get_snapshot
from app.services.v1_errors import WorkspaceError


def inventory_entities(snapshot_id: str) -> list[GraphEntity]:
    records = get_inventory(snapshot_id, limit=None).files
    snap = get_snapshot(snapshot_id)
    directories = {'.'}
    for rec in records:
        parts = rec.path.split('/')
        directories.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    entities = {}
    for path in sorted(directories):
        parent = path.rsplit('/', 1)[0] if '/' in path else '.'
        kind = 'repository' if path == '.' else 'folder'
        entities[path] = GraphEntity(id=entity_id(snapshot_id, path, kind), kind=kind,
            label=get_project(snap.project_id).name if path == '.' else path.rsplit('/', 1)[-1], path=path,
            parent_id=None if path == '.' else entity_id(snapshot_id, parent, 'repository' if parent == '.' else 'folder'))
    for rec in records:
        parent = rec.path.rsplit('/', 1)[0] if '/' in rec.path else '.'
        entities[rec.path] = GraphEntity(id=rec.id, kind=EntityKind.FILE, label=rec.name, path=rec.path,
            file_id=rec.id, parent_id=entities[parent].id,
            metadata={'language': rec.language, 'size': rec.size, 'is_text': rec.is_text, 'excluded': rec.excluded,
                      'content_hash': rec.content_hash, 'exclusion_reason': rec.exclusion_reason})
    by_id = {e.id: e for e in entities.values()}
    for entity in entities.values():
        if entity.parent_id:
            by_id[entity.parent_id].child_count += 1
    return list(entities.values())


def build_structural_graph(snapshot_id: str, max_entities: int = 12, focus: str | None = None, cursor: int = 0) -> Graph:
    entities = inventory_entities(snapshot_id)
    path = focus or '.'
    root = next((e for e in entities if e.path == path), None)
    if root is None:
        raise WorkspaceError('INVALID_FOCUS', 'The requested folder is not in this snapshot.', 404)
    if root.kind == EntityKind.FILE:
        root = next(e for e in entities if e.id == root.parent_id)
    children = sorted((e for e in entities if e.parent_id == root.id), key=lambda e: (e.kind == EntityKind.FILE, e.label.casefold(), e.id))
    limit = max(1, min(max_entities - 1, 11))
    if cursor > len(children):
        raise WorkspaceError('INVALID_CURSOR', 'Map page is out of range.', 422)
    visible = [root, *children[cursor:cursor + limit]]
    relations = [GraphRelation(id=entity_id(snapshot_id, f'{root.id}:{e.id}', 'contains'),
        source_id=root.id, target_id=e.id, kind=RelationKind.CONTAINS, basis=RelationBasis.OBSERVED) for e in visible[1:]]
    caps = build_capability_report(snapshot_id)
    coverage = GraphCoverage(inventoried_files=len(caps.files), parsed_files=caps.parsed_count,
        unresolved_references=0, excluded_paths=[f.path for f in caps.files if f.level == 'excluded'],
        limitations=['Contains means folder membership. Dependencies and calls are not assessed.'],
        truncated=len(children) > limit or cursor > 0, total_entities=len(entities), returned_entities=len(visible))
    return Graph(snapshot_id=snapshot_id, entities=visible, relations=relations, coverage=coverage,
                 focus_path=root.path, cursor=cursor, next_cursor=cursor + limit if cursor + limit < len(children) else None,
                 child_total=len(children))
