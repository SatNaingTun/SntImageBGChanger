// ======================================================
// 🔹 Tab Switching (Upload <-> Webcam)
// ======================================================
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// ======================================================
// 🔹 Dynamic UI Visibility for Mode Options
// ======================================================
const modeSelect = document.getElementById("modeSelect");
const colorPicker = document.getElementById("colorPicker");
const bgLabel = document.getElementById("bgLabel");
const bgFileInput = document.getElementById("bg_file");
const bgPreviewContainer = document.getElementById("bgPreviewContainer");
const bgPreviewImg = document.getElementById("bg_preview_img");
const bgPreviewVideo = document.getElementById("bg_preview_video");
const blurContainer = document.getElementById("blurContainer");
const blurRange = document.getElementById("blurRange");
const blurValue = document.getElementById("blurValue");

function updateModeUI() {
  const mode = modeSelect.value;

  // Hide all optional controls by default
  colorPicker.style.display = "none";
  bgLabel.style.display = "none";
  bgPreviewContainer.style.display = "none";
  bgPreviewImg.style.display = "none";
  bgPreviewVideo.style.display = "none";
  blurContainer.style.display = "none";

  if (mode === "color") {
    colorPicker.style.display = "inline-block";
  } else if (mode === "custom") {
    bgLabel.style.display = "inline-block";
    if (bgFileInput.files.length > 0) {
      bgPreviewContainer.style.display = "inline-block";
    }
  } else if (mode === "blur") {
    blurContainer.style.display = "flex";
  }
}

modeSelect.addEventListener("change", updateModeUI);
updateModeUI(); // initialize on load

// ======================================================
// 🔹 Blur slider display value
// ======================================================
if (blurRange && blurValue) {
  blurRange.addEventListener("input", () => {
    blurValue.textContent = blurRange.value;
  });
}

// ======================================================
// 🔹 Background Preview (Image or Video)
// ======================================================
if (bgFileInput) {
  bgFileInput.addEventListener("change", e => {
    const file = e.target.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);

    // Reset previews
    bgPreviewImg.style.display = "none";
    bgPreviewVideo.style.display = "none";
    bgPreviewContainer.style.display = "none";

    if (file.type.startsWith("image/")) {
      bgPreviewImg.src = url;
      bgPreviewImg.style.display = "inline-block";
      bgPreviewContainer.style.display = "inline-block";
    } else if (file.type.startsWith("video/")) {
      bgPreviewVideo.src = url;
      bgPreviewVideo.load();
      bgPreviewVideo.play();
      bgPreviewVideo.loop = true;
      bgPreviewVideo.style.display = "inline-block";
      bgPreviewContainer.style.display = "inline-block";
    }
  });
}

// ======================================================
// 🔹 Upload and Process Video (with Frame Progress)
// ======================================================
document.getElementById('uploadBtn').onclick = async () => {
  const videoInput = document.getElementById('videoUpload');
  if (!videoInput.files.length) {
    alert("Please select a video first!");
    return;
  }

  const formData = new FormData();
  formData.append("file", videoInput.files[0]);
  formData.append("mode", modeSelect.value);
  formData.append("color", colorPicker.value);
  formData.append("blur_strength", blurRange.value);
  const bgFile = bgFileInput.files[0];
  if (bgFile) formData.append("bg_file", bgFile);

  const statusMsg = document.getElementById('statusMsg');
  const processedVideo = document.getElementById('processedVideo');
  const downloadLink = document.getElementById('downloadLink');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');

  // Reset UI
  statusMsg.textContent = "⏳ Uploading and processing...";
  processedVideo.style.display = "none";
  downloadLink.style.display = "none";
  progressContainer.style.display = "block";
  progressBar.style.width = "0%";
  progressBar.textContent = "0%";
  progressBar.style.background = "linear-gradient(90deg,#007bff,#00d4ff)";

  try {
    // Send the video to backend for processing
    const res = await fetch("/api/video/process_video", { method: "POST", body: formData });
    const data = await res.json();

    if (!data.progress_id) {
      statusMsg.textContent = "❌ Processing failed.";
      return;
    }

    const progressUrl = `/api/video/progress/${data.progress_id}`;
    const outputUrl = data.output_url;
    let finished = false;

    // ======================================================
    // 🔁 Poll backend for frame-based progress
    // ======================================================
    while (!finished) {
      try {
        const resp = await fetch(progressUrl + `?t=${Date.now()}`, { cache: "no-store" });
        if (!resp.ok) throw new Error("HTTP " + resp.status);

        const prog = await resp.json();
        const pct = Number(prog.progress || 0);
        const stage = prog.stage || "processing";
        const frameIdx = prog.frame_index || 0;
        const frameTotal = prog.frame_total || 0;
        const framePct = frameTotal > 0 ? (frameIdx / frameTotal) * 100 : pct;

        // Update progress bar
        progressBar.style.width = framePct.toFixed(1) + "%";
        progressBar.textContent = framePct.toFixed(1) + "%";
        console.log(`Progress: ${framePct.toFixed(1)}% | Frame ${frameIdx}/${frameTotal} | Stage: ${stage}`);

        if ((framePct >= 100 && stage === "done") || stage === "failed") {
          finished = true;
        }
      } catch (err) {
        console.warn("Progress fetch failed:", err);
      }

      await new Promise(r => setTimeout(r, 1000)); // wait 1 second
    }

    // ======================================================
    // ✅ Wait until file is ready and then display video
    // ======================================================
    progressBar.style.width = "100%";
    progressBar.textContent = "100%";
    progressBar.style.background = "linear-gradient(90deg,#28a745,#00e676)";
    statusMsg.textContent = "✅ Processing complete! Finalizing file...";

    let fileReady = false;
    for (let attempt = 0; attempt < 10; attempt++) {
      try {
        const headCheck = await fetch(outputUrl, { method: "HEAD", cache: "no-store" });
        if (headCheck.ok) {
          fileReady = true;
          break;
        }
      } catch (e) {
        console.warn("Video readiness check failed:", e);
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    if (fileReady) {
      processedVideo.src = outputUrl + "?t=" + Date.now();
      processedVideo.load();
      processedVideo.style.display = "block";
      downloadLink.href = outputUrl;
      downloadLink.style.display = "inline-block";
      statusMsg.textContent = "✅ Video ready to view!";
    } else {
      statusMsg.textContent = "⚠️ Video file is taking longer to finalize. Try refreshing.";
    }

  } catch (err) {
    console.error("Error during upload:", err);
    statusMsg.textContent = "❌ Error during upload or processing.";
  }
};
