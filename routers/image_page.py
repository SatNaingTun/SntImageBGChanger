from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import cv2
import numpy as np
import os
import time

from modnet_infer import apply_modnet, apply_modnet_cutout_rgba

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/image", tags=["Image"])

# -------------------------------------------------------
# Folder structure
# -------------------------------------------------------
BASE_DIR = Path("images")
UPLOAD_DIR = BASE_DIR / "upload"
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"

for folder in [UPLOAD_DIR, CHANGED_DIR, BACKGROUND_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

MAX_FILES_PER_FOLDER = 100  # keep latest 100


# -------------------------------------------------------
# Utility: cleanup old files
# -------------------------------------------------------
def cleanup_old_files(folder: Path, max_files: int = 100):
    """Keep only the most recent N files based on modified time."""
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
async def image_page(request: Request):
    """Render the upload page."""
    return templates.TemplateResponse("image.html", {"request": request, "result": None})


@router.post("/", response_class=HTMLResponse)
async def process_image(
    request: Request,
    file: UploadFile,
    mode: str = Form("color"),
    color: str = Form("#ffffff"),
):
    try:
        # Extract filename safely
        upload_name = Path(file.filename).stem
        upload_ext = Path(file.filename).suffix or ".jpg"

        # Define paths
        original_path = UPLOAD_DIR / f"{upload_name}{upload_ext}"
        changed_ext = ".png" if mode == "transparent" else ".jpg"
        changed_path = CHANGED_DIR / f"{upload_name}_changed{changed_ext}"
        bg_path = BACKGROUND_DIR / f"{upload_name}_bg.jpg"

        # Read uploaded file
        data = await file.read()
        npimg = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            return HTMLResponse("<h3>❌ Could not decode uploaded image.</h3>", status_code=400)

        # Save (overwrite old if exists)
        cv2.imwrite(str(original_path), frame)

        # Transparent mode
        if mode == "transparent":
            rgba = apply_modnet_cutout_rgba(frame)
            bgra = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
            cv2.imwrite(str(changed_path), bgra)

        # Solid color mode
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

        # ✅ Cleanup: keep only last 100 per folder
        cleanup_old_files(UPLOAD_DIR, MAX_FILES_PER_FOLDER)
        cleanup_old_files(CHANGED_DIR, MAX_FILES_PER_FOLDER)
        cleanup_old_files(BACKGROUND_DIR, MAX_FILES_PER_FOLDER)

        # ✅ Render template
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
    """Download the processed image."""
    path_changed = CHANGED_DIR / filename
    if not path_changed.exists():
        return HTMLResponse("<h3>File not found.</h3>", status_code=404)
    mt = "image/png" if path_changed.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path_changed, media_type=mt, filename=path_changed.name)
