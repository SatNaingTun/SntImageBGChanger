// camera.js
// CameraSettings and CameraController classes + wiring
class CameraSettings {
  constructor({ facing = "user", width = 640, height = 480, frameRate = 30, torch = false } = {}) {
    this.facing = facing;
    this.width = width;
    this.height = height;
    this.frameRate = frameRate;
    this.torch = torch;
    this.deviceId = null;
  }

  toMediaConstraints() {
    const video = this.deviceId
      ? { deviceId: { exact: this.deviceId } }
      : { facingMode: this.facing };

    video.width = { ideal: this.width };
    video.height = { ideal: this.height };
    video.frameRate = { ideal: this.frameRate };

    return { video, audio: false };
  }

  setResolution(w, h) { this.width = w; this.height = h; }
  setFrameRate(fps) { this.frameRate = fps; }
  setFacing(f) { this.facing = f; this.deviceId = null; }
  setTorch(on) { this.torch = !!on; }
}

class CameraController {
  constructor(videoEl, settings = new CameraSettings()) {
    this.videoEl = videoEl;
    this.settings = settings;
    this.stream = null;
    this.devices = [];
  }

  async ensureDevices() {
    // We'll refresh device list
    const list = await navigator.mediaDevices.enumerateDevices();
    this.devices = list.filter(d => d.kind === "videoinput");
  }

  async pickDeviceIdForFacing() {
    if (!this.devices.length) await this.ensureDevices();
    const wantFront = this.settings.facing === "user";
    const match = this.devices.find(d => {
      const label = (d.label || "").toLowerCase();
      return wantFront ? (label.includes("front") || label.includes("user")) :
                         (label.includes("back") || label.includes("rear") || label.includes("environment"));
    });
    if (match) this.settings.deviceId = match.deviceId;
  }

  async start() {
    await this.stop();
    // get devices and try to pick deviceId if possible
    try {
      await this.ensureDevices();
      if (!this.settings.deviceId) await this.pickDeviceIdForFacing();
    } catch (e) {
      // ignore - enumerateDevices may need a prior permission
    }

    const constraints = this.settings.toMediaConstraints();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoEl.srcObject = this.stream;

      // if torch requested, attempt to set (best-effort)
      if (this.settings.torch) {
        this.tryTorch(true).catch(()=>{});
      }
    } catch (err) {
      console.error("getUserMedia error:", err);
      alert("Camera error: " + (err.message || err.name));
    }
  }

  async stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.videoEl.srcObject = null;
      this.stream = null;
    }
  }

  async switchCamera() {
    this.settings.facing = this.settings.facing === "user" ? "environment" : "user";
    this.settings.deviceId = null;
    return this.start();
  }

  async applySettings() {
    if (!this.stream) return this.start();

    const track = this.stream.getVideoTracks()[0];
    if (!track) return this.start();

    const capabilities = track.getCapabilities ? track.getCapabilities() : {};
    const constraints = {};

    if (capabilities.width)  constraints.width = this.settings.width;
    if (capabilities.height) constraints.height = this.settings.height;
    if (capabilities.frameRate) constraints.frameRate = this.settings.frameRate;

    try {
      await track.applyConstraints(constraints);
    } catch (err) {
      // If granular apply fails, restart with new constraints
      await this.start();
    }

    if (typeof this.settings.torch === "boolean") {
      this.tryTorch(this.settings.torch).catch(()=>{});
    }
  }

  async tryTorch(on) {
    // Best-effort to enable torch on supporting devices
    const track = this.stream?.getVideoTracks?.()[0];
    if (!track) return;
    try {
      const cap = track.getCapabilities?.() || {};
      if (cap.torch) {
        await track.applyConstraints({ advanced: [{ torch: !!on }] });
        return;
      }
    } catch (e) {
      // ignore
    }

    // Fallback: some devices require ImageCapture (not widely available)
    if (window.ImageCapture) {
      try {
        const imageCapture = new ImageCapture(track);
        const photoCapabilities = await imageCapture.getPhotoCapabilities();
        if (photoCapabilities.torch) {
          await track.applyConstraints({ advanced: [{ torch: !!on }] });
        }
      } catch (e) { /* ignore */ }
    }
  }
}

// Wiring: element lookup and event handlers
const video = document.getElementById("preview");
const btnStart = document.getElementById("btnStart");
const btnSwitch = document.getElementById("btnSwitch");
const btnStop = document.getElementById("btnStop");
const selRes = document.getElementById("selRes");
const inpFps = document.getElementById("inpFps");
const selTorch = document.getElementById("selTorch");
const btnApply = document.getElementById("btnApply");

const settings = new CameraSettings({ facing: "user", width: 640, height: 480, frameRate: 30, torch: false });
const cam = new CameraController(video, settings);

window.addEventListener("load", () => {
  // Auto-start selfie when possible; browsers may block autoplay without gesture -> user can press Start
  cam.start().catch(err => console.debug("autostart failed:", err));
});

btnStart.addEventListener("click", () => cam.start());
btnSwitch.addEventListener("click", () => cam.switchCamera());
btnStop.addEventListener("click", () => cam.stop());
btnApply.addEventListener("click", () => {
  const [w,h] = selRes.value.split("x").map(Number);
  const fps = parseInt(inpFps.value || "30", 10);
  const torchOn = selTorch.value === "on";
  settings.setResolution(w,h);
  settings.setFrameRate(fps);
  settings.setTorch(torchOn);
  cam.applySettings();
});
