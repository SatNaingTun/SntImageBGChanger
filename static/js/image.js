document.addEventListener("DOMContentLoaded", () => {
  const modeSelect = document.getElementById("modeSelect");
  const colorField = document.getElementById("colorField");
  const bgUploadField = document.getElementById("bgUploadField");
  const form = document.getElementById("uploadForm");
  const loading = document.getElementById("loading");
  const previewSection = document.getElementById("previewSection");
  const resultPreview = document.getElementById("resultPreview");
  const originalPreview = document.getElementById("originalPreview");
  const downloadLink = document.getElementById("downloadLink");
  const buttons = document.getElementById("buttons");
  const resetBtn = document.getElementById("resetBtn");
  const fileInput = document.getElementById("fileInput");

  // Show/hide fields based on mode selection
  function toggleFields() {
    const mode = modeSelect.value;
    colorField.style.display = mode === "color" ? "flex" : "none";
    bgUploadField.style.display = mode === "custom" ? "flex" : "none";
  }
  modeSelect.addEventListener("change", toggleFields);
  toggleFields();

  // Handle form submission (AJAX)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return alert("Please choose an image first.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", modeSelect.value);
    formData.append("color", document.getElementById("colorPicker").value);

    const bgFile = document.getElementById("bg_file").files[0];
    if (bgFile) formData.append("bg_file", bgFile);

    // Debug form data
    for (const [key, value] of formData.entries()) {
      console.log("⬆ sending:", key, value);
    }

    // Show local preview immediately (no waiting)
    originalPreview.src = URL.createObjectURL(file);
    previewSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    previewSection.style.opacity = "0.5";
    buttons.classList.add("hidden");

    try {
      // Send request to backend
      const res = await fetch("/api/image/process", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("⬇ response:", data);

      if (data.error) throw new Error(data.error);

      // Small delay to ensure FastAPI has finished writing files
      await new Promise((r) => setTimeout(r, 300));

      // Force fresh fetch (avoid browser cache)
      const ts = "?t=" + new Date().getTime();
      originalPreview.src = data.original + ts;
      resultPreview.src = data.result + ts;
      downloadLink.href = data.download + ts;

      previewSection.style.opacity = "1";
      buttons.classList.remove("hidden");
    } catch (err) {
      alert("❌ Error: " + err.message);
      console.error(err);
    } finally {
      loading.classList.add("hidden");
    }
  });

  // Reset form
  resetBtn.addEventListener("click", () => {
    form.reset();
    previewSection.classList.add("hidden");
    buttons.classList.add("hidden");
    toggleFields();
  });
});
