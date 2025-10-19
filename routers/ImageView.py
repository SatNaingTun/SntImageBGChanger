from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import cv2
import numpy as np
import os

from modnet_infer import apply_modnet, apply_modnet_cutout_rgba, apply_modnet_blur_background, extract_background

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/imageview", tags=["Image View"])

# -------------------------------------------------------
# Folder structure
# -------------------------------------------------------
BASE_DIR = Path("images")
UPLOAD_DIR = BASE_DIR / "upload"
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"

for folder in [UPLOAD_DIR, CHANGED_DIR, BACKGROUND_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

MAX_FILES_PER_FOLDER = 100


def cleanup_old_files(folder: Path, max_files: int = 15):
    """Keep only latest N files."""
    files = sorted(folder.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_file in files[max_files:]:
        try:
            old_file.unlink()
        except Exception as e:
            print(f"⚠️ Could not delete {old_file}: {e}")


# -------------------------------------------------------
# Routes
# -------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def ImageView(request: Request):
    """Render upload page."""
    return templates.TemplateResponse("ImageView.html", {"request": request, "result": None})


@router.post("/", response_class=HTMLResponse)
async def process_image(
    request: Request,
    file: UploadFile,
    mode: str = Form("color"),
    color: str = Form("#ffffff"),
    bg_file: UploadFile = None,
    blur_strength: int = Form(35),
):
    """Process uploaded image with MODNet."""
    try:
        upload_name = Path(file.filename).stem
        upload_ext = Path(file.filename).suffix or ".jpg"
        original_path = UPLOAD_DIR / f"{upload_name}{upload_ext}"
        changed_ext = ".png" if mode == "transparent" else ".jpg"
        changed_path = CHANGED_DIR / f"{upload_name}_changed{changed_ext}"
        bg_path = BACKGROUND_DIR / f"{upload_name}_bg.jpg"

        # Decode main image
        data = await file.read()
        npimg = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            return HTMLResponse("<h3>❌ Could not decode uploaded image.</h3>", status_code=400)
        cv2.imwrite(str(original_path), frame)
        print(f"{mode} is running")
        # Transparent background
        if mode == "transparent":
             print("🧼 Transparent mode triggered")
             rgba = apply_modnet_cutout_rgba(frame)
             cv2.imwrite(str(changed_path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

        # Custom uploaded background
        elif mode == "custom" and bg_file:
            print("🖼️ Custom background mode triggered")
            bg_data = await bg_file.read()
            np_bg = np.frombuffer(bg_data, np.uint8)
            bg_img = cv2.imdecode(np_bg, cv2.IMREAD_COLOR)
            if bg_img is not None:
                cv2.imwrite(str(bg_path), bg_img)
                result = apply_modnet(frame, bg_image_path=str(bg_path))
                cv2.imwrite(str(changed_path), result)
            else:
                return HTMLResponse("<h3>❌ Could not read background image.</h3>", status_code=400)
                # Extract background only
        # elif mode == "extract_bg":
        #     result = extract_background(frame)
        #     if result is not None:
        #         cv2.imwrite(str(changed_path), result)  # Save the extracted background
        #     else:
        #         return HTMLResponse("<h3>❌ Could not extract background.</h3>", status_code=400)

        # Replace background with its blurred version
        elif mode == "blur_bg":
            print("Blur background mode triggered")
            # print(f" Blurring background with strength: {blur_strength}")
            result = apply_modnet_blur_background(frame_bgr=frame, blur_strength=blur_strength)
            if result is not None:
                cv2.imwrite(str(changed_path), result)
            else:
                return HTMLResponse("<h3>❌ Could not blur background.</h3>", status_code=400)

        # Solid color background
        else:
            print("🎨 Solid color mode triggered")
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

        # Cleanup (keep 100)
        cleanup_old_files(UPLOAD_DIR, MAX_FILES_PER_FOLDER)
        cleanup_old_files(CHANGED_DIR, MAX_FILES_PER_FOLDER)
        cleanup_old_files(BACKGROUND_DIR, MAX_FILES_PER_FOLDER)

        return templates.TemplateResponse(
            "image.html",
            {
                "request": request,
                "original": f"images/upload/{original_path.name}",
                "result": f"images/changed/{changed_path.name}",
                "mode": mode,
                "color": color,
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h3>Error:</h3><pre>{e}</pre>", status_code=500)


@router.get("/download/{filename}")
async def download_image(filename: str):
    """Download processed image."""
    path_changed = CHANGED_DIR / filename
    if not path_changed.exists():
        return HTMLResponse("<h3>File not found.</h3>", status_code=404)
    mt = "image/png" if path_changed.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path_changed, media_type=mt, filename=path_changed.name)
