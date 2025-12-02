from fastapi import APIRouter, UploadFile, Form, File, BackgroundTasks
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse
import cv2, numpy as np, base64, time, asyncio, json, uuid
from concurrent.futures import ThreadPoolExecutor
from inference.modnet_infer_video import apply_modnet_video, apply_modnet_video_file
from routers.CleanFiles import cleanup_old_files
from progress import read_progress, start_progress

router = APIRouter(prefix="/api/video", tags=["AJAX Video API"])

BASE_DIR = Path("video")
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"
CHANGED_VIDEO_DIR = BASE_DIR / "changedVideo"
UPLOAD_DIR = BASE_DIR / "upload"

# Ensure directories exist
for d in [CHANGED_DIR, BACKGROUND_DIR, CHANGED_VIDEO_DIR, UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=3)

# =================================================
# 🎥 Background Video Manager (for Webcam)
# =================================================
bg_video_cache = {
    "cap": None,
    "path": None,
    "frame_count": 0,
    "index": 0
}

def get_next_bg_frame(bg_path, target_size):
    """Read next frame from background video, looping when necessary."""
    global bg_video_cache

    if not bg_path:
        return None

    # Initialize or reload if new path
    if (bg_video_cache["path"] != bg_path) or (bg_video_cache["cap"] is None):
        if bg_video_cache["cap"]:
            bg_video_cache["cap"].release()
        cap = cv2.VideoCapture(str(bg_path))
        if not cap.isOpened():
            print(f"⚠️ Could not open background video: {bg_path}")
            return None
        bg_video_cache.update({
            "cap": cap,
            "path": bg_path,
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1,
            "index": 0
        })
        print(f"🎞️ Loaded webcam background video ({bg_video_cache['frame_count']} frames)")

    cap = bg_video_cache["cap"]
    total = bg_video_cache["frame_count"]
    idx = bg_video_cache["index"]

    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        bg_video_cache["index"] = 1
    else:
        bg_video_cache["index"] = (idx + 1) % total

    if ret and frame is not None:
        frame = cv2.resize(frame, target_size)
        return frame
    return None



# =================================================
# 🧠 Process Single Frame (Webcam)
# =================================================
def process_frame_sync(frame_bytes, mode, color, bg_file_data=None, bg_temp_path=None):
    """Heavy synchronous MODNet frame processing (runs in thread)."""
    npimg = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "Invalid webcam frame"}

    # Parse color
    hex_color = color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    bg_bgr = (b, g, r)

    bg_img = None
    if bg_temp_path:
        ext = Path(bg_temp_path).suffix.lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv"]:
            bg_img = get_next_bg_frame(bg_temp_path, (frame.shape[1], frame.shape[0]))
        else:
            img = cv2.imread(str(bg_temp_path))
            if img is not None:
                bg_img = cv2.resize(img, (frame.shape[1], frame.shape[0]))

    elif bg_file_data:
        bg_np = np.frombuffer(bg_file_data, np.uint8)
        bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)

    result = apply_modnet_video(frame, mode=mode, bgcolor=bg_bgr, bg_image=bg_img)

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
    """Async MODNet background processing for webcam frames (supports video BG)."""
    frame_bytes = await file.read()
    bg_temp_path = None

    # Save uploaded background temporarily if provided
    if bg_file:
        ext = Path(bg_file.filename).suffix or ".jpg"
        bg_temp_path = (UPLOAD_DIR / f"bg_webcam{ext}").resolve()
        with open(bg_temp_path, "wb") as f:
            f.write(await bg_file.read())

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        executor,
        process_frame_sync,
        frame_bytes,
        mode,
        color,
        None,
        str(bg_temp_path) if bg_temp_path else None,
    )
    return result




# =================================================
# 🎞️ Process Full Video (Upload Tab)
# =================================================
@router.post("/process_video")
async def process_video(
    background_tasks: BackgroundTasks,
    mode: str = Form("color"),
    color: str = Form("#00ff00"),
    file: UploadFile = File(...),
    bg_file: UploadFile = File(None),
    blur_strength: int = Form(25),
):
    """Handles video upload and background processing (supports image or video backgrounds)."""

    file_id = str(uuid.uuid4())[:8]
    input_path = (UPLOAD_DIR / f"input_{file_id}.mp4").resolve()
    output_path = (CHANGED_VIDEO_DIR / f"output_{file_id}.mp4").resolve()
    progress_path = (CHANGED_VIDEO_DIR / f"progress_{file_id}.json").resolve()
    bg_path = None

    # Save main input video
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Save optional background (image or video)
    if bg_file:
        ext = Path(bg_file.filename).suffix or ".jpg"
        bg_path = (UPLOAD_DIR / f"bg_{file_id}{ext}").resolve()
        with open(bg_path, "wb") as f:
            f.write(await bg_file.read())
        print(f"🎨 Background saved as {bg_path.name}")

    start_progress(progress_path, "starting")

    # ✅ Schedule background execution (non-blocking)
    background_tasks.add_task(
        apply_modnet_video_file,
        str(input_path),
        str(output_path),
        mode,
        color,
        str(bg_path) if bg_path else None,
        str(progress_path),
        blur_strength
    )

    # ✅ Return immediately for frontend polling
    return {
        "result": "processing",
        "progress_id": file_id,
        "output_url": f"/video/changedVideo/{output_path.name}"
    }

# =================================================
# ⬇️ Download Processed Video
# =================================================
@router.get("/download/{filename}")
async def download_video(filename: str):
    file_path = CHANGED_VIDEO_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not ready"}, status_code=404)

    # Ensure file fully written
    for _ in range(10):
        if file_path.exists() and file_path.stat().st_size > 0:
            break
        await asyncio.sleep(0.5)

    return FileResponse(path=file_path, filename=filename, media_type="video/mp4")

# =================================================
# 📊 Progress Polling Endpoint
# =================================================
@router.get("/progress/{file_id}")
async def get_progress(file_id: str):
    progress_file = (CHANGED_VIDEO_DIR / f"progress_{file_id}.json").resolve()

    if not progress_file.exists():
        return {"progress": 0.0, "stage": "initializing"}

    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("⚠️ Error reading progress file:", e)
        data = {"progress": 0.0, "stage": "unknown"}

    data["timestamp"] = time.time()
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return JSONResponse(content=data, headers=headers)
