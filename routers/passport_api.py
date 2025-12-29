# app/routes/passport_api.py
from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import Response
from PIL import Image

router = APIRouter(prefix="/api/passport", tags=["passport"])

def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / 25.4))

@router.post("/render")
async def render_passport_photo(
    file: UploadFile = File(...),

    # Output size
    out_width_mm: Optional[float] = Form(None),
    out_height_mm: Optional[float] = Form(None),
    dpi: int = Form(300),
    out_width_px: Optional[int] = Form(None),
    out_height_px: Optional[int] = Form(None),

    # Crop box (original image coordinates)
    crop_x: float = Form(...),
    crop_y: float = Form(...),
    crop_w: float = Form(...),
    crop_h: float = Form(...),

    # Style
    bg: str = Form("white"),
    bg_hex: str = Form("#FFFFFF"),
    margin_pct: float = Form(0.06),
    fmt: str = Form("jpeg"),
    quality: int = Form(92),
):
    if out_width_px and out_height_px:
        W, H = out_width_px, out_height_px
    elif out_width_mm and out_height_mm:
        W = mm_to_px(out_width_mm, dpi)
        H = mm_to_px(out_height_mm, dpi)
    else:
        raise HTTPException(400, "Output size not specified")

    raw = await file.read()
    img = Image.open(io.BytesIO(raw)).convert("RGB")

    iw, ih = img.size
    x = max(0, min(crop_x, iw - 1))
    y = max(0, min(crop_y, ih - 1))
    w = max(1, min(crop_w, iw - x))
    h = max(1, min(crop_h, ih - y))

    crop = img.crop((int(x), int(y), int(x + w), int(y + h)))

    if bg == "white":
        bg_color = (255, 255, 255)
    elif bg == "blue":
        bg_color = (210, 228, 245)
    else:
        bg_color = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    canvas = Image.new("RGB", (W, H), bg_color)

    margin_x = int(W * margin_pct)
    margin_y = int(H * margin_pct)
    inner_w = W - 2 * margin_x
    inner_h = H - 2 * margin_y

    scale = min(inner_w / crop.width, inner_h / crop.height)
    resized = crop.resize(
        (int(crop.width * scale), int(crop.height * scale)),
        Image.Resampling.LANCZOS
    )

    px = (W - resized.width) // 2
    py = (H - resized.height) // 2
    canvas.paste(resized, (px, py))

    out = io.BytesIO()
    if fmt == "png":
        canvas.save(out, format="PNG")
        media = "image/png"
        ext = "png"
    else:
        canvas.save(out, format="JPEG", quality=quality)
        media = "image/jpeg"
        ext = "jpg"

    return Response(
        content=out.getvalue(),
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="passport.{ext}"'}
    )
