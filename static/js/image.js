// image.js
document.addEventListener("DOMContentLoaded", () => {
  // ===== DOM Elements =====
  const modeSelect = document.getElementById("modeSelect");
  const colorField = document.getElementById("colorField");
  const bgUploadField = document.getElementById("bgUploadField");
  const form = document.getElementById("uploadForm");
  const loading = document.getElementById("loading");
  const previewSection = document.getElementById("previewSection");
  const resultPreview = document.getElementById("resultPreview");
  const originalPreview = document.getElementById("originalPreview");
  const downloadLink = document.getElementById("downloadLink");
  const buttons = document.getElementById("buttons");
  const resetBtn = document.getElementById("resetBtn");
  const fileInput = document.getElementById("fileInput");

  const inputOptions = document.querySelectorAll("input[name='inputOption']");
  const uploadSection = document.getElementById("uploadSection");
  const cameraSection = document.getElementById("cameraSection");
  const toggleCameraBtn = document.getElementById("toggleCameraBtn");
  const cameraContainer = document.getElementById("cameraContainer");
  const canvas = document.getElementById("cameraCanvas");
  const canvasWrapper = document.getElementById("canvasWrapper");
  const captureBtn = document.getElementById("captureBtn");

  // ===== Camera State =====
  let camera = null;
  let cameraActive = false;

  // ===== Helper: Canvas Visibility =====
  function showCanvas() {
    if (canvasWrapper) {
      canvasWrapper.classList.add("show");
      canvasWrapper.classList.remove("hidden");
    }
  }

  function hideCanvas() {
    if (canvasWrapper) {
      canvasWrapper.classList.remove("show");
      canvasWrapper.classList.add("hidden");
    }
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

  // ===== Mode (color/custom/transparent) =====
  function toggleFields() {
    const mode = modeSelect.value;
    colorField.style.display = mode === "color" ? "flex" : "none";
    bgUploadField.style.display = mode === "custom" ? "flex" : "none";
  }
  modeSelect.addEventListener("change", toggleFields);
  toggleFields();

  // ===== Form Submit Handler =====
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return alert("Please choose or capture an image first.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", modeSelect.value);
    formData.append("color", document.getElementById("colorPicker").value);

    const bgFile = document.getElementById("bg_file").files[0];
    if (bgFile) formData.append("bg_file", bgFile);

    originalPreview.src = URL.createObjectURL(file);
    previewSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    previewSection.style.opacity = "0.5";
    buttons.classList.add("hidden");

    try {
      const res = await fetch("/api/image/process", { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      await new Promise((r) => setTimeout(r, 300));
      const ts = "?t=" + Date.now();
      originalPreview.src = data.original + ts;
      resultPreview.src = data.result + ts;

      downloadLink.dataset.downloadUrl = data.download;
      downloadLink.dataset.filename = data.download.split("/").pop();

      previewSection.style.opacity = "1";
      buttons.classList.remove("hidden");
    } catch (err) {
      alert("❌ Error: " + err.message);
      console.error(err);
    } finally {
      loading.classList.add("hidden");
    }
  });

  // ===== Download Button =====
  downloadLink.addEventListener("click", async (e) => {
    e.preventDefault();
    const url = downloadLink.dataset.downloadUrl;
    const filename = downloadLink.dataset.filename || "changed_image.jpg";
    if (!url) return alert("No file available for download.");

    try {
      const res = await fetch(url + "?t=" + Date.now());
      const blob = await res.blob();
      const a = document.createElement("a");
      const objectUrl = URL.createObjectURL(blob);
      a.href = objectUrl;
      a.download = filename;
      a.style.display = "none";
      document.body.appendChild(a);
      setTimeout(() => {
        a.click();
        URL.revokeObjectURL(objectUrl);
        a.remove();
      }, 0);
    } catch (err) {
      console.error("❌ Download failed:", err);
      alert("Failed to download image.");
    }
  });

  // ===== Reset Button =====
  resetBtn.addEventListener("click", async () => {
    form.reset();
    previewSection.classList.add("hidden");
    buttons.classList.add("hidden");
    toggleFields();
    hideCanvas();

    // Stop camera if running
    if (cameraActive && camera) {
      await camera.stop();
      cameraActive = false;
    }
    if (cameraContainer) cameraContainer.classList.add("hidden");
    const videoEl = document.getElementById("cameraPreview");
    if (videoEl) videoEl.style.visibility = "hidden";
    toggleCameraBtn.textContent = "📷 Start Camera";
    toggleCameraBtn.style.background = "#6c757d";
    camera = null;
  });

  // ===== Upload / Camera Toggle =====
  inputOptions.forEach(opt => {
    opt.addEventListener("change", async () => {
      if (opt.value === "upload" && opt.checked) {
        // Show upload, hide camera
        uploadSection.classList.remove("hidden");
        cameraSection.classList.add("hidden");
        hideCanvas();

        // ✅ Stop camera automatically if running
        if (cameraActive && camera) {
          await camera.stop();
          cameraActive = false;
          cameraContainer.classList.add("hidden");
          const videoEl = document.getElementById("cameraPreview");
          if (videoEl) videoEl.style.visibility = "hidden";
          toggleCameraBtn.textContent = "📷 Start Camera";
          toggleCameraBtn.style.background = "#6c757d";
          camera = null;
        }
      } else if (opt.value === "camera" && opt.checked) {
        // Show camera section
        uploadSection.classList.add("hidden");
        cameraSection.classList.remove("hidden");
        hideCanvas();
      }
    });
  });

  // ===== Camera Start/Stop Button =====
  toggleCameraBtn.addEventListener("click", async () => {
    const videoEl = document.getElementById("cameraPreview");
    if (!videoEl) {
      alert("Camera element not ready yet. Please reload the page.");
      console.error("cameraPreview not found in DOM.");
      return;
    }

    // Let browser render before starting camera
    await new Promise(requestAnimationFrame);

    if (!cameraActive) {
      cameraContainer.classList.remove("hidden");
      videoEl.style.visibility = "visible";
      await new Promise(requestAnimationFrame); // second frame for layout

      if (!camera) {
        camera = new window.CameraController(
          videoEl,
          new window.CameraSettings({ facing: "user", width: 640, height: 480 })
        );
      }

      try {
        await camera.start();
        cameraActive = true;
        toggleCameraBtn.textContent = "❌ Stop Camera";
        toggleCameraBtn.style.background = "#dc3545";
      } catch (err) {
        console.error("Failed to start camera:", err);
        alert("Could not start camera. Please check permissions.");
        camera = null;
        cameraActive = false;
      }
    } else {
      if (camera) await camera.stop();
      cameraContainer.classList.add("hidden");
      videoEl.style.visibility = "hidden";
      cameraActive = false;
      toggleCameraBtn.textContent = "📷 Start Camera";
      toggleCameraBtn.style.background = "#6c757d";
      hideCanvas();
      camera = null;
    }
  });

  // ===== Capture Photo =====
  captureBtn.addEventListener("click", () => {
    const videoEl = document.getElementById("cameraPreview");
    if (!videoEl || !videoEl.srcObject) {
      alert("Camera not active!");
      return;
    }

    const ctx = canvas.getContext("2d");
    canvas.width = videoEl.videoWidth || 320;
    canvas.height = videoEl.videoHeight || 240;
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const file = new File([blob], "camera_capture.jpg", { type: "image/jpeg" });
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;

      const imageURL = URL.createObjectURL(file);
      drawToCanvas(imageURL);
      alert("✅ Photo captured and ready to process!");
    }, "image/jpeg");
  });

  // ===== Draw Image to Canvas =====
  function drawToCanvas(imageSource) {
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      const card = document.querySelector(".card");
      const maxW = card ? card.clientWidth * 0.85 : 800;
      const maxH = window.innerHeight * 0.6;
      let { width, height } = img;

      const scale = Math.min(maxW / width, maxH / height, 1);
      width *= scale;
      height *= scale;

      canvas.width = width;
      canvas.height = height;
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);
      showCanvas();

      if (originalPreview) originalPreview.src = canvas.toDataURL("image/jpeg");
    };
    img.src = imageSource;
  }

  // ===== File Upload → Draw to Canvas =====
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const imageURL = URL.createObjectURL(file);
      drawToCanvas(imageURL);
    } else {
      hideCanvas();
    }
  });

  // ===== Auto Stop Camera When Leaving Page =====
  window.addEventListener("beforeunload", () => {
    if (camera) camera.stop();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && camera) camera.stop();
  });
});
