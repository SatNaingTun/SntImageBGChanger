document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const output = document.getElementById("output");
  const startBtn = document.getElementById("startBtn");
  const modeSelect = document.getElementById("modeSelect");
  const colorPicker = document.getElementById("colorPicker");
  const bgFileInput = document.getElementById("bg_file");
  const bgLabel = document.getElementById("bg_label");
  const bgPreview = document.getElementById("bg_preview");

  let streaming = false;
  let intervalId = null;

  // 🧠 Mode change: show/hide background + color picker
  modeSelect.addEventListener("change", () => {
    const mode = modeSelect.value;

    if (mode === "custom") {
      bgLabel.style.display = "inline-block";
      bgPreview.style.display = bgFileInput.files.length > 0 ? "inline-block" : "none";
      colorPicker.style.display = "none";  // hide color when using custom BG
    } else {
      bgLabel.style.display = "none";
      bgPreview.style.display = "none";
      bgFileInput.value = "";
      bgPreview.src = "";
      colorPicker.style.display = "inline-block";  // show color picker again
    }
  });

  // 🖼️ Preview uploaded background
  bgFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        bgPreview.src = event.target.result;
        bgPreview.style.display = "inline-block";
      };
      reader.readAsDataURL(file);
    } else {
      bgPreview.src = "";
      bgPreview.style.display = "none";
    }
  });

  // 🎥 Start/Stop webcam
  startBtn.addEventListener("click", async () => {
    if (!streaming) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        streaming = true;
        startBtn.textContent = "⏹ Stop Webcam";
        startBtn.classList.remove("btn-start");
        startBtn.classList.add("btn-stop");
        intervalId = setInterval(processFrame, 500);
      } catch (err) {
        alert("Webcam access denied: " + err.message);
      }
    } else {
      // stop webcam
      video.srcObject.getTracks().forEach((t) => t.stop());
      streaming = false;
      startBtn.textContent = "🎥 Start Webcam";
      startBtn.classList.remove("btn-stop");
      startBtn.classList.add("btn-start");
      clearInterval(intervalId);
    }
  });

  // 🧠 Frame processing
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
