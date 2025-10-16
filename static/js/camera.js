// camera.js
// Defines CameraSettings and CameraController classes only.
// No auto-starting behavior or DOM binding on page load.

class CameraSettings {
  constructor({
    facing = "user",
    width = 640,
    height = 480,
    frameRate = 30,
    torch = false
  } = {}) {
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

  setResolution(w, h) {
    this.width = w;
    this.height = h;
  }

  setFrameRate(fps) {
    this.frameRate = fps;
  }

  setFacing(f) {
    this.facing = f;
    this.deviceId = null;
  }

  setTorch(on) {
    this.torch = !!on;
  }
}

class CameraController {
  constructor(videoEl, settings = new CameraSettings()) {
    this.videoEl = videoEl;
    this.settings = settings;
    this.stream = null;
    this.devices = [];

    if (!this.videoEl) {
      console.warn("CameraController: video element is null!");
    }
  }

  async ensureDevices() {
    try {
      const list = await navigator.mediaDevices.enumerateDevices();
      this.devices = list.filter((d) => d.kind === "videoinput");
    } catch (err) {
      console.warn("Failed to enumerate devices:", err);
      this.devices = [];
    }
  }

  async pickDeviceIdForFacing() {
    if (!this.devices.length) await this.ensureDevices();
    const wantFront = this.settings.facing === "user";

    const match = this.devices.find((d) => {
      const label = (d.label || "").toLowerCase();
      return wantFront
        ? label.includes("front") || label.includes("user")
        : label.includes("back") || label.includes("rear") || label.includes("environment");
    });

    if (match) {
      this.settings.deviceId = match.deviceId;
    }
  }

  async start() {
    await this.stop(); // Always stop before starting new stream

    try {
      await this.ensureDevices();
      if (!this.settings.deviceId) await this.pickDeviceIdForFacing();
    } catch (e) {
      console.warn("Device enumeration failed:", e);
    }

    const constraints = this.settings.toMediaConstraints();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);

      // ✅ Check video element availability and DOM presence
      if (this.videoEl && document.body.contains(this.videoEl)) {
        this.videoEl.srcObject = this.stream;
      } else {
        console.warn("Camera error: Video element not found in DOM.");
        this.stop();
        return;
      }

      // ✅ Optional torch handling
      if (this.settings.torch) {
        this.tryTorch(true).catch(() => {});
      }
    } catch (err) {
      console.error("getUserMedia error:", err);
      alert("Camera error: " + (err.message || err.name));
      this.stop();
    }
  }

  async stop() {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      if (this.videoEl) {
        this.videoEl.srcObject = null;
      }
      this.stream = null;
    }
  }

  async switchCamera() {
    this.settings.facing =
      this.settings.facing === "user" ? "environment" : "user";
    this.settings.deviceId = null;
    return this.start();
  }

  async applySettings() {
    if (!this.stream) return this.start();

    const track = this.stream.getVideoTracks()[0];
    if (!track) return this.start();

    const capabilities = track.getCapabilities ? track.getCapabilities() : {};
    const constraints = {};

    if (capabilities.width) constraints.width = this.settings.width;
    if (capabilities.height) constraints.height = this.settings.height;
    if (capabilities.frameRate)
      constraints.frameRate = this.settings.frameRate;

    try {
      await track.applyConstraints(constraints);
    } catch (err) {
      console.warn("applyConstraints failed, restarting camera:", err);
      await this.start();
    }

    if (typeof this.settings.torch === "boolean") {
      this.tryTorch(this.settings.torch).catch(() => {});
    }
  }

  async tryTorch(on) {
    const track = this.stream?.getVideoTracks?.()[0];
    if (!track) return;

    try {
      const cap = track.getCapabilities?.() || {};
      if (cap.torch) {
        await track.applyConstraints({ advanced: [{ torch: !!on }] });
        return;
      }
    } catch (e) {
      console.debug("Torch capability not supported via constraints:", e);
    }

    // Optional fallback for browsers supporting ImageCapture
    if (window.ImageCapture) {
      try {
        const imageCapture = new ImageCapture(track);
        const photoCapabilities = await imageCapture.getPhotoCapabilities();
        if (photoCapabilities.torch) {
          await track.applyConstraints({ advanced: [{ torch: !!on }] });
        }
      } catch (e) {
        console.debug("Torch not supported via ImageCapture:", e);
      }
    }
  }
}

// Export classes globally for use in image.js
window.CameraSettings = CameraSettings;
window.CameraController = CameraController;
