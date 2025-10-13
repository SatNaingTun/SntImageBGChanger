from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os, time
import ffmpeg

router = APIRouter(prefix="/api/record", tags=["Recording API"])

RECORDED_DIR = Path("video/recorded")
RECORDED_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_recording(video: UploadFile = File(...)):
    """
    Save uploaded WebM recording and generate thumbnail.
    """
    try:
        timestamp = int(time.time() * 1000)
        base_name = f"recorded_{timestamp}"
        webm_path = RECORDED_DIR / f"{base_name}.webm"

        with open(webm_path, "wb") as f:
            f.write(await video.read())
        print(f"💾 Saved uploaded video: {webm_path}")

        # Extract thumbnail (first frame)
        thumb_path = RECORDED_DIR / f"{base_name}_thumb.jpg"
        try:
            (
                ffmpeg
                .input(str(webm_path), ss=0.5)
                .output(str(thumb_path), vframes=1, loglevel='error')
                .overwrite_output()
                .run()
            )
            print(f"🖼️ Thumbnail created: {thumb_path}")
        except Exception as e:
            print(f"⚠️ Thumbnail creation failed: {e}")

        return {
            "message": "Recording saved successfully",
            "video_path": f"/video/recorded/{webm_path.name}",
            "thumbnail_path": f"/video/recorded/{thumb_path.name}",
            "download_link": f"/api/record/download/{webm_path.name}"
        }

    except Exception as e:
        print("❌ Upload failed:", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_recording(filename: str):
    """
    Download a recorded .webm or .jpg file.
    """
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
    """
    List all recorded WebM files with thumbnails.
    """
    recordings = []
    for file in sorted(RECORDED_DIR.glob("*.webm"), reverse=True):
        base_name = file.stem
        thumb_path = RECORDED_DIR / f"{base_name}_thumb.jpg"
        recordings.append({
            "video_path": f"/video/recorded/{file.name}",
            "thumbnail_path": f"/video/recorded/{thumb_path.name}" if thumb_path.exists() else "",
            "download_link": f"/api/record/download/{file.name}"
        })
    return {"recordings": recordings}


@router.delete("/delete/{filename}")
async def delete_recording(filename: str):
    """
    Delete a recorded WebM file and its thumbnail.
    """
    webm_path = RECORDED_DIR / filename
    thumb_path = RECORDED_DIR / f"{webm_path.stem}_thumb.jpg"

    if not webm_path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        os.remove(webm_path)
        if thumb_path.exists():
            os.remove(thumb_path)
        print(f"🗑️ Deleted: {filename}")
        return {"message": "Recording deleted", "deleted": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete {filename}: {e}")
