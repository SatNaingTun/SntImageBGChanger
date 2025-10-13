document.addEventListener("DOMContentLoaded", () => {
  const output = document.getElementById("output");
  const recordCanvas = document.getElementById("recordCanvas");
  const recordBtn = document.getElementById("recordBtn");
  const stopRecordBtn = document.getElementById("stopRecordBtn");
  const startBtn = document.getElementById("startBtn"); // webcam control

  let mediaRecorder = null;
  let recordedChunks = [];
  let recording = false;
  let drawLoopActive = false;

  // 🎬 Start recording processed output
  recordBtn.addEventListener("click", () => {
    if (!output.src || output.src.includes("black")) {
      showToast("⚠️ Start the webcam before recording!");
      return;
    }

    recording = true;
    recordedChunks = [];

    const ctx = recordCanvas.getContext("2d");
    recordCanvas.width = output.width || 480;
    recordCanvas.height = output.height || 360;

    const stream = recordCanvas.captureStream(15); // ~15 FPS
    mediaRecorder = new MediaRecorder(stream, { mimeType: "video/webm" });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = saveRecording;

    mediaRecorder.start();
    drawLoopActive = true;
    drawLoop(ctx);

    recordBtn.style.display = "none";
    stopRecordBtn.style.display = "inline-block";

    showToast("🎥 Recording started...");
  });

  // ⏹ Stop recording manually
  stopRecordBtn.addEventListener("click", () => {
    stopRecording();
  });

  // 🧠 Stop recording automatically when webcam stops
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      const isStopping = startBtn.textContent.includes("Start Webcam");
      if (isStopping && recording) {
        stopRecording();
      }
    });
  }

  // 💾 Stop recording logic
  function stopRecording() {
    if (!recording) return;
    recording = false;
    drawLoopActive = false;

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }

    recordBtn.style.display = "inline-block";
    stopRecordBtn.style.display = "none";

    showToast("🛑 Recording stopped.");
  }

  // 🔁 Draw loop for recording
  function drawLoop(ctx) {
    if (!drawLoopActive) return;
    ctx.drawImage(output, 0, 0, recordCanvas.width, recordCanvas.height);
    requestAnimationFrame(() => drawLoop(ctx));
  }

  // 💾 Upload video
  async function saveRecording() {
    const blob = new Blob(recordedChunks, { type: "video/webm" });
    const formData = new FormData();
    formData.append("video", blob, `modnet_recorded_${Date.now()}.webm`);

    try {
      const res = await fetch("/api/record/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.video_path) {
        showToast("✅ Recording saved!");
        console.log("📦 Uploaded:", data);
      } else {
        showToast("⚠️ Upload failed: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      showToast("❌ Upload failed: " + err.message);
    }
  }

  // 🌟 Toast popup
  function showToast(message) {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.position = "fixed";
    toast.style.bottom = "20px";
    toast.style.right = "20px";
    toast.style.background = "#333";
    toast.style.color = "#fff";
    toast.style.padding = "10px 16px";
    toast.style.borderRadius = "8px";
    toast.style.fontSize = "0.9rem";
    toast.style.zIndex = "9999";
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";

    document.body.appendChild(toast);
    setTimeout(() => (toast.style.opacity = "1"), 50);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }
  // 📸 Take Snapshot of processed output
  const snapshotBtn = document.getElementById("snapshotBtn");
  snapshotBtn.addEventListener("click", () => {
    const output = document.getElementById("output");
    if (!output.src || output.src.includes("black")) {
      showToast("⚠️ Start webcam to take a snapshot!");
      return;
    }

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = output.width || 480;
    canvas.height = output.height || 360;

    // Draw the processed output image
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = output.src;

    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const link = document.createElement("a");
      link.download = `snapshot_${Date.now()}.jpg`;
      link.href = canvas.toDataURL("image/jpeg");
      link.click();
      showToast("📸 Snapshot saved!");
    };
  });
});
