import torch
import cv2
import numpy as np
from torchvision import transforms
from PIL import Image
import sys
from pathlib import Path
import os

# -------------------------------------------------------
# Add path to official MODNet repo
# -------------------------------------------------------
ROOT = Path(__file__).resolve().parent  # project root
MODNET_PATH = ROOT / "thirdparty" / "MODNet" / "src"
if str(MODNET_PATH) not in sys.path:
    sys.path.append(str(MODNET_PATH))

try:
    from models.modnet import MODNet
except ModuleNotFoundError as e:
    raise ImportError(f"❌ Could not import MODNet. Check path: {MODNET_PATH}\n{e}")

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🧠 Using device: {device}")

# -------------------------------------------------------
# Load your fine-tuned checkpoint
# -------------------------------------------------------
model_name = "modnet_photographic_portrait_matting.ckpt"
CKPT_PATH = ROOT / "models" / model_name

modnet = MODNet(backbone_pretrained=False).to(device)

print(f"Loading checkpoint from: {CKPT_PATH}")
try:
    state = torch.load(CKPT_PATH, map_location=device)
except FileNotFoundError:
    raise RuntimeError(
        f"Model checkpoint not found at '{CKPT_PATH}'. "
        "Please ensure the file exists before running the application."
    )
if isinstance(state, dict) and "state_dict" in state:
    state = state["state_dict"]
state = {k.replace("module.", ""): v for k, v in state.items()}
missing, unexpected = modnet.load_state_dict(state, strict=False)
print(f"✅ MODNet loaded ({device}) | Missing: {len(missing)} | Unexpected: {len(unexpected)}")

modnet.eval()

# -------------------------------------------------------
# Define preprocess globally (BEFORE the function)
# -------------------------------------------------------
preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5],
                         std=[0.5, 0.5, 0.5])
])
# UPLOAD_PATH  = Path("uploads/original_8bf0b283.jpg")
# if not UPLOAD_PATH.exists():
#     raise FileNotFoundError(f"❌ Could not find {UPLOAD_PATH}. Please update the path.")

# im = Image.open(UPLOAD_PATH).convert("RGB").resize((512, 512))
# print("Preprocess output type:", type(preprocess(im)))  # Debug line to check the type

# -------------------------------------------------------
# Inference function
# -------------------------------------------------------

@torch.inference_mode()
def apply_modnet(frame_bgr, bg_image_path=None, bgcolor=(255, 255, 255)):
    """
    Apply MODNet to remove background and blend with custom background image.
    If bg_image_path is None or not found, use solid background color (default: white).
    """
    # ---- Preprocess ----
    h, w, _ = frame_bgr.shape
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb).resize((512, 512))
    tensor_input = preprocess(im)              # -> torch.Tensor [3,512,512]
    x = tensor_input.unsqueeze(0).to(device)   # -> [1,3,512,512]
    # ---- Inference ----
    _, _, matte = modnet(x, True)
    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)

    # ---- Normalize matte ----
    matte = np.clip(matte, 0, 1)

    # Optional cleanup: light threshold to remove weak alpha regions
    matte = np.where(matte > 0.2, matte, 0)
    matte = cv2.GaussianBlur(matte, (5, 5), 0)  # smooth edges

    # ---- Prepare background ----
    if bg_image_path and Path(bg_image_path).exists():
        bg = cv2.imread(str(bg_image_path))
        if bg is not None:
            bg = cv2.resize(bg, (w, h))
        else:
            bg = np.full((h, w, 3), bgcolor, dtype=np.uint8)
    else:
        bg = np.full((h, w, 3), bgcolor, dtype=np.uint8)

    # ---- Blend with clipping ----
    matte_3 = np.repeat(matte[:, :, None], 3, axis=2)
    out = frame_bgr.astype(np.float32) * matte_3 + bg.astype(np.float32) * (1 - matte_3)
    out = np.clip(out, 0, 255).astype(np.uint8)

    return out

@torch.inference_mode()
def apply_modnet_cutout_rgba(frame_bgr):
    """
    Return an RGBA image (numpy uint8 HxWx4) where the alpha channel is the MODNet matte.
    Background is transparent (no compositing).
    """
    h, w, _ = frame_bgr.shape

    # Preprocess (same as apply_modnet)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb).resize((512, 512))
    tensor_input = preprocess(im)               # torch.Tensor [3,512,512]
    x = tensor_input.unsqueeze(0).to(device)    # [1,3,512,512]

    # Inference
    _, _, matte = modnet(x, True)
    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
    matte = np.clip(matte, 0, 1)

    # Optional cleanup (soft denoise of weak alpha)
    matte = np.where(matte > 0.2, matte, 0)
    matte = cv2.GaussianBlur(matte, (5, 5), 0)

    # Build RGBA: use original RGB + alpha from matte
    rgb_u8 = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.uint8)
    alpha_u8 = (matte * 255).astype(np.uint8)
    rgba = np.dstack([rgb_u8, alpha_u8])  # H x W x 4, uint8

    return rgba

def apply_modnet_video(frame, mode="color", bgcolor=(255, 255, 255), bg_image=None):
    """
    Real-time MODNet processing for webcam/video.
    mode: "color", "custom", or "transparent"
    """
    alpha = run_modnet_video_inference(frame)  # grayscale mask (0–255)
    alpha_3 = cv2.merge([alpha, alpha, alpha]) / 255.0
    fg = frame.astype(np.float32) / 255.0
    h, w, _ = frame.shape

    if mode == "transparent":
        result = cv2.cvtColor((fg * alpha_3 * 255).astype(np.uint8), cv2.COLOR_BGR2BGRA)
        result[:, :, 3] = alpha
        return result

    elif mode == "custom" and bg_image is not None:
        bg_resized = cv2.resize(bg_image, (w, h))
        bg = bg_resized.astype(np.float32) / 255.0
        result = (fg * alpha_3 + bg * (1 - alpha_3)) * 255
        return result.astype(np.uint8)

    else:  # default solid color
        bg = np.full_like(frame, bgcolor, dtype=np.uint8).astype(np.float32) / 255.0
        result = (fg * alpha_3 + bg * (1 - alpha_3)) * 255
        return result.astype(np.uint8)


def run_modnet_video_inference(frame):
    """
    Stub for MODNet video inference.
    Replace with your real model inference.
    """
    h, w, _ = frame.shape
    # Dummy alpha mask for testing
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[h//4:h*3//4, w//4:w*3//4] = 255
    return mask

