from fastapi import APIRouter, UploadFile, Form, File
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse
import cv2, numpy as np, base64, time, asyncio
from concurrent.futures import ThreadPoolExecutor
from modnet_infer_video import apply_modnet_video,apply_modnet_video_file
import uuid
from routers.CleanFiles import cleanup_old_files


router = APIRouter(prefix="/api/video", tags=["AJAX Video API"])

BASE_DIR = Path("video")
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"
CHANGED_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)

CHANGED_VIDEO_DIR = BASE_DIR / "changedVideo"
CHANGED_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = BASE_DIR / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=3)

def process_frame_sync(frame_bytes, mode, color, bg_file_data=None):
    """Heavy synchronous MODNet frame processing (runs in thread)."""
    npimg = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "Invalid webcam frame"}

    # Parse color
    hex_color = color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    bg_bgr = (b, g, r)

    # Optional background
    bg_img = None
    if bg_file_data:
        bg_np = np.frombuffer(bg_file_data, np.uint8)
        bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)

    # Apply MODNet
    result = apply_modnet_video(frame, mode=mode, bgcolor=bg_bgr, bg_image=bg_img)

    # Save & encode
    timestamp = int(time.time() * 1000)
    output_path = CHANGED_DIR / f"frame_changed_{timestamp}.jpg"
    cv2.imwrite(str(output_path), result)
    _, buffer = cv2.imencode(".jpg", result)
    encoded = base64.b64encode(buffer).decode("utf-8")
    cleanup_old_files(CHANGED_DIR, max_files=100)
    cleanup_old_files(BACKGROUND_DIR, max_files=100)
    return {
        "result": f"data:image/jpeg;base64,{encoded}",
        "saved_path": f"/video/changed/{output_path.name}"
    }

@router.post("/process_frame")
async def process_frame(
    mode: str = Form("color"),
    color: str = Form("#ffffff"),
    file: UploadFile = File(...),
    bg_file: UploadFile = None
):
    """Async wrapper for MODNet background processing."""
    frame_bytes = await file.read()
    bg_data = await bg_file.read() if bg_file else None

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        executor,
        process_frame_sync,
        frame_bytes,
        mode,
        color,
        bg_data,
    )
    return result

# =================================================
# 🎞️ PROCESS FULL VIDEO (for Upload tab)
# =================================================
@router.post("/process_video")
async def process_video(
    mode: str = Form("color"),
    color: str = Form("#00ff00"),
    file: UploadFile = File(...),
    bg_file: UploadFile = File(None),
):
    """
    Handle full uploaded video and run MODNet inference asynchronously.
    Supports:
      - Solid color background
      - Custom background image
      - Transparent background
    """
    file_id = str(uuid.uuid4())[:8]
    input_path = UPLOAD_DIR / f"input_{file_id}.mp4"
    output_path = CHANGED_VIDEO_DIR / f"output_{file_id}.mp4"
    bg_path = None

    # Save uploaded video
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Optional background image
    if bg_file:
        bg_path = UPLOAD_DIR / f"bg_{file_id}.jpg"
        with open(bg_path, "wb") as f:
            f.write(await bg_file.read())

    # Run inference in background thread
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        executor,
        apply_modnet_video_file,
        str(input_path),
        str(output_path),
        mode,
        color,
        str(bg_path) if bg_path else None,
    )

    # Clean old files
    cleanup_old_files(CHANGED_VIDEO_DIR, max_files=20)
    cleanup_old_files(UPLOAD_DIR, max_files=5)

    # Return path to processed video
    rel_path = f"/video/changedVideo/{output_path.name}"
    return {"result": "done", "output_url": rel_path}


@router.get("/download/{filename}")
async def download_video(filename: str):
    """Serve processed video."""
    file_path = CHANGED_VIDEO_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not ready"}, status_code=404)

    # ensure file fully written
    for _ in range(10):
        if file_path.exists() and file_path.stat().st_size > 0:
            break
        await asyncio.sleep(0.5)

    return FileResponse(path=file_path, filename=filename, media_type="video/mp4")