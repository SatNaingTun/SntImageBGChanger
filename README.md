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
git clone https://github.com/SatNaingTun/SntImageBGChanger.git
```
```
cd SntImageBGChanger
pip install -r requirements.txt

```
### Option 2: NVIDIA GPU (CUDA) Installation
If you have an NVIDIA graphics card and want hardware-accelerated background removal, install the core requirements first, then apply the optional GPU extensions:

```
pip install -r requirements.txt
pip install -r requirements-gpu.txt
```

## Running with Docker
You can run the pre-built container image from either Docker Hub or GitHub Container Registry (GHCR) without managing local Python dependencies.

### From Docker Hub:

```
docker pull satnaingtun/imagebgchanger:latest
docker run -p 8000:8000 satnaingtun/imagebgchanger:latest

```
###  From GitHub Container Registry (GHCR):
```
docker pull ghcr.io/satnaingtun/sntimagebgchanger:latest
docker run -p 8000:8000 ghcr.io/satnaingtun/sntimagebgchanger:latest
```

## Running Locally from Source
To run the FastAPI server directly for local development:

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```