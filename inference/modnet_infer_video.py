# ==========================================
# modnet_infer_video.py
# ==========================================
import os
import time
import subprocess
import sys
import cv2
import numpy as np
import torch
from pathlib import Path
from progress import start_progress, set_progress, complete_progress, fail_progress


from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent  # project root
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

# --------------------------------------------------
# 🔧 MODEL INITIALIZATION
# --------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

ROOT = Path(__file__).resolve().parent.parent
webcam_model_name = "modnet_finetuned_webcam.ckpt"
webcam_model_path = ROOT / "weights" / webcam_model_name

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

# ==============================
# 🔹 New: Blur Background Support
# ==============================
def apply_modnet_video_blur(frame, blur_strength=25):
    """Apply MODNet matting and blur only the background."""
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
    image = image.astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image.transpose(2, 0, 1)).unsqueeze(0).to(device)

    with torch.no_grad():
        _, _, matte = modnet_webcam(image_tensor, True)

    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
    matte = np.clip(matte, 0, 1)
    matte = cv2.GaussianBlur(matte, (5, 5), 0)  # smooth edges
    
    matte_3 = np.repeat(matte[:, :, np.newaxis], 3, axis=2)

    fg = frame.astype(np.float32) / 255.0
    
    # Ensure blur kernel is odd and valid
    blur_k = int(blur_strength)
    if blur_k % 2 == 0:
        blur_k += 1
    blur_k = max(3, blur_k)
    
    blurred_bg = cv2.GaussianBlur(fg, (blur_k, blur_k), 0)

    # matte=1.0 (foreground) → use original, matte=0.0 (background) → use blurred
    result = (fg * matte_3 + blurred_bg * (1 - matte_3)) * 255
    return result.astype(np.uint8)

# --------------------------------------------------
# 🧠 INFERENCE FUNCTION
# --------------------------------------------------
def apply_modnet_video(frame, mode="color", bgcolor=(255, 255, 255), bg_image=None, blur_strength=25):
    """
    Apply MODNet portrait matting for webcam frames.
    mode: 'color', 'custom', 'transparent', 'blur'
    """
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
    image = image.astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image.transpose(2, 0, 1)).unsqueeze(0).to(device)

    with torch.no_grad():
        _, _, matte = modnet_webcam(image_tensor, True)
    
    matte = matte[0][0].cpu().numpy()
    matte = cv2.resize(matte, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
    matte = np.clip(matte, 0, 1)
    matte = cv2.GaussianBlur(matte, (5, 5), 0)  # smooth edges
    
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
    
    elif mode == "blur":
        # Ensure blur kernel is odd and valid
        blur_k = int(blur_strength)
        if blur_k % 2 == 0:
            blur_k += 1
        blur_k = max(3, blur_k)
        
        blurred_bg = cv2.GaussianBlur(fg, (blur_k, blur_k), 0)
        # matte=1.0 (foreground sharp), matte=0.0 (background blurred)
        result = (fg * matte_3 + blurred_bg * (1 - matte_3)) * 255
        return result.astype(np.uint8)

    else:  # solid color background
        bg = np.full_like(frame, bgcolor, dtype=np.uint8).astype(np.float32) / 255.0
        result = (fg * matte_3 + bg * (1 - matte_3)) * 255
        return result.astype(np.uint8)

# =====================================================
# 🎬 Apply MODNet on full video using MoviePy
# =====================================================
def apply_modnet_video_file(input_path, output_path, mode="color", color="#00ff00", bg_path=None, progress_file=None, blur_strength=25):
    """
    Process full video with MODNet.
    Supports image or video backgrounds.
    If background video is shorter → loops.
    If background video is longer → stops at foreground end.
    """

    from moviepy import ImageSequenceClip
    from modnet_infer_video import apply_modnet_video

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"❌ Cannot open video: {input_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"🎞 Processing {frame_count} frames from {input_path}")

    # -----------------------------------------------------
    # 🔹 Background setup
    # -----------------------------------------------------
    bg_image = None
    bg_cap = None
    bg_is_video = False

    if mode == "custom" and bg_path:
        ext = Path(bg_path).suffix.lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv"]:
            bg_cap = cv2.VideoCapture(str(bg_path))
            if bg_cap.isOpened():
                bg_is_video = True
                bg_frame_count = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                print(f"🎥 Background video loaded ({bg_frame_count} frames)")
            else:
                print(f"⚠️ Could not open background video: {bg_path}")
        else:
            bg_image = cv2.imread(str(bg_path))
            if bg_image is not None:
                bg_image = cv2.resize(bg_image, (w, h))
            else:
                print(f"⚠️ Could not read background image: {bg_path}")

    bgcolor = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    frames = []

    if progress_file:
        start_progress(progress_file, "processing")

    # -----------------------------------------------------
    # 🎬 Frame-by-frame MODNet inference
    # -----------------------------------------------------
    for idx in tqdm(range(frame_count), desc="Processing frames", ncols=80):
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        # ----- Background frame logic -----
        current_bg = None
        if bg_is_video:
            ret_bg, bg_frame = bg_cap.read()
            if not ret_bg:  # Loop back to start if shorter
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_bg, bg_frame = bg_cap.read()
            if ret_bg:
                current_bg = cv2.resize(bg_frame, (w, h))
        elif bg_image is not None:
            current_bg = bg_image

        # ----- MODNet processing -----
        try:
            result = apply_modnet_video(frame, mode=mode, bgcolor=bgcolor, bg_image=current_bg, blur_strength=blur_strength)
            frames.append(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        except Exception as e:
            print(f"⚠️ Frame {idx} error: {e}")

        set_progress(progress_file, idx + 1, frame_count, "processing")

    cap.release()
    if bg_cap: bg_cap.release()

    # -----------------------------------------------------
    # 🧩 Write video
    # -----------------------------------------------------
    if not frames:
        fail_progress(progress_file)
        print("❌ No frames processed.")
        return False

    try:
        clip = ImageSequenceClip(frames, fps=fps)
        clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio=False,
            preset="medium",
            ffmpeg_params=["-movflags", "+faststart"]
        )
        print(f"✅ Saved processed video: {output_path}")
        complete_progress(progress_file)
        return True
    except Exception as e:
        fail_progress(progress_file)
        print(f"❌ Error writing video: {e}")
        return False



