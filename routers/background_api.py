from fastapi import APIRouter, UploadFile, Form
from pathlib import Path
import numpy as np, cv2, shutil, asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/api/background", tags=["Background API"])
BG_PATH = Path("model/bg_custom.jpg")
executor = ThreadPoolExecutor(max_workers=2)

# ---------- Helper Functions ----------
def save_background_sync(file_obj, dst: Path):
    """Blocking save (runs in thread executor)."""
    with open(dst, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)
    return {"status": "ok", "msg": f"Background saved to {dst}"}

def solid_background_sync(color_hex: str):
    """Blocking creation of a solid background."""
    color = color_hex.lstrip("#")
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    bg_color = (b, g, r)  # OpenCV uses BGR
    bg = np.full((720, 1280, 3), bg_color, dtype=np.uint8)
    cv2.imwrite(str(BG_PATH), bg)
    return {"status": "ok", "msg": f"Solid background set to #{color_hex.upper()}"}

# ---------- API Endpoints ----------
@router.post("/upload")
async def upload_background(file: UploadFile):
    """Upload a custom background image asynchronously."""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, save_background_sync, file.file, BG_PATH)
    return result

@router.post("/solid")
async def solid_background(color: str = Form("#ffffff")):
    """Generate a solid background image asynchronously."""
    color = color.lstrip("#")
    if len(color) != 6:
        return {"status": "error", "msg": "Invalid color format"}

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, solid_background_sync, color)
        return result
    except ValueError:
        return {"status": "error", "msg": "Invalid color code"}
