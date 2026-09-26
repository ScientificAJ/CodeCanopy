"""Ask CodeCanopy – Groq-backed codebase chat endpoint."""
from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field

from app.api.v1.session import workspace_session
from app.api.v1.snapshots import snapshot_access
from app.models.v1.snapshot import Snapshot
from app.services.snapshot_service import get_inventory, read_source_lines
from app.services.v1_errors import WorkspaceError

router = APIRouter(prefix="/projects", tags=["v1-ask"])

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

# Token budget (8 000 TPM free tier):
#   system prompt  ~200 tokens
#   file tree      ~300 tokens  (all paths, no content)
#   source snippet ~800 tokens  (selected file or top files)
#   history        ~200 tokens
#   question       ~100 tokens
#   ─────────────────────────
#   total input    ~1 600 tokens  →  leaves 6 400 for output
MAX_TREE_CHARS   = 3_000   # full path list – cheap, ~750 tokens
MAX_SOURCE_CHARS = 3_000   # source snippets on top of the tree
MAX_SNIPPET_LINES_FILE = 60   # lines read when a single file is focused
MAX_SNIPPET_LINES_REPO = 15   # lines read per file in repo-wide mode
MAX_FILES_SNIPPET = 10        # files to sample for repo-wide snippets
MAX_OUTPUT_TOKENS = 1_200

CODE_EXTENSIONS = {
    '.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs',
    '.java', '.cs', '.rb', '.php', '.cpp', '.c', '.kt',
    '.html', '.css', '.json', '.yaml', '.yml', '.toml', '.md'
}


class ChatMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)
    file_id: str | None = None      # focused file (optional)
    folder_path: str | None = None  # focused folder path (optional)
    scope: str = "repository"       # "repository" | "file" | "folder"


class AskResponse(BaseModel):
    answer: str
    context_hint: str


def _api_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise WorkspaceError("AI_NOT_CONFIGURED", "GROQ_API_KEY is not set on the server.", 503)
    return key


def _build_file_tree(snap: Snapshot) -> str:
    """Return a compact directory tree of ALL files in the snapshot.

    Format mirrors `tree` output so the model understands folder structure:
        backend/
          app/
            main.py
            api/
              router.py
    Capped at MAX_TREE_CHARS so it never blows the token budget.
    """
    try:
        inventory = get_inventory(snap.id, limit=5000)
    except WorkspaceError:
        return ""

    all_paths = sorted(f.path for f in inventory.files)

    # Build indented tree lines
    lines: list[str] = []
    seen_dirs: set[str] = set()
    for path in all_paths:
        parts = path.split("/")
        # emit any unseen parent directories
        for depth in range(1, len(parts)):
            dir_path = "/".join(parts[:depth])
            if dir_path not in seen_dirs:
                seen_dirs.add(dir_path)
                indent = "  " * (depth - 1)
                lines.append(f"{indent}{parts[depth - 1]}/")
        # emit the file
        indent = "  " * (len(parts) - 1)
        lines.append(f"{indent}{parts[-1]}")

    tree_text = "\n".join(lines)
    return tree_text[:MAX_TREE_CHARS]


def _question_keywords(question: str) -> list[str]:
    """Extract meaningful lowercase tokens from the question to match file paths."""
    import re
    STOP = {
        'the', 'is', 'are', 'was', 'a', 'an', 'of', 'in', 'to', 'for', 'and',
        'or', 'not', 'it', 'this', 'that', 'what', 'why', 'how', 'where',
        'which', 'with', 'by', 'be', 'do', 'does', 'can', 'has', 'have',
        'i', 'my', 'me', 'its', 'at', 'on', 'from', 'file', 'folder', 'show',
        'tell', 'give', 'explain', 'about', 'here', 'there', 'used', 'use',
    }
    tokens = re.split(r'[\s/\\.,:;\'\"()\[\]{}]+', question.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOP]


def _score_file(path: str, keywords: list[str]) -> int:
    """Score a file path by how many question keywords appear in it."""
    p = path.lower()
    return sum(1 for kw in keywords if kw in p)


def _build_source_snippets(
    snap: Snapshot,
    file_id: str | None,
    scope: str,
    question: str = "",
    folder_path: str | None = None,
) -> tuple[str, str]:
    """Read source only for files relevant to the question. Capped at MAX_SOURCE_CHARS."""

    # ── Single file scope ──────────────────────────────────────────────────
    if scope == "file" and file_id:
        try:
            sl = read_source_lines(snap.id, file_id, 1, None, MAX_SNIPPET_LINES_FILE)
            text = sl.content[:MAX_SOURCE_CHARS]
            hint = f"Focused on {sl.path} ({sl.total_lines} lines total)"
            return text, hint
        except WorkspaceError:
            return "", "Source unavailable for that file."

    try:
        inventory = get_inventory(snap.id, limit=5000)
    except WorkspaceError:
        return "", "Repository inventory unavailable."

    text_files = [f for f in inventory.files if f.is_text and not f.excluded]

    # ── Folder scope — restrict to files under the selected folder ─────────
    if scope == "folder" and folder_path and folder_path not in (".", ""):
        prefix = folder_path.rstrip("/") + "/"
        folder_files = [f for f in text_files if f.path.startswith(prefix)]
        # fall back to full repo if the folder has no text files
        if folder_files:
            text_files = folder_files

    keywords = _question_keywords(question)

    # Sort by: keyword match score (desc) then code file preference (desc)
    def sort_key(f):
        return (_score_file(f.path, keywords), int(any(f.path.endswith(e) for e in CODE_EXTENSIONS)))

    ranked = sorted(text_files, key=sort_key, reverse=True)[:MAX_FILES_SNIPPET]

    parts: list[str] = []
    total = 0
    sampled: list[str] = []
    for rec in ranked:
        if total >= MAX_SOURCE_CHARS:
            break
        try:
            sl = read_source_lines(snap.id, rec.id, 1, None, MAX_SNIPPET_LINES_REPO)
            budget = MAX_SOURCE_CHARS - total
            chunk = f"### {rec.path}\n{sl.content[:budget]}\n"
            parts.append(chunk)
            total += len(chunk)
            sampled.append(rec.path)
        except WorkspaceError:
            continue

    hint = (
        f"Based on {len(sampled)} relevant files: {', '.join(sampled[:5])}"
        + (" …" if len(sampled) > 5 else "")
    )
    return "\n".join(parts), hint


@router.post("/{project_id}/snapshots/{snapshot_id}/chat", response_model=AskResponse)
def ask_chat(
    project_id: str,
    snapshot_id: str,
    body: Annotated[AskRequest, Body()],
    snap: Snapshot = Depends(snapshot_access),
    _workspace: str = Depends(workspace_session),
) -> AskResponse:
    # Always build the full file tree — cheap tokens, complete structural awareness
    file_tree = _build_file_tree(snap)

    # Source snippets — only read files relevant to this specific question
    source_snippets, hint = _build_source_snippets(
        snap, body.file_id, body.scope, body.question, body.folder_path
    )

    # Compose system prompt
    system_parts = [
        "You are CodeCanopy's AI assistant. You help developers understand large codebases.",
        "You have full structural knowledge of this repository via the file tree below.",
        "Answer questions about code structure, imports, API design, technologies, logic, and any file or folder.",
        "Always reference exact file paths from the tree when answering.",
        "If source content is not in the snippets, say so — but still use the file tree to give accurate structural answers.",
    ]
    if file_tree:
        system_parts.append(
            f"\n<repository_file_tree>\n{file_tree}\n</repository_file_tree>"
        )
    if source_snippets:
        system_parts.append(
            f"\n<source_snippets>\n{source_snippets}\n</source_snippets>"
        )

    system_prompt = "\n".join(system_parts)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in body.history[-4:]:   # last 4 turns to save tokens
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.question})

    try:
        resp = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        answer: str = data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("error", {}).get("message", e.response.text[:300])
        except Exception:
            detail = e.response.text[:300]
        raise WorkspaceError("AI_ERROR", f"Groq {e.response.status_code}: {detail}", 502) from e
    except (httpx.TimeoutException, httpx.RequestError) as e:
        raise WorkspaceError("AI_TIMEOUT", "The AI provider did not respond in time.", 504) from e
    except (KeyError, ValueError) as e:
        raise WorkspaceError("AI_PARSE", "Unexpected response format from the AI provider.", 502) from e

    return AskResponse(answer=answer, context_hint=hint)
