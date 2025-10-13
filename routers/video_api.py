from fastapi import APIRouter, UploadFile, Form, File
from pathlib import Path
import cv2, numpy as np, base64, time
from modnet_infer_video import apply_modnet_video

router = APIRouter(prefix="/api/video", tags=["AJAX Video API"])

BASE_DIR = Path("video")
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"
CHANGED_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/process_frame")
async def process_frame(
    mode: str = Form("color"),
    color: str = Form("#ffffff"),
    file: UploadFile = File(...),
    bg_file: UploadFile = None
):
    """Process webcam frame using MODNet video model."""
    try:
        # --- read webcam frame ---
        frame_bytes = await file.read()
        npimg = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            return {"error": "Invalid webcam frame"}

        # --- parse solid color ---
        hex_color = color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

        # --- optional custom background ---
        bg_img = None
        if bg_file is not None:
            bg_bytes = await bg_file.read()
            bg_np = np.frombuffer(bg_bytes, np.uint8)
            bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)
            print("🎨 Background image received:", bg_img.shape if bg_img is not None else "None")

        # --- run MODNet ---
        result = apply_modnet_video(frame, mode=mode, bgcolor=(r, g, b), bg_image=bg_img)

        # --- save output ---
        timestamp = int(time.time() * 1000)
        output_path = CHANGED_DIR / f"frame_changed_{timestamp}.jpg"
        cv2.imwrite(str(output_path), result)

        # --- send Base64 to frontend ---
        _, buffer = cv2.imencode(".jpg", result)
        encoded = base64.b64encode(buffer).decode("utf-8")

        return {
            "result": f"data:image/jpeg;base64,{encoded}",
            "saved_path": f"/video/changed/{output_path.name}"
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"error": str(e)}
