"""
progress.py
---------------------------------
Reusable JSON-based progress tracker for long-running tasks.

Functions:
    start_progress(path, stage)
    set_progress(path, current, total, stage)
    complete_progress(path)
    fail_progress(path)
    read_progress(path)
    cleanup_progress(dir, max_files)
"""

import json, time
from pathlib import Path


def start_progress(progress_file: str, stage: str = "starting"):
    """Initialize a new progress file."""
    p = Path(progress_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"progress": 0.0, "stage": stage, "timestamp": time.time()}
    p.write_text(json.dumps(data))
    return str(p)


def set_progress(progress_file: str, current: int, total: int, stage: str = "processing"):
    """Update percentage and stage."""
    if not progress_file:
        return
    progress = round((current / max(total, 1)) * 100, 1)
    Path(progress_file).write_text(json.dumps({
        "progress": progress, "stage": stage, "timestamp": time.time()
    }))


def complete_progress(progress_file: str):
    """Mark task as finished."""
    Path(progress_file).write_text(json.dumps({
        "progress": 100.0, "stage": "done", "timestamp": time.time()
    }))


def fail_progress(progress_file: str):
    """Mark task as failed."""
    Path(progress_file).write_text(json.dumps({
        "progress": 0.0, "stage": "failed", "timestamp": time.time()
    }))


def read_progress(progress_file: str):
    """Read progress file safely."""
    try:
        p = Path(progress_file)
        if not p.exists():
            return {"progress": 0.0, "stage": "initializing"}
        return json.loads(p.read_text())
    except Exception:
        return {"progress": 0.0, "stage": "unknown"}


def cleanup_progress(directory: Path, max_files: int = 20):
    """Remove older progress JSON files."""
    files = sorted(directory.glob("progress_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in files[max_files:]:
        try:
            old.unlink()
        except Exception:
            pass
