"""Delete expired source and render data; keep brief tombstones for honest 410s."""
from datetime import datetime, timedelta, timezone
from app.services.snapshot_service import _v1_root, _read_json, remove_tree


def purge_expired():
    root = _v1_root()
    now = datetime.now(timezone.utc)
    for path in root.iterdir():
        try:
            if path.is_dir() and (path / 'snapshot.json').is_file():
                data = _read_json(path / 'snapshot.json')
                expiry = datetime.fromisoformat(data['expires_at'])
                if expiry <= now:
                    for child in path.iterdir():
                        if child.name == 'snapshot.json':
                            continue
                        if child.is_dir():
                            remove_tree(child, ignore_errors=True)
                        else:
                            child.unlink(missing_ok=True)
                if expiry + timedelta(days=1) <= now:
                    remove_tree(path, ignore_errors=True)
                    (root / f"project_{data['project_id']}.json").unlink(missing_ok=True)
            elif path.name.startswith('run_') and path.suffix == '.json':
                data = _read_json(path)
                if data.get('completed_at') and datetime.fromisoformat(data['completed_at']) + timedelta(days=2) <= now:
                    path.unlink(missing_ok=True)
        except (OSError, ValueError, KeyError):
            continue
