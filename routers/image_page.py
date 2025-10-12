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

# Central uploads folder (auto-create elsewhere in main.py or here)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request, "result": None})

@router.post("/", response_class=HTMLResponse)
async def process_image(
    request: Request,
    file: UploadFile,
    mode: str = Form("color"),          # "color" or "transparent"
    color: str = Form("#ffffff"),       # used only if mode == "color"
):
    # Unique names
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
        # Build RGBA cutout and save PNG
        rgba = apply_modnet_cutout_rgba(frame)
        output_path = UPLOAD_DIR / f"changed_{uid}.png"
        # Save with cv2 (expects BGRA) -> convert RGBA to BGRA
        bgra = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(str(output_path), bgra)
    else:
        # Solid color composite (PNG or JPG, keep JPG here)
        # Convert hex → BGR
        hex_color = color.lstrip("#")
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            r, g, b = (255, 255, 255)
        bg = np.full((frame.shape[0], frame.shape[1], 3), (b, g, r), dtype=np.uint8)

        # Save temp bg and composite
        temp_bg = UPLOAD_DIR / "temp_bg.jpg"
        cv2.imwrite(str(temp_bg), bg)
        result = apply_modnet(frame, bg_image_path=str(temp_bg))
        output_path = UPLOAD_DIR / f"changed_{uid}.jpg"
        cv2.imwrite(str(output_path), result)

    # Render page with paths
    return templates.TemplateResponse(
        "image.html",
        {
            "request": request,
            "original": f"uploads/{original_path.name}",
            "result": f"uploads/{output_path.name}",
            "mode": mode,
            "color": color,
        },
    )

@router.get("/download/{filename}")
async def download_image(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists():
        return {"error": "File not found"}
    # Pick media type by extension
    mt = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path, media_type=mt, filename=path.name)
