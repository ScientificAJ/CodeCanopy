"""Vercel ASGI entrypoint for the existing GREPO backend."""
from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Archify invokes a trusted, pinned renderer. The Python runtime does not
# promise a Node executable, so the build packages its Linux Node binary.
node_binary = ROOT / ".runtime" / "node"
if node_binary.is_file():
    os.environ.setdefault("CODECANOPY_NODE", str(node_binary))
    os.environ["PATH"] = f"{node_binary.parent}{os.pathsep}{os.environ.get('PATH', '')}"

# Function source is read-only. These are instance-local working directories;
# durable storage and job ownership belong to the backend's storage layer.
cache_root = Path(tempfile.gettempdir()) / "grepo"
os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "cache"))
os.environ.setdefault("CODECANOPY_PROJECTS_DIR", str(cache_root / "projects"))
os.environ.setdefault("CODECANOPY_SNAPSHOTS_DIR", str(cache_root / "snapshots"))

from app.main import app  # noqa: E402,F401
