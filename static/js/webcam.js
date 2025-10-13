document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const output = document.getElementById("output");
  const startBtn = document.getElementById("startBtn");
  const modeSelect = document.getElementById("modeSelect");
  const colorPicker = document.getElementById("colorPicker");
  const bgLabel = document.getElementById("bg_label");
  const bgPreview = document.getElementById("bg_preview");
  const bgFile = document.getElementById("bg_file");

  let streaming = false;
  let intervalId = null;
  let sessionId = 0; // 🆕 Used to ignore late frames

  // 🧠 Mode change: show/hide background + color picker
  modeSelect.addEventListener("change", () => {
    const mode = modeSelect.value;

    if (mode === "custom") {
      bgLabel.style.display = "inline-block";
      bgPreview.style.display = bgFile.files.length > 0 ? "inline-block" : "none";
      colorPicker.style.display = "none"; // hide color picker for custom BG
    } else {
      bgLabel.style.display = "none";
      bgPreview.style.display = "none";
      bgFile.value = "";
      bgPreview.src = "";
      colorPicker.style.display = "inline-block"; // show color picker again
    }
  });

  // 🖼️ Preview uploaded background
  bgFile.addEventListener("change", (e) => {
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
        sessionId = Date.now(); // 🆕 new session ID
        startBtn.textContent = "⏹ Stop Webcam";
        startBtn.classList.remove("btn-start");
        startBtn.classList.add("btn-stop");
        intervalId = setInterval(() => processFrame(sessionId), 500);
      } catch (err) {
        alert("Webcam access denied: " + err.message);
      }
    } else {
      // 🧹 Stop webcam
      if (video.srcObject) {
        video.srcObject.getTracks().forEach((t) => t.stop());
      }
      streaming = false;

      // 🧩 Invalidate session so late frames are ignored
      sessionId = 0;

      // Stop interval
      clearInterval(intervalId);
      intervalId = null;

      // 🎨 Reset UI
      startBtn.textContent = "🎥 Start Webcam";
      startBtn.classList.remove("btn-stop");
      startBtn.classList.add("btn-start");

      // 🕶️ Set Processed Output to black immediately
      const blackPixel =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQoBAQfz7W4AAAAASUVORK5CYII=";
      output.src = blackPixel;
      output.alt = "Processed Output (Stopped)";
      console.log("🧹 Webcam stopped, output set to black.");
    }
  });

  // 🧠 Frame processing (with session check)
  async function processFrame(currentSession) {
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

    if (modeSelect.value === "custom" && bgFile.files.length > 0) {
      formData.append("bg_file", bgFile.files[0]);
    }

    try {
      const res = await fetch("/api/video/process_frame", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      // 🧩 Ignore late responses (from previous session)
      if (!streaming || currentSession !== sessionId) return;

      if (data.result) output.src = data.result;
    } catch (err) {
      console.error("Frame error:", err);
    }
  }

  if (!modeSelect) {
    console.debug("webcam.js: modeSelect not found, aborting UI init");
    return;
  }

  function updateControls() {
    const mode = modeSelect.value;
    if (mode === "color") {
      if (colorPicker) colorPicker.style.display = "inline-block";
      if (bgLabel) bgLabel.style.display = "none";
      if (bgPreview) bgPreview.style.display = "none";
    } else if (mode === "custom") {
      if (colorPicker) colorPicker.style.display = "none";
      if (bgLabel) bgLabel.style.display = "inline-block";
    } else {
      // transparent
      if (colorPicker) colorPicker.style.display = "none";
      if (bgLabel) bgLabel.style.display = "none";
      if (bgPreview) bgPreview.style.display = "none";
    }
  }

  modeSelect.addEventListener("change", updateControls);
  updateControls();
});
