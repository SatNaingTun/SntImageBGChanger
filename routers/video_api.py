from fastapi import APIRouter, UploadFile, Form, File
from pathlib import Path
import cv2, numpy as np, base64, time
from modnet_infer_video import apply_modnet_video

router = APIRouter(prefix="/api/video", tags=["AJAX Video API"])

# Directories for saving processed frames and backgrounds
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
    """
    Process a webcam frame using the MODNet model (webcam version).
    Supports modes:
      - 'color': replace background with solid color
      - 'custom': replace background with uploaded image
      - 'transparent': remove background
    """
    try:
        # --- Read uploaded webcam frame ---
        frame_bytes = await file.read()
        npimg = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            return {"error": "Invalid webcam frame"}

        # --- Parse selected background color from HTML (RGB format) ---
        hex_color = color.lstrip("#")
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

        # ✅ Convert RGB → BGR (OpenCV uses BGR)
        bg_bgr = (b, g, r)
        print(f"🎨 Selected RGB({r},{g},{b}) → Applied BGR({b},{g},{r})")

        # --- Optional custom background ---
        bg_img = None
        if bg_file is not None:
            bg_bytes = await bg_file.read()
            bg_np = np.frombuffer(bg_bytes, np.uint8)
            bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)
            if bg_img is not None:
                print(f"🖼️ Custom background received: {bg_img.shape}")
            else:
                print("⚠️ Background file invalid or empty")

        # --- Apply MODNet for background change ---
        result = apply_modnet_video(frame, mode=mode, bgcolor=bg_bgr, bg_image=bg_img)

        # --- Save output frame for record/debug ---
        timestamp = int(time.time() * 1000)
        output_path = CHANGED_DIR / f"frame_changed_{timestamp}.jpg"
        cv2.imwrite(str(output_path), result)

        # --- Encode result to base64 for live preview ---
        _, buffer = cv2.imencode(".jpg", result)
        encoded = base64.b64encode(buffer).decode("utf-8")

        return {
            "result": f"data:image/jpeg;base64,{encoded}",
            "saved_path": f"/video/changed/{output_path.name}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
