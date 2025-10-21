# ==========================================
# modnet_infer_video.py
# ==========================================
import time
import subprocess
import sys
import cv2
import numpy as np
import torch
from pathlib import Path
from progress import start_progress, set_progress, complete_progress, fail_progress


from tqdm import tqdm

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
webcam_model_name = "modnet_finetuned_photographic.ckpt"
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

# =====================================================
# 🎬 Apply MODNet on full video using MoviePy
# =====================================================
def apply_modnet_video_file(input_path, output_path, mode="color", color="#00ff00", bg_path=None,progress_file=None):
    """
    Process a full video with MODNet using MoviePy for writing.
    This version does not require an external FFmpeg installation.
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

    # Background setup
    bg_image = None
    if mode == "custom" and bg_path:
        bg_image = cv2.imread(str(bg_path))
        if bg_image is not None:
            bg_image = cv2.resize(bg_image, (w, h))
        else:
            print(f"⚠️ Could not read background image: {bg_path}")

    bgcolor = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"🎞 Processing {frame_count} frames from {input_path}")

    frames = []
    start_time = time.time()
    if progress_file:
        start_progress(progress_file, "processing")

    for idx in tqdm(range(frame_count), desc="Processing frames", ncols=80):
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        try:
            result = apply_modnet_video(frame, mode=mode, bgcolor=bgcolor, bg_image=bg_image)
            # Convert from BGR to RGB for MoviePy
            frames.append(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        except Exception as e:
            print(f"⚠️ Frame {idx} error: {e}")
        # idx += 1
        set_progress(progress_file, idx + 1, frame_count, "processing")

    cap.release()

    if not frames:
        fail_progress(progress_file)
        print("❌ No frames processed.")
        return False

    # =====================================================
    # Write using MoviePy (pure Python, no external FFmpeg)
    # =====================================================
    try:
        clip = ImageSequenceClip(frames, fps=fps)
        clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio=False,
            preset="medium",
            ffmpeg_params=["-movflags", "+faststart"]
        )
        complete_progress(progress_file)
        print(f"✅ Saved processed video: {output_path} ({time.time() - start_time:.2f}s)")
        return True
    except Exception as e:
        fail_progress(progress_file)
        print(f"❌ Error writing video with MoviePy: {e}")
        return False


