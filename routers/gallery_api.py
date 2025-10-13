from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter(prefix="/api/gallery", tags=["Gallery API"])

RECORDED_DIR = Path("video/recorded")
SNAPSHOT_DIR = Path("video/snapshots")
RECORDED_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/list")
async def list_gallery():
    """
    Return combined list of recorded videos and snapshots.
    """
    gallery = []

    # Videos
    for file in sorted(RECORDED_DIR.glob("*.webm"), reverse=True):
        thumb = RECORDED_DIR / f"{file.stem}_thumb.jpg"
        gallery.append({
            "type": "video",
            "path": f"/video/recorded/{file.name}",
            "thumbnail": f"/video/recorded/{thumb.name}" if thumb.exists() else "",
            "name": file.name
        })

    # Snapshots
    for file in sorted(SNAPSHOT_DIR.glob("*.jpg"), reverse=True):
        gallery.append({
            "type": "snapshot",
            "path": f"/video/snapshots/{file.name}",
            "thumbnail": f"/video/snapshots/{file.name}",
            "name": file.name
        })

    return {"gallery": gallery}


@router.delete("/delete/{filename}")
async def delete_item(filename: str):
    """
    Delete a video or snapshot by filename.
    """
    for folder in [RECORDED_DIR, SNAPSHOT_DIR]:
        file_path = folder / filename
        if file_path.exists():
            file_path.unlink()
            # Delete thumbnail if exists
            thumb = file_path.parent / f"{file_path.stem}_thumb.jpg"
            if thumb.exists():
                thumb.unlink()
            return {"message": f"Deleted {filename}"}

    raise HTTPException(status_code=404, detail="File not found")
