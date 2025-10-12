from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid
import cv2
import numpy as np

from modnet_infer import apply_modnet, apply_modnet_cutout_rgba

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/image", tags=["Image"])

# -------------------------------------------------------
# Create all required folders if missing
# -------------------------------------------------------
BASE_DIR = Path("images")
UPLOAD_DIR = BASE_DIR / "upload"
CHANGED_DIR = BASE_DIR / "changed"
BACKGROUND_DIR = BASE_DIR / "background"

for folder in [UPLOAD_DIR, CHANGED_DIR, BACKGROUND_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def image_page(request: Request):
    """Render upload page."""
    return templates.TemplateResponse("image.html", {"request": request, "result": None})


@router.post("/", response_class=HTMLResponse)
async def process_image(
    request: Request,
    file: UploadFile,
    mode: str = Form("color"),          # "color" or "transparent"
    color: str = Form("#ffffff"),       # used only if mode == "color"
):
    """Process uploaded image with MODNet."""
    uid = uuid.uuid4().hex[:8]
    original_path = UPLOAD_DIR / f"original_{uid}.jpg"

    # Decode upload
    data = await file.read()
    npimg = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "Could not decode the uploaded image."}

    # Save original
    cv2.imwrite(str(original_path), frame)

    # Branch by mode
    if mode == "transparent":
        # Transparent PNG (no background)
        rgba = apply_modnet_cutout_rgba(frame)
        output_path = CHANGED_DIR / f"changed_{uid}.png"
        bgra = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(str(output_path), bgra)
    else:
        # Solid color background
        hex_color = color.lstrip("#")
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            r, g, b = (255, 255, 255)

        bg = np.full((frame.shape[0], frame.shape[1], 3), (b, g, r), dtype=np.uint8)
        bg_temp = BACKGROUND_DIR / f"bg_{uid}.jpg"
        cv2.imwrite(str(bg_temp), bg)

        result = apply_modnet(frame, bg_image_path=str(bg_temp))
        output_path = CHANGED_DIR / f"changed_{uid}.jpg"
        cv2.imwrite(str(output_path), result)

    # Render output page
    return templates.TemplateResponse(
        "image.html",
        {
            "request": request,
            "original": f"images/upload/{original_path.name}",
            "result": f"images/changed/{output_path.name}",
            "mode": mode,
            "color": color,
        },
    )


@router.get("/download/{filename}")
async def download_image(filename: str):
    """Download processed image."""
    path_changed = CHANGED_DIR / filename
    if not path_changed.exists():
        return {"error": "File not found"}
    mt = "image/png" if path_changed.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path_changed, media_type=mt, filename=path_changed.name)
