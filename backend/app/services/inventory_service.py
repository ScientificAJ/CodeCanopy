"""Inventory and existing Python syntax extraction. Never executes source."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import os
import tokenize
from pathlib import Path

from app.models.v1.snapshot import FileRecord, RunDiagnostic
from app.services.project_archive import IGNORED_DIRECTORIES

LANGUAGES = {
    '.py': 'python', '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
    '.cjs': 'javascript', '.ts': 'typescript', '.tsx': 'typescript', '.go': 'go',
    '.rs': 'rust', '.java': 'java', '.kt': 'kotlin', '.swift': 'swift', '.c': 'c',
    '.h': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.cs': 'csharp', '.rb': 'ruby',
    '.php': 'php', '.sh': 'shell', '.bash': 'shell', '.sql': 'sql', '.html': 'html',
    '.htm': 'html', '.css': 'css', '.scss': 'css', '.json': 'json', '.yaml': 'yaml',
    '.yml': 'yaml', '.toml': 'toml', '.md': 'markdown', '.txt': 'text',
    '.xml': 'xml', '.svg': 'xml', '.tf': 'terraform', 'dockerfile': 'dockerfile',
}
MAX_PARSE_BYTES = 1024 * 1024


def entity_id(snapshot_id: str, path: str, kind: str = 'file') -> str:
    return hashlib.sha256(f'1.0:{snapshot_id}:{kind}:{path}'.encode()).hexdigest()[:32]


def decode_text(data: bytes, language: str) -> tuple[str | None, str | None]:
    if b'\x00' in data:
        return None, None
    try:
        encoding = tokenize.detect_encoding(io.BytesIO(data).readline)[0] if language == 'python' else 'utf-8'
        return data.decode(encoding), encoding
    except (UnicodeError, SyntaxError, LookupError):
        return None, None


def exclusion_reason(path: Path, data: bytes) -> str | None:
    name = path.name.lower()
    if name == '.env' or (name.startswith('.env.') and name not in {'.env.example', '.env.sample', '.env.template'}):
        return 'Environment secrets are excluded by source policy.'
    if name.endswith(('.pem', '.key', '.p12', '.pfx', '.keystore')) or name in {'id_rsa', 'id_ed25519', '.npmrc', '.pypirc', 'credentials'}:
        return 'Credential/key files are excluded by source policy.'
    if any(marker in data for marker in (b'-----BEGIN PRIVATE KEY', b'-----BEGIN RSA PRIVATE KEY', b'-----BEGIN OPENSSH PRIVATE KEY', b'-----BEGIN EC PRIVATE KEY')):
        return 'Private-key material is excluded by source policy.'
    return None


def build_inventory(snapshot_id: str, source: Path, destination: Path, check_cancel=lambda: None):
    records: list[FileRecord] = []
    diagnostics: list[RunDiagnostic] = []
    parsed: dict[str, dict] = {}
    for current, dirs, names in os.walk(source, followlinks=False):
        check_cancel()
        directory = Path(current)
        dirs[:] = sorted(d for d in dirs if d.casefold() not in IGNORED_DIRECTORIES and not (directory / d).is_symlink())
        for name in sorted(names):
            check_cancel()
            file = directory / name
            if file.is_symlink() or not file.is_file():
                continue
            path = file.relative_to(source).as_posix()
            data = file.read_bytes()
            language = LANGUAGES.get(file.suffix.lower(), LANGUAGES.get(name.lower(), 'unknown'))
            text, encoding = decode_text(data, language)
            reason = exclusion_reason(file, data)
            record = FileRecord(
                id=entity_id(snapshot_id, path), snapshot_id=snapshot_id, path=path, name=name,
                size=len(data), content_hash=hashlib.sha256(data).hexdigest(), is_text=text is not None,
                encoding=encoding, language=language, excluded=reason is not None, exclusion_reason=reason,
            )
            records.append(record)
            if reason:
                continue
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o444)
            if text is None:
                diagnostics.append(RunDiagnostic(file_path=path, stage='inventory', message='Binary or unsupported text encoding; metadata only.'))
            elif language == 'python':
                if len(data) > MAX_PARSE_BYTES:
                    diagnostics.append(RunDiagnostic(file_path=path, stage='parse', message='Python syntax extraction skipped above 1 MiB; source remains browsable.'))
                else:
                    try:
                        result = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('syntax_worker.py'))], input=json.dumps({'text': text, 'path': path, 'size': len(data)}), capture_output=True, text=True, timeout=4, check=True)
                        parsed[record.id] = json.loads(result.stdout)
                    except (ValueError, OSError, subprocess.SubprocessError):
                        diagnostics.append(RunDiagnostic(file_path=path, stage='parse', message='Python syntax extraction failed or exceeded its resource budget; original text remains browsable.'))
    return sorted(records, key=lambda r: r.path), parsed, diagnostics

