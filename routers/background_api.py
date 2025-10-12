from fastapi import APIRouter, UploadFile, Form
import shutil
import cv2
import numpy as np
from pathlib import Path

router = APIRouter(prefix="/api/background", tags=["Background"])
BG_PATH = Path("model/bg_custom.jpg")


@router.post("/upload")
async def upload_background(file: UploadFile):
    """Upload a custom background image."""
    with open(BG_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "ok", "msg": "Background image uploaded"}


@router.post("/solid")
async def solid_background(color: str = Form("#ffffff")):
    """
    Create a solid background image from a hex color (e.g. #RRGGBB).
    Example: color="#00ff00" -> green background.
    """
    # Remove '#' and convert to integer RGB
    color = color.lstrip("#")
    if len(color) != 6:
        return {"status": "error", "msg": "Invalid color format"}
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return {"status": "error", "msg": "Invalid color code"}

    bg_color = (b, g, r)  # OpenCV uses BGR
    bg = np.full((720, 1280, 3), bg_color, dtype=np.uint8)
    cv2.imwrite(str(BG_PATH), bg)
    return {"status": "ok", "msg": f"Solid background set to #{color.upper()}"}
