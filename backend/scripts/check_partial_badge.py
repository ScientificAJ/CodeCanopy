"""Manual end-to-end check: does a binary file still say PARTIAL?

Imports a zip containing one Python file and two real PNGs through the actual
HTTP import route, then prints the terminal run status and every diagnostic.
Run from the backend directory with the venv python.
"""
import io
import os
import pathlib
import secrets
import struct
import sys
import tempfile
import time
import zipfile
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

root = pathlib.Path(tempfile.mkdtemp())
os.environ['CODECANOPY_SNAPSHOTS_DIR'] = str(root / 'snapshots')


def png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00'))
        + chunk(b'IEND', b'')
    )


buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('pkg/a.py', 'def f():\n    return 1\n')
    z.writestr('pkg/shot.png', png())
    z.writestr('pkg/two.png', png())

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.cookies.set('codecanopy_workspace', secrets.token_hex(32))

resp = client.post(
    '/api/v1/imports/zip',
    files={'file': ('repo.zip', buf.getvalue(), 'application/zip')},
)
print('POST /api/v1/imports/zip ->', resp.status_code)
run_id = resp.json()['run_id']

run = {}
for _ in range(80):
    time.sleep(0.4)
    run = client.get(f'/api/v1/runs/{run_id}').json()
    if run.get('status') in {'completed', 'partial', 'failed', 'cancelled'}:
        break

print('status      ->', run.get('status'))
print('diagnostics ->', len(run.get('diagnostics', [])))
for d in run.get('diagnostics', []):
    print(f"   severity={d.get('severity'):<8} {d.get('message', '')[:52]}")

print()
print('expected: completed, because 2 PNGs cost syntax, not content')
