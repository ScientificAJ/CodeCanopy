"""Unauthenticated public GitHub transport with pre-request redirect enforcement."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from app.services.project_archive import _validated_entries, _extract_entries

MAX_GITHUB_ARCHIVE_BYTES = 1024 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

ALLOWED_HOSTS = {'api.github.com', 'codeload.github.com', 'github.com'}
_OWNER_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$')
_REPO_RE = re.compile(r'^[A-Za-z0-9_.-]{1,100}$')
_REF_RE = re.compile(r'^[A-Za-z0-9_./-]{1,200}$')
_COMMIT_RE = re.compile(r'^[a-f0-9]{40}$')


class GitHubImportError(ValueError):
    pass


class GitHubImportTooLargeError(GitHubImportError):
    pass


def _validate_transport_url(url: str):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise GitHubImportError('GitHub redirected outside the allowed HTTPS hosts.')


class AllowlistedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_transport_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str):
    _validate_transport_url(url)
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'GREPO-read-only/1.0'})
    try:
        return urllib.request.build_opener(AllowlistedRedirects()).open(request, timeout=20)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise GitHubImportError('Public repository or reference not found.') from None
        if error.code in {403, 429}:
            raise GitHubImportError('GitHub refused this request or its public rate limit was reached. Try later or upload a ZIP.') from None
        raise GitHubImportError('GitHub could not complete this request.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise GitHubImportError('GitHub is unavailable. Check the connection or upload a ZIP.') from None


def _safe_urlopen(url: str) -> bytes:
    with _open(url) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise GitHubImportTooLargeError('GitHub metadata exceeded the size limit.')
    return data


def parse_github_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.username or parsed.password:
        raise GitHubImportError('Credentials must not be embedded in the URL.')
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment:
        raise GitHubImportError('Use an HTTPS github.com/owner/repository URL without credentials, query or fragment.')
    parts = parsed.path.strip('/').split('/')
    if len(parts) != 2:
        raise GitHubImportError('URL must identify exactly one owner/repository.')
    owner, repo = parts
    repo = repo[:-4] if repo.endswith('.git') else repo
    if not _OWNER_RE.fullmatch(owner) or not _REPO_RE.fullmatch(repo) or repo in {'.', '..'}:
        raise GitHubImportError('Invalid repository owner or name.')
    return owner, repo


def resolve_ref_to_commit(owner: str, repo: str, ref: str = 'HEAD') -> tuple[str, str]:
    if not _REF_RE.fullmatch(ref) or '..' in ref:
        raise GitHubImportError('Invalid branch, tag or commit format.')
    base = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        metadata = json.loads(_safe_urlopen(base))
        if metadata.get('private') is not False:
            raise GitHubImportError('Only public repositories are supported.')
        display_ref = metadata['default_branch'] if ref == 'HEAD' else ref
        commit = json.loads(_safe_urlopen(f'{base}/commits/{urllib.parse.quote(display_ref, safe="")}'))['sha']
    except (ValueError, KeyError, TypeError) as error:
        if isinstance(error, GitHubImportError):
            raise
        raise GitHubImportError('GitHub returned invalid repository metadata.') from None
    if not _COMMIT_RE.fullmatch(commit):
        raise GitHubImportError('GitHub returned an invalid immutable commit.')
    return commit, display_ref


def download_archive(owner: str, repo: str, commit: str, dest_dir: Path, check_cancel=lambda: None) -> Path:
    if not _COMMIT_RE.fullmatch(commit):
        raise GitHubImportError('Invalid immutable commit.')
    archive = dest_dir / 'github.zip'
    size, started = 0, time.monotonic()
    created = False
    try:
        with _open(f'https://codeload.github.com/{owner}/{repo}/zip/{commit}') as response, archive.open('xb') as target:
            created = True
            while True:
                check_cancel()
                if time.monotonic() - started > 120:
                    raise GitHubImportError('GitHub archive download timed out.')
                # Read at most one byte beyond the cap, even without Content-Length.
                chunk = response.read(min(DOWNLOAD_CHUNK_BYTES, MAX_GITHUB_ARCHIVE_BYTES - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_GITHUB_ARCHIVE_BYTES:
                    raise GitHubImportTooLargeError(
                        f'GitHub archive exceeds the {MAX_GITHUB_ARCHIVE_BYTES // (1024 * 1024)} MiB download limit.'
                    )
                target.write(chunk)
    except Exception:
        if created:
            archive.unlink(missing_ok=True)
        raise
    return archive


def import_github_repository(url: str, ref: str = 'HEAD', check_cancel=lambda: None, on_skip=lambda path: None):
    owner, repo = parse_github_url(url)
    commit, display_ref = resolve_ref_to_commit(owner, repo, ref)
    check_cancel()
    staging = Path(tempfile.mkdtemp(prefix='codecanopy-github-'))
    extraction = staging / 'extracted'
    try:
        archive_path = download_archive(owner, repo, commit, staging, check_cancel)
        with zipfile.ZipFile(archive_path) as archive:
            entries = _validated_entries(archive, check_cancel, skip_symlinks=True, on_skip=on_skip)
            _extract_entries(archive, entries, extraction, check_cancel)
        # Strip only after safe extraction; do not modify ZipInfo header names.
        children = list(extraction.iterdir())
        files = children[0] if len(children) == 1 and children[0].is_dir() else extraction
        check_cancel()
        return owner, repo, commit, display_ref, f'{owner}/{repo}', files, staging
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
