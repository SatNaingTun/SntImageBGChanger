document.addEventListener("DOMContentLoaded", async () => {
  const gallery = document.getElementById("record-gallery");

  async function loadRecordings() {
    try {
      const res = await fetch("/api/record/list");
      const data = await res.json();

      if (!data.recordings || data.recordings.length === 0) {
        gallery.innerHTML = `<p style="text-align:center;">📭 No recordings found.</p>`;
        return;
      }

      gallery.innerHTML = ""; // Clear old entries

      data.recordings.forEach((rec) => {
        const card = document.createElement("div");
        card.className = "record-card";

        const filename = rec.video_path.split("/").pop();

        const dateLabel = new Date().toLocaleString("en-US", {
          hour12: false,
          year: "numeric",
          month: "short",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });

        card.innerHTML = `
          <img src="${rec.thumbnail_path}" 
               alt="Thumbnail"
               class="record-thumb"
               onclick="window.open('${rec.video_path}', '_blank')">
          <div class="record-actions">
            <a href="${rec.video_path}" target="_blank" class="btn-play">▶ Play</a>
            <a href="${rec.download_link}" download class="btn-download">⬇ Download</a>
            <button class="btn-delete">🗑 Delete</button>
          </div>
          <div class="record-date">${dateLabel}</div>
        `;

        // Delete handler
        card.querySelector(".btn-delete").addEventListener("click", async () => {
          if (!confirm("Are you sure you want to delete this recording?")) return;

          try {
            const res = await fetch(`/api/record/delete/${filename}`, { method: "DELETE" });
            if (res.ok) {
              card.remove();
              console.log(`🗑 Deleted ${filename}`);
            } else {
              const err = await res.json();
              alert("⚠️ Delete failed: " + (err.detail || "Unknown error"));
            }
          } catch (err) {
            console.error("Delete failed:", err);
            alert("Delete failed: " + err.message);
          }
        });

        gallery.appendChild(card);
      });
    } catch (err) {
      console.error("Failed to load gallery:", err);
    }
  }

  // 🚀 Initialize
  loadRecordings();
});
