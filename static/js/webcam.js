document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const output = document.getElementById("output");
  const startBtn = document.getElementById("startBtn");
  const modeSelect = document.getElementById("modeSelect");
  const colorPicker = document.getElementById("colorPicker");
  const bgFileInput = document.getElementById("bg_file");

  let streaming = false;
  let intervalId = null;

  // 🎥 Start / Stop webcam
  startBtn.addEventListener("click", async () => {
    if (!streaming) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        streaming = true;
        startBtn.textContent = "Stop Webcam";
        console.log("✅ Webcam started.");
        // Run every 500ms (≈2 FPS) for testing stability
        intervalId = setInterval(processFrame, 500);
      } catch (err) {
        alert("Webcam access denied: " + err.message);
      }
    } else {
      const tracks = video.srcObject?.getTracks() || [];
      tracks.forEach((t) => t.stop());
      streaming = false;
      startBtn.textContent = "Start Webcam";
      console.log("⏹️ Webcam stopped.");
      clearInterval(intervalId);
      intervalId = null;
    }
  });

  // 🧠 Process one frame at a time
  async function processFrame() {
    if (!streaming) return;
    if (video.readyState !== 4) {
      console.warn("⏳ Waiting for video to be ready...");
      return;
    }

    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert the current frame to JPEG Blob
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));

    if (!blob || blob.size === 0) {
      console.warn("⚠️ Empty blob (no frame captured). Skipping this cycle.");
      return;
    }

    console.log("📸 Captured frame. Blob size:", blob.size, "bytes");

    const formData = new FormData();
    formData.append("mode", modeSelect.value);
    formData.append("color", colorPicker.value);
    formData.append("file", blob, "frame.jpg");

    if (bgFileInput.files.length > 0) {
      formData.append("bg_file", bgFileInput.files[0]);
      console.log("🖼️ Using custom background:", bgFileInput.files[0].name);
    }

    try {
      const res = await fetch("/api/video/process_frame", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        console.error("❌ Server response error:", res.status, res.statusText);
        return;
      }

      const data = await res.json();
      console.log("📨 Server response:", data);

      if (data.error) {
        console.error("🚨 Processing error:", data.error);
        return;
      }

      // If backend returns Base64 string
      if (data.result && data.result.startsWith("data:image")) {
        output.src = data.result;
      }
      // If backend returns file path (e.g., /video/changed/frame_XXXX.jpg)
      else if (data.result && data.result.startsWith("/")) {
        output.src = data.result + "?t=" + Date.now();
      } else {
        console.warn("⚠️ Unknown response format from backend.");
      }
    } catch (err) {
      console.error("💥 Frame error:", err);
    }
  }
});
