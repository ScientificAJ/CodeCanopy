"""Stress-test GREPO against a real repository.

Run from the backend directory with the venv python. Prints one JSON line per
stage so a long import is visible rather than silent.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

SKIP_DIRS = {'.git', 'node_modules', 'dist', '.next', 'build', 'coverage', '.turbo'}


def emit(stage, **kw):
    print(json.dumps({'stage': stage, **kw}), flush=True)


def strip(src: pathlib.Path) -> int:
    for name in SKIP_DIRS:
        for p in src.rglob(name):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
    return sum(1 for p in src.rglob('*') if p.is_file())


def main() -> None:
    src = pathlib.Path(sys.argv[1])
    n = strip(src)
    emit('stripped', files=n)

    root = pathlib.Path(tempfile.mkdtemp())
    os.environ['CODECANOPY_SNAPSHOTS_DIR'] = str(root / 'snapshots')

    from app.services.snapshot_service import create_snapshot_from_project

    t = time.time()
    snap, run = create_snapshot_from_project('a' * 32, src, 'test', 'stress')
    emit('import', seconds=round(time.time() - t, 1), snapshot_id=snap.id)

    from app.features.dependencies.service import build_dependencies

    t = time.time()
    overlay = asyncio.run(build_dependencies(snap.id, None, None))
    emit(
        'dependencies',
        seconds=round(time.time() - t, 1),
        edges=len(overlay.graph.edges),
        unresolved=len(overlay.graph.unresolved),
        impact=len(overlay.impact_subject_ids),
        limitations=overlay.limitations[:4],
    )

    from app.features.summaries.service import build_summary

    try:
        inv = __import__('app.services.snapshot_service', fromlist=['x']).get_inventory
        records = [r for r in inv(snap.id, limit=50).files if r.path.endswith(('.ts', '.tsx'))]
        target = records[0].path if records else None
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        target = None
        emit('summary', error=f'inventory: {exc}')

    if target:
        t = time.time()
        payload = asyncio.run(build_summary(snap.id, target))
        emit(
            'summary',
            seconds=round(time.time() - t, 1),
            path=target,
            evidence=len(payload.evidence),
            text_len=len(payload.text),
        )

    emit('done')


if __name__ == '__main__':
    main()
