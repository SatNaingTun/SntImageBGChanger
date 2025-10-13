document.addEventListener("DOMContentLoaded", () => {
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

  // Show/hide fields based on mode selection
  function toggleFields() {
    const mode = modeSelect.value;
    colorField.style.display = mode === "color" ? "flex" : "none";
    bgUploadField.style.display = mode === "custom" ? "flex" : "none";
  }
  modeSelect.addEventListener("change", toggleFields);
  toggleFields();

  // Handle form submission (AJAX)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return alert("Please choose an image first.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", modeSelect.value);
    formData.append("color", document.getElementById("colorPicker").value);

    const bgFile = document.getElementById("bg_file").files[0];
    if (bgFile) formData.append("bg_file", bgFile);

    // Debug form data
    for (const [key, value] of formData.entries()) {
      console.log("⬆ sending:", key, value);
    }

    // Show local preview immediately (no waiting)
    originalPreview.src = URL.createObjectURL(file);
    previewSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    previewSection.style.opacity = "0.5";
    buttons.classList.add("hidden");

    try {
      // Send request to backend
      const res = await fetch("/api/image/process", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("⬇ response:", data);

      if (data.error) throw new Error(data.error);

      // Small delay to ensure FastAPI finished writing files
      await new Promise((r) => setTimeout(r, 300));

      // Force fresh fetch (avoid browser cache)
      const ts = "?t=" + new Date().getTime();
      originalPreview.src = data.original + ts;
      resultPreview.src = data.result + ts;

      // Store download URL for later
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

  // ✅ Download handler with Save File dialog
  downloadLink.addEventListener("click", async (e) => {
  e.preventDefault();

  const url = downloadLink.dataset.downloadUrl;
  const filename = downloadLink.dataset.filename || "changed_image.jpg";
  if (!url) return alert("No file available for download.");

  try {
    // Step 1: fetch the image blob BEFORE user click finishes
    const res = await fetch(url + "?t=" + Date.now());
    const blob = await res.blob();

    // Step 2: Immediately create a download link (still within click event)
    const a = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    a.href = objectUrl;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);

    // Force synchronous download trigger (browser safe)
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

// Reset form
  resetBtn.addEventListener("click", () => {
    form.reset();
    previewSection.classList.add("hidden");
    buttons.classList.add("hidden");
    toggleFields();
  });

  const inputOptions = document.querySelectorAll("input[name='inputOption']");
  const uploadSection = document.getElementById("uploadSection");
  const cameraSection = document.getElementById("cameraSection");
  const toggleCameraBtn = document.getElementById("toggleCameraBtn");
  const cameraContainer = document.getElementById("cameraContainer");
  const video = document.getElementById("cameraPreview");
  const canvas = document.getElementById("cameraCanvas");
  const canvasWrapper = document.getElementById("canvasWrapper");
  const captureBtn = document.getElementById("captureBtn");

  let camera;
  let cameraActive = false;

  // Toggle between upload and camera
  inputOptions.forEach(opt => {
    opt.addEventListener("change", () => {
      if (opt.value === "upload" && opt.checked) {
        uploadSection.classList.remove("hidden");
        cameraSection.classList.add("hidden");
      } else if (opt.value === "camera" && opt.checked) {
        uploadSection.classList.add("hidden");
        cameraSection.classList.remove("hidden");
      }
    });
  });

  // Camera start/stop toggle
  toggleCameraBtn.addEventListener("click", async () => {
    if (!cameraActive) {
      cameraContainer.classList.remove("hidden");
      if (!camera) {
        if (!video) {
          console.error("Camera preview element not found");
          alert("Camera not available in this page.");
          return;
        }
        const settings = new CameraSettings({ facing: "user", width: 640, height: 480 });
        camera = new CameraController(video, settings);
      }
      try {
        await camera.start();
        cameraActive = true;
        toggleCameraBtn.textContent = "❌ Stop Camera";
        toggleCameraBtn.style.background = "#dc3545";
      } catch (err) {
        console.error("Failed to start camera:", err);
        alert("Could not start camera. Please check permissions.");
      }
    } else {
      if (camera) await camera.stop();
      cameraContainer.classList.add("hidden");
      cameraActive = false;
      toggleCameraBtn.textContent = "📷 Start Camera";
      toggleCameraBtn.style.background = "#6c757d";
    }
  });

  // Function to draw image (upload or capture)
  function drawToCanvas(imageSource) {
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvasWrapper.classList.remove("hidden");
      if (originalPreview) originalPreview.src = canvas.toDataURL("image/jpeg");
    };
    img.src = imageSource;
  }

  // Upload → draw to canvas
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const imageURL = URL.createObjectURL(file);
      drawToCanvas(imageURL);
    }
  });

  // Capture → draw to canvas
  captureBtn.addEventListener("click", () => {
    if (!video) {
      console.error("No video element for capture");
      return;
    }
    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 240;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

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
});
