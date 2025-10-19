from fastapi import APIRouter, UploadFile, Form, File
from pathlib import Path
import cv2, numpy as np, base64, time, asyncio
from concurrent.futures import ThreadPoolExecutor
from modnet_infer_video import apply_modnet_video
from routers.CleanFiles import cleanup_old_files

router = APIRouter(prefix="/api/video", tags=["AJAX Video API"])

BASE_DIR = Path("video")
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"
CHANGED_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)

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
