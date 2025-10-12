from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse
from pathlib import Path
import cv2
import numpy as np
from modnet_infer import apply_modnet, apply_modnet_cutout_rgba

router = APIRouter(prefix="/api/image", tags=["AJAX Image API"])

BASE_DIR = Path("images")
UPLOAD_DIR = BASE_DIR / "upload"
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"

for folder in [UPLOAD_DIR, CHANGED_DIR, BACKGROUND_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

MAX_FILES_PER_FOLDER = 100


def cleanup_old_files(folder: Path, max_files: int = 100):
    files = sorted(folder.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_file in files[max_files:]:
        try:
            old_file.unlink()
        except Exception as e:
            print(f"⚠️ Could not delete {old_file}: {e}")


@router.post("/process")
async def process_image(
    file: UploadFile,
    mode: str = Form("color"),
    color: str = Form("#ffffff"),
    bg_file: UploadFile = None,
):
    """
    Process an uploaded image with MODNet and return JSON paths.
    Supports solid color, transparent, or custom background modes.
    """
    try:
        upload_name = Path(file.filename).stem
        upload_ext = Path(file.filename).suffix or ".jpg"
        original_path = UPLOAD_DIR / f"{upload_name}{upload_ext}"
        changed_ext = ".png" if mode == "transparent" else ".jpg"
        changed_path = CHANGED_DIR / f"{upload_name}_changed{changed_ext}"
        bg_path = BACKGROUND_DIR / f"{upload_name}_bg.jpg"

        # Debug received fields
        print("🎨 mode:", mode)
        print("🎨 color:", color)
        print("🎨 bg_file:", bg_file.filename if bg_file else None)

        # Decode portrait
        npimg = np.frombuffer(await file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            return JSONResponse({"error": "Invalid image."}, status_code=400)
        cv2.imwrite(str(original_path), frame)

        # Transparent
        if mode == "transparent":
            rgba = apply_modnet_cutout_rgba(frame)
            cv2.imwrite(str(changed_path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

        # Custom background image
        elif mode == "custom" and bg_file:
            np_bg = np.frombuffer(await bg_file.read(), np.uint8)
            bg_img = cv2.imdecode(np_bg, cv2.IMREAD_COLOR)
            if bg_img is not None:
                cv2.imwrite(str(bg_path), bg_img)
                result = apply_modnet(frame, bg_image_path=str(bg_path))
                cv2.imwrite(str(changed_path), result)
            else:
                return JSONResponse({"error": "Could not read background image."}, status_code=400)

        # Solid color
        else:
            hex_color = color.lstrip("#")
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
            except ValueError:
                r, g, b = (255, 255, 255)
            bg = np.full((frame.shape[0], frame.shape[1], 3), (b, g, r), dtype=np.uint8)
            cv2.imwrite(str(bg_path), bg)
            result = apply_modnet(frame, bg_image_path=str(bg_path))
            cv2.imwrite(str(changed_path), result)

        cleanup_old_files(UPLOAD_DIR)
        cleanup_old_files(CHANGED_DIR)
        cleanup_old_files(BACKGROUND_DIR)

        return {
            "original": f"/images/upload/{original_path.name}",
            "result": f"/images/changed/{changed_path.name}",
            "download": f"/image/download/{changed_path.name}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)
