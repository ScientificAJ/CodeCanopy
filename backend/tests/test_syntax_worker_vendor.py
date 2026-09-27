"""Exercise the actual isolated worker with only deployment-bundled dependencies."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig


def test_isolated_worker_uses_trusted_vendor_and_ignores_repository_imports(tmp_path):
    deployment = tmp_path / 'deployment'
    app_source = Path(__file__).resolve().parents[1] / 'app'
    app_copy = deployment / 'backend' / 'app'
    shutil.copytree(app_source, app_copy, ignore=shutil.ignore_patterns('__pycache__'))
    # -S removes automatic site-packages initialization. The worker must find
    # real Pydantic and native Tree-sitter through this Vercel-shaped bundle.
    (deployment / '_vendor').symlink_to(sysconfig.get_path('purelib'), target_is_directory=True)
    repository = tmp_path / 'untrusted-repository'
    repository.mkdir()
    (repository / 'json.py').write_text('raise AssertionError("Imported repository code!")\n')
    (repository / 'pydantic.py').write_text('raise AssertionError("Imported repository code!")\n')
    source_python = 'raise RuntimeError("Do not execute repository source")\ndef add(a, b):\n    return a + b\n'
    source_typescript = 'export function hello() { return 2; }'
    payloads = [
        dict(path='a.py', text=source_python, size=len(source_python), language='python'),
        dict(path='b.ts', text=source_typescript, size=len(source_typescript), language='typescript'),
    ]
    result = subprocess.run(
        [sys.executable, '-I', '-S', str(app_copy / 'services' / 'syntax_worker.py'), '--persistent'],
        input=''.join(json.dumps(payload) + '\n' for payload in payloads),
        capture_output=True, text=True, timeout=15, cwd=repository,
        env={**os.environ, 'PYTHONPATH': str(repository)},
    )
    assert result.returncode == 0, result.stderr
    python_result, typescript_result = map(json.loads, result.stdout.splitlines())
    assert python_result['parser'] == 'python-ast'
    assert python_result['functions'][0]['name'] == 'add'
    assert typescript_result['parser'] == 'tree-sitter'
    assert typescript_result['functions'][0]['name'] == 'hello'
