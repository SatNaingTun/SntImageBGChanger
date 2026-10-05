# BackgroundChanger

A high-performance FastAPI application for AI-powered background removal and replacement utilizing MODNet inference.

---

## 🚀 Features
* Fast and lightweight FastAPI backend.
* Accurate background segmentation and removal via MODNet.
* Containerized deployment support via GitHub Container Registry (GHCR).
* Flexible installation choices for CPU and NVIDIA GPU users.

---

## ⚙️ Installation Options

Choose the installation method that matches your hardware setup:

### Option 1: Standard CPU Installation (Recommended)
Fastest installation, lightweight, and works on any machine (Windows, macOS, or Linux) without a dedicated GPU:

```
git clone [https://github.com/SatNaingTun/SntImageBGChanger.git](https://github.com/SatNaingTun/SntImageBGChanger.git)
cd SntImageBGChanger
pip install -r requirements.txt
```

### Option 2: NVIDIA GPU (CUDA) Installation
If you have an NVIDIA graphics card and want hardware-accelerated background removal, install the core requirements first, then apply the optional GPU extensions:

```
pip install -r requirements.txt
pip install -r requirements-gpu.txt
```