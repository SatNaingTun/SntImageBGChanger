import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from modnet_infer import apply_modnet

router = APIRouter(prefix="/ws", tags=["MODNet Stream"])

@router.websocket("/modnet")
async def modnet_stream(ws: WebSocket):
    await ws.accept()
    print("🔌 MODNet WebSocket connected")
    try:
        while True:
            frame_bytes = await ws.receive_bytes()
            npimg = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            # apply white background
            result = apply_modnet(frame, bg_image_path=None)
            _, enc = cv2.imencode(".jpg", result, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            await ws.send_bytes(enc.tobytes())
    except WebSocketDisconnect:
        print("❌ MODNet WebSocket disconnected")
