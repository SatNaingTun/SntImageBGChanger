document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const output = document.getElementById("output");
  const startBtn = document.getElementById("startBtn");
  const modeSelect = document.getElementById("modeSelect");
  const colorPicker = document.getElementById("colorPicker");
  const bgFileInput = document.getElementById("bg_file");
  const bgLabel = document.getElementById("bg_label");

  let streaming = false;
  let intervalId = null;

  // Show/hide background upload button
  modeSelect.addEventListener("change", () => {
    if (modeSelect.value === "custom") {
      bgLabel.style.display = "inline-block";
    } else {
      bgLabel.style.display = "none";
      bgFileInput.value = "";
    }
  });

  // Start/Stop webcam
  startBtn.addEventListener("click", async () => {
    if (!streaming) {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      streaming = true;
      startBtn.textContent = "Stop Webcam";
      intervalId = setInterval(processFrame, 500); // ~2 FPS
    } else {
      video.srcObject.getTracks().forEach((t) => t.stop());
      streaming = false;
      startBtn.textContent = "Start Webcam";
      clearInterval(intervalId);
    }
  });

  async function processFrame() {
    if (!streaming || video.readyState !== 4) return;

    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9)
    );
    if (!blob || blob.size === 0) return;

    const formData = new FormData();
    formData.append("mode", modeSelect.value);
    formData.append("color", colorPicker.value);
    formData.append("file", blob, "frame.jpg");

    if (modeSelect.value === "custom" && bgFileInput.files.length > 0) {
      formData.append("bg_file", bgFileInput.files[0]);
      console.log("🖼️ Custom background:", bgFileInput.files[0].name);
    }

    try {
      const res = await fetch("/api/video/process_frame", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.result) output.src = data.result;
    } catch (err) {
      console.error("Frame error:", err);
    }
  }
});
