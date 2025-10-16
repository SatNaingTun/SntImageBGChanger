import cv2, base64, numpy as np, asyncio
from fastapi import APIRouter, File, UploadFile
from concurrent.futures import ThreadPoolExecutor
from modnet_infer import apply_modnet

router = APIRouter(prefix="/api/modnet", tags=["MODNet"])
executor = ThreadPoolExecutor(max_workers=2)

def modnet_sync(frame_bytes):
    npimg = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    result = apply_modnet(frame)
    _, buf = cv2.imencode(".jpg", result)
    return base64.b64encode(buf).decode("utf-8")

@router.post("/process")
async def process_frame(file: UploadFile = File(...)):
    data = await file.read()
    loop = asyncio.get_running_loop()
    b64_img = await loop.run_in_executor(executor, modnet_sync, data)
    return {"image_base64": b64_img}
