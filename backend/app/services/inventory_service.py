"""Inventory and existing Python syntax extraction. Never executes source."""
from __future__ import annotations

import hashlib
from collections import deque
import io
import subprocess
import os
import tokenize
from pathlib import Path

from app.analyzers.tree_sitter_analyzer import parser_language
from app.models.v1.snapshot import FileRecord, RunDiagnostic
from app.services.project_archive import IGNORED_DIRECTORIES
from app.services.syntax_process import SyntaxPool

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


def build_inventory(snapshot_id: str, source: Path, destination: Path, check_cancel=lambda: None, report_progress=lambda done, total: None):
    records: list[FileRecord] = []
    diagnostics: list[RunDiagnostic] = []
    parsed: dict[str, dict] = {}
    files = []
    for current, dirs, names in os.walk(source, followlinks=False):
        check_cancel()
        directory = Path(current)
        dirs[:] = sorted(d for d in dirs if d.casefold() not in IGNORED_DIRECTORIES and not (directory / d).is_symlink())
        for name in sorted(names):
            file = directory / name
            if not file.is_symlink() and file.is_file():
                files.append(file)
    report_progress(0, len(files))
    pending = deque()

    def collect():
        record, future = pending.popleft()
        try:
            parsed[record.id] = future.result()
        except (ValueError, OSError, subprocess.SubprocessError):
            diagnostics.append(RunDiagnostic(file_path=record.path, stage='parse', message='Syntax extraction failed or exceeded its resource budget; original text remains browsable.'))

    with SyntaxPool() as parser:
        for index, file in enumerate(files):
            check_cancel()
            name = file.name
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
                report_progress(index + 1 - len(pending), len(files))
                continue
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o444)
            if text is None:
                diagnostics.append(RunDiagnostic(file_path=path, stage='inventory', message='Binary or unsupported text encoding; metadata only.'))
            elif language == 'python' or parser_language(language, path) is not None:
                if len(data) > MAX_PARSE_BYTES:
                    diagnostics.append(RunDiagnostic(file_path=path, stage='parse', message='Syntax extraction skipped above 1 MiB; source remains browsable.'))
                else:
                    pending.append((record, parser.submit({'text': text, 'path': path, 'size': len(data), 'language': language}, check_cancel)))
                    if len(pending) >= 4:
                        collect()
            report_progress(index + 1 - len(pending), len(files))
        while pending:
            check_cancel()
            collect()
            report_progress(len(files) - len(pending), len(files))
    return sorted(records, key=lambda r: r.path), parsed, diagnostics

