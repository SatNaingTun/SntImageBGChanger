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
// 🔹 Upload and Process Video
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

  statusMsg.textContent = "⏳ Uploading and processing...";
  processedVideo.style.display = "none";
  downloadLink.style.display = "none";

  try {
    const res = await fetch("/api/video/process_video", { method: "POST", body: formData });
    const data = await res.json();

    if (!data.output_url) {
      statusMsg.textContent = "❌ Processing failed.";
      return;
    }

    const url = data.output_url;
    statusMsg.textContent = "✅ Done! Processed video ready.";
    processedVideo.src = url;
    processedVideo.style.display = "block";
    downloadLink.href = url;
    downloadLink.style.display = "inline-block";
  } catch (err) {
    console.error("Error during upload:", err);
    statusMsg.textContent = "❌ Error during upload or processing.";
  }
};
