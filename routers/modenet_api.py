import cv2
import base64
import numpy as np
from fastapi import APIRouter, File, UploadFile
from models.modnet_infer import apply_modnet

router = APIRouter(prefix="/api/modnet", tags=["MODNet"])

@router.post("/process")
async def process_frame(file: UploadFile = File(...)):
    """Receive an image, apply MODNet, return base64-encoded result"""
    data = await file.read()
    npimg = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    result = apply_modnet(frame)

    _, buf = cv2.imencode(".jpg", result)
    b64_img = base64.b64encode(buf).decode("utf-8")

    return {"image_base64": b64_img}
