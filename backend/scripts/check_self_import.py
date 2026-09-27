"""Import this repository and print the terminal run status.

Proves the 'Partial import' badge no longer appears for a repository whose only
diagnostics are binary files and files above the parse budget.

Run from the backend directory with the venv python while the API is up.
"""
from __future__ import annotations

import pathlib
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPO = ROOT.parent
BASE = 'http://127.0.0.1:8000'
WS = 'a' * 64

resp = httpx.post(
    f'{BASE}/api/v1/imports/github',
    json={'url': 'https://github.com/ScientificAJ/CodeCanopy'},
    cookies={'codecanopy_workspace': WS},
    timeout=60,
)
print('POST /imports/github ->', resp.status_code, resp.text[:200])
if resp.status_code != 202:
    raise SystemExit(1)

run_id = resp.json()['run_id']
run: dict = {}
for _ in range(200):
    time.sleep(3)
    run = httpx.get(f'{BASE}/api/v1/runs/{run_id}', cookies={'codecanopy_workspace': WS}).json()
    if run.get('status') in {'completed', 'partial', 'failed', 'cancelled'}:
        break

print('status      ->', run.get('status'))
print('diagnostics ->', len(run.get('diagnostics', [])))
for d in run.get('diagnostics', [])[:4]:
    print(f"   severity={d['severity']:<8} {d['message'][:56]}")
if len(run.get('diagnostics', [])) > 4:
    print(f'   ... and {len(run["diagnostics"]) - 4} more')
print()
print('COMPLETED means the badge is gone: files were imported in full.')
