# ==========================================
# modnet_infer_video.py
# ==========================================
import sys
import cv2
import numpy as np
import torch
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # project root
MODNET_PATH = ROOT / "thirdparty" / "MODNet" / "src"
if str(MODNET_PATH) not in sys.path:
    sys.path.append(str(MODNET_PATH))

try:
    from models.modnet import MODNet
except ModuleNotFoundError as e:
    raise ImportError(f"❌ Could not import MODNet. Check path: {MODNET_PATH}\n{e}")

# --------------------------------------------------
# 🔧 MODEL INITIALIZATION
# --------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

ROOT = Path(__file__).resolve().parent
webcam_model_name = "modnet_webcam_portrait_matting.ckpt"
webcam_model_path = ROOT / "models" / webcam_model_name

print(f"🔧 Loading webcam MODNet model: {webcam_model_path}")

modnet_webcam = MODNet(backbone_pretrained=False).to(device)

# Load checkpoint
state = torch.load(webcam_model_path, map_location=device)
if isinstance(state, dict) and "state_dict" in state:
    state = state["state_dict"]
state = {k.replace("module.", ""): v for k, v in state.items()}

missing, unexpected = modnet_webcam.load_state_dict(state, strict=False)
print(f"✅ Webcam MODNet loaded. Missing: {len(missing)}, Unexpected: {len(unexpected)}")

modnet_webcam.eval()


# --------------------------------------------------
# 🧠 INFERENCE FUNCTION
# --------------------------------------------------
def apply_modnet_video(frame, mode="color", bgcolor=(255, 255, 255), bg_image=None):
    """
    Apply MODNet portrait matting for webcam frames.
    mode: 'color', 'custom', 'transparent'
    """
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
    image = image.astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image.transpose(2, 0, 1)).unsqueeze(0).to(device)

    with torch.no_grad():
        _, _, matte = modnet_webcam(image_tensor, True)
    matte = matte[0][0].cpu().numpy()

    matte = cv2.resize(matte, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
    matte_3 = np.repeat(matte[:, :, np.newaxis], 3, axis=2)
    fg = frame.astype(np.float32) / 255.0

    h, w, _ = frame.shape
    if mode == "transparent":
        result = cv2.cvtColor((fg * matte_3 * 255).astype(np.uint8), cv2.COLOR_BGR2BGRA)
        result[:, :, 3] = (matte * 255).astype(np.uint8)
        return result

    elif mode == "custom" and bg_image is not None:
        bg_resized = cv2.resize(bg_image, (w, h))
        bg = bg_resized.astype(np.float32) / 255.0
        result = (fg * matte_3 + bg * (1 - matte_3)) * 255
        return result.astype(np.uint8)

    else:  # solid color background
        bg = np.full_like(frame, bgcolor, dtype=np.uint8).astype(np.float32) / 255.0
        result = (fg * matte_3 + bg * (1 - matte_3)) * 255
        return result.astype(np.uint8)
