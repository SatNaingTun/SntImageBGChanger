document.addEventListener("DOMContentLoaded", () => {
  const output = document.getElementById("output");
  const recordCanvas = document.getElementById("recordCanvas");
  const recordBtn = document.getElementById("recordBtn");
  const stopRecordBtn = document.getElementById("stopRecordBtn");

  let mediaRecorder = null;
  let recordedChunks = [];
  let recording = false;

  // 🎬 Start recording processed output
  recordBtn.addEventListener("click", () => {
    if (!output.src || output.src.includes("black")) {
      alert("Start the webcam first before recording!");
      return;
    }

    recording = true;
    recordedChunks = [];

    const ctx = recordCanvas.getContext("2d");
    recordCanvas.width = output.width || 480;
    recordCanvas.height = output.height || 360;

    const stream = recordCanvas.captureStream(15); // 15 FPS capture
    mediaRecorder = new MediaRecorder(stream, { mimeType: "video/webm" });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = saveRecording;

    mediaRecorder.start();
    recordBtn.style.display = "none";
    stopRecordBtn.style.display = "inline-block";

    console.log("🎥 Recording started...");
    drawLoop(ctx);
  });

  // ⏹ Stop recording
  stopRecordBtn.addEventListener("click", () => {
    recording = false;

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }

    recordBtn.style.display = "inline-block";
    stopRecordBtn.style.display = "none";

    console.log("🛑 Recording stopped.");
  });

  // 🔁 Continuously draw processed output onto canvas
  function drawLoop(ctx) {
    if (!recording) return;
    ctx.drawImage(output, 0, 0, recordCanvas.width, recordCanvas.height);
    requestAnimationFrame(() => drawLoop(ctx));
  }

  // 💾 Upload to backend and confirm
  async function saveRecording() {
    const blob = new Blob(recordedChunks, { type: "video/webm" });
    const formData = new FormData();
    formData.append("video", blob, `modnet_recorded_${Date.now()}.webm`);

    console.log("📤 Uploading recording...");

    try {
      const res = await fetch("/api/record/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("📦 Upload response:", data);

      if (res.ok && data.video_path) {
        showToast("✅ Recording saved successfully!");
        console.log("🎞 Video:", data.video_path);
        console.log("🖼 Thumbnail:", data.thumbnail_path);
        console.log("⬇ Download:", data.download_link);
      } else {
        showToast("⚠️ Upload failed: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      console.error("❌ Upload failed:", err);
      showToast("❌ Upload failed: " + err.message);
    }
  }

  // 🌟 Toast Notification (small popup at bottom)
  function showToast(message) {
    let toast = document.createElement("div");
    toast.textContent = message;
    toast.style.position = "fixed";
    toast.style.bottom = "25px";
    toast.style.right = "25px";
    toast.style.background = "#333";
    toast.style.color = "#fff";
    toast.style.padding = "10px 16px";
    toast.style.borderRadius = "8px";
    toast.style.fontSize = "0.9rem";
    toast.style.zIndex = "9999";
    toast.style.boxShadow = "0 2px 10px rgba(0,0,0,0.3)";
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";

    document.body.appendChild(toast);

    setTimeout(() => (toast.style.opacity = "1"), 50);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }
});
