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
// 🔹 Upload and Process Video (with progress bar)
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

  statusMsg.textContent = "⏳ Uploading and processing...";
  processedVideo.style.display = "none";
  downloadLink.style.display = "none";
  progressContainer.style.display = "block";
  progressBar.style.width = "0%";
  progressBar.textContent = "0%";
  progressBar.style.background = "linear-gradient(90deg, #007bff, #00d4ff)";

  try {
    const res = await fetch("/api/video/process_video", { method: "POST", body: formData });
    const data = await res.json();

    if (!data.progress_id) {
      statusMsg.textContent = "❌ Processing failed.";
      return;
    }

    const progressUrl = `/api/video/progress/${data.progress_id}`;
    const outputUrl = data.output_url;
    let finished = false;

    while (!finished) {
      const resp = await fetch(progressUrl);
      const prog = await resp.json();
      const pct = prog.progress || 0;

      progressBar.style.width = pct + "%";
      progressBar.textContent = pct.toFixed(1) + "%";

      if (prog.stage === "done" || prog.stage === "failed") {
        finished = true;
        break;
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    if (finished) {
      progressBar.style.width = "100%";
      progressBar.textContent = "100%";
      progressBar.style.background = "linear-gradient(90deg,#28a745,#00e676)";
      statusMsg.textContent = "✅ Processing complete!";
      processedVideo.src = outputUrl;
      processedVideo.style.display = "block";
      downloadLink.href = outputUrl;
      downloadLink.style.display = "inline-block";
    }
  } catch (err) {
    console.error("Error during upload:", err);
    statusMsg.textContent = "❌ Error during upload or processing.";
  }
};
