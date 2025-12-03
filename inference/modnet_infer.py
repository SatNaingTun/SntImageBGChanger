import subprocess
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
ROOT = Path(__file__).resolve().parent.parent
THIRDPARTY_DIR = ROOT / "thirdparty"
MODNET_PATH = THIRDPARTY_DIR / "MODNet" / "src"

# Auto clone MODNet if missing
if not MODNET_PATH.exists():
    print(f"⚠️ MODNet not found at {MODNET_PATH}. Cloning repository...")
    os.makedirs(THIRDPARTY_DIR, exist_ok=True)
    repo_url = "https://github.com/ZHKKKe/MODNet.git"
    try:
        subprocess.run(
            ["git", "clone", repo_url, str(THIRDPARTY_DIR / "MODNet")],
            check=True
        )
        print("✅ MODNet successfully cloned.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"❌ Failed to clone MODNet: {e}")

# Add MODNet src to sys.path
if str(MODNET_PATH) not in sys.path:
    sys.path.append(str(MODNET_PATH))

# Try import
try:
    from models.modnet import MODNet
    print("✅ MODNet imported successfully.")
except ModuleNotFoundError as e:
    raise ImportError(f"❌ Could not import MODNet. Check path: {MODNET_PATH}\n{e}")

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🧠 Using device: {device}")

# -------------------------------------------------------
# Load your fine-tuned checkpoint
# -------------------------------------------------------
model_name = "modnet_finetuned_photographic.ckpt"
CKPT_PATH = ROOT / "weights" / model_name

modnet = MODNet(backbone_pretrained=False).to(device)

print(f"Loading Image Model from: {CKPT_PATH}")
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

@torch.inference_mode()
def extract_background(frame_bgr):
    """
    Extract only the background part of the image using MODNet matte.
    Returns a BGR image where foreground is blacked out.
    """
    h, w, _ = frame_bgr.shape
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb).resize((512, 512))
    tensor_input = preprocess(im).unsqueeze(0).to(device)

    _, _, matte = modnet(tensor_input, True)
    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
    matte = np.clip(matte, 0, 1)

    # Background = inverse matte
    bg_mask = 1 - matte
    bg_mask = np.repeat(bg_mask[:, :, None], 3, axis=2)
    background = (frame_bgr.astype(np.float32) * bg_mask).astype(np.uint8)
    return background


@torch.inference_mode()
def apply_modnet_blur_background(frame_bgr, blur_strength=35):
    """
    Keep the person/foreground sharp, blur only the background region.
    Uses MODNet matte to isolate foreground from background.
    """
    h, w, _ = frame_bgr.shape
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb).resize((512, 512))
    tensor_input = preprocess(im).unsqueeze(0).to(device)

    _, _, matte = modnet(tensor_input, True)
    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
    matte = np.clip(matte, 0, 1)
    
    # Smooth matte edges for better blending
    matte = cv2.GaussianBlur(matte, (5, 5), 0)

    # Ensure blur strength is odd number for cv2.GaussianBlur
    blur_k = int(blur_strength)
    if blur_k % 2 == 0:
        blur_k += 1
    blur_k = max(3, blur_k)  # minimum kernel size

    # Create blurred background
    blurred_bg = cv2.GaussianBlur(frame_bgr, (blur_k, blur_k), 0)

    # Matte: 1.0 = foreground (keep original), 0.0 = background (use blurred)
    # Expand matte to 3 channels for blending
    matte_3 = np.repeat(matte[:, :, None], 3, axis=2)

    # Blend: foreground stays sharp, background gets blurred
    out = frame_bgr.astype(np.float32) * matte_3 + blurred_bg.astype(np.float32) * (1 - matte_3)
    out = np.clip(out, 0, 255).astype(np.uint8)
    
    return out

if __name__ == "__main__":
    input_path = "./images/upload/Sat Naing Tun bg changed.jpg"
    output_path = "./images/changed/Sat Naing Tun blur only.png"

    frame_bgr = cv2.imread(input_path)
    if frame_bgr is None:
        raise FileNotFoundError(f"❌ Could not read image: {input_path}")
    # print("Extracting background only...")
    # background = extract_background(frame_bgr)
    output=apply_modnet_blur_background(frame_bgr, blur_strength=35)
    cv2.imwrite(output_path, output)
