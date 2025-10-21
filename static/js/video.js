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
// 🔹 Background Preview
// ======================================================
document.getElementById('bg_file').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const preview = document.getElementById('bg_preview');
    preview.src = reader.result;
    preview.style.display = 'inline';
  };
  reader.readAsDataURL(file);
});

// ======================================================
// 🔹 Upload and Process Video (with Progress Bar)
// ======================================================
document.getElementById('uploadBtn').onclick = async () => {
  const videoInput = document.getElementById('videoUpload');
  if (!videoInput.files.length) {
    alert("Please select a video first!");
    return;
  }

  const formData = new FormData();
  formData.append("file", videoInput.files[0]);
  formData.append("mode", document.getElementById("modeSelect").value);
  formData.append("color", document.getElementById("colorPicker").value);
  const bgFile = document.getElementById("bg_file").files[0];
  if (bgFile) formData.append("bg_file", bgFile);

  const statusMsg = document.getElementById('statusMsg');
  const processedVideo = document.getElementById('processedVideo');
  const downloadLink = document.getElementById('downloadLink');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');

  // ✅ Reset UI
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
    // 🔁 Poll backend for progress every second
    // ======================================================
    while (!finished) {
      try {
        // ✅ Fetch fresh data every time (prevent caching)
        const resp = await fetch(progressUrl + `?t=${Date.now()}`, { cache: "no-store" });
        if (!resp.ok) throw new Error("HTTP " + resp.status);

        const prog = await resp.json();
        const pct = Number(prog.progress || 0);
        const stage = prog.stage || "processing";

        // Debug log
        console.log(`Progress: ${pct.toFixed(1)}% | Stage: ${stage}`);

        // Update progress bar
        progressBar.style.width = pct + "%";
        progressBar.textContent = pct.toFixed(1) + "%";

        if (stage === "done" || stage === "failed" || pct >= 100) {
          finished = true;
        }
      } catch (err) {
        console.warn("Progress fetch failed:", err);
      }

      // Wait 1 second before next check
      await new Promise(r => setTimeout(r, 1000));
    }

    // ======================================================
    // ✅ Processing complete
    // ======================================================
    progressBar.style.width = "100%";
    progressBar.textContent = "100%";
    progressBar.style.background = "linear-gradient(90deg,#28a745,#00e676)";
    statusMsg.textContent = "✅ Processing complete!";
    processedVideo.src = outputUrl;
    processedVideo.style.display = "block";
    downloadLink.href = outputUrl;
    downloadLink.style.display = "inline-block";
  } catch (err) {
    console.error("Error during upload:", err);
    statusMsg.textContent = "❌ Error during upload or processing.";
  }
};
