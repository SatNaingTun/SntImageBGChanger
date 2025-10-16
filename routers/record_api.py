from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os, time, asyncio
import ffmpeg
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/api/record", tags=["Recording API"])

RECORDED_DIR = Path("video/recorded")
SNAPSHOT_DIR = Path("video/snapshots")
RECORDED_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=3)

def save_video_sync(video_path: Path, data: bytes):
    """Blocking save + thumbnail extraction."""
    with open(video_path, "wb") as f:
        f.write(data)
    thumb_path = video_path.with_name(video_path.stem + "_thumb.jpg")
    try:
        (
            ffmpeg
            .input(str(video_path), ss=0.5)
            .output(str(thumb_path), vframes=1, loglevel="error")
            .overwrite_output()
            .run()
        )
    except Exception as e:
        print(f"⚠️ Thumbnail creation failed: {e}")
    return thumb_path

@router.post("/upload")
async def upload_recording(video: UploadFile = File(...)):
    """Save uploaded WebM recording and generate thumbnail asynchronously."""
    try:
        timestamp = int(time.time() * 1000)
        base_name = f"recorded_{timestamp}"
        webm_path = RECORDED_DIR / f"{base_name}.webm"
        data = await video.read()
        loop = asyncio.get_running_loop()
        thumb_path = await loop.run_in_executor(executor, save_video_sync, webm_path, data)

        return {
            "message": "Recording saved successfully",
            "video_path": f"/video/recorded/{webm_path.name}",
            "thumbnail_path": f"/video/recorded/{thumb_path.name}",
            "download_link": f"/api/record/download/{webm_path.name}",
        }
    except Exception as e:
        print("❌ Upload failed:", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_recording(filename: str):
    """Download recorded video or thumbnail."""
    file_path = RECORDED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = (
        "video/webm" if file_path.suffix.lower() == ".webm"
        else "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"]
        else "application/octet-stream"
    )
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)

@router.get("/list")
async def list_recordings():
    """List all recordings."""
    recordings = []
    for file in sorted(RECORDED_DIR.glob("*.webm"), reverse=True):
        base = file.stem
        thumb = RECORDED_DIR / f"{base}_thumb.jpg"
        recordings.append({
            "video_path": f"/video/recorded/{file.name}",
            "thumbnail_path": f"/video/recorded/{thumb.name}" if thumb.exists() else "",
            "download_link": f"/api/record/download/{file.name}",
        })
    return {"recordings": recordings}

@router.delete("/delete/{filename}")
async def delete_recording(filename: str):
    """Delete recording + thumbnail."""
    webm = RECORDED_DIR / filename
    thumb = RECORDED_DIR / f"{webm.stem}_thumb.jpg"
    if not webm.exists():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        os.remove(webm)
        if thumb.exists():
            os.remove(thumb)
        return {"message": "Deleted", "deleted": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")

@router.post("/snapshot_upload")
async def snapshot_upload(snapshot: UploadFile = File(...)):
    """Save webcam snapshot asynchronously."""
    try:
        data = await snapshot.read()
        timestamp = int(time.time() * 1000)
        filename = f"snapshot_{timestamp}.jpg"
        save_path = SNAPSHOT_DIR / filename
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_path.write_bytes, data)
        return {"message": "Snapshot saved", "path": f"/video/snapshots/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
