from pathlib import Path
from fastapi import APIRouter

MAX_FILES_PER_FOLDER = 20
router = APIRouter(prefix="/api/clean", tags=["Clean API"])

def cleanup_old_files(folder: Path, max_files: int = 20):
    files = sorted(folder.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_file in files[max_files:]:
        try:
            old_file.unlink()
        except Exception as e:
            print(f"⚠️ Could not delete {old_file}: {e}")