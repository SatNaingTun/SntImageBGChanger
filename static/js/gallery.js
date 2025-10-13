document.addEventListener("DOMContentLoaded", async () => {
  const gallery = document.getElementById("gallery");

  async function loadGallery() {
    gallery.innerHTML = "⏳ Loading...";
    const res = await fetch("/api/gallery/list");
    const data = await res.json();
    gallery.innerHTML = "";

    if (!data.gallery || data.gallery.length === 0) {
      gallery.innerHTML = "<p style='text-align:center;'>No recordings or snapshots yet.</p>";
      return;
    }

    data.gallery.forEach(item => {
      const div = document.createElement("div");
      div.className = "item";

      if (item.type === "video") {
        div.innerHTML = `
          <video class="thumb" src="${item.path}" controls preload="metadata"></video>
          <div class="actions">
            <a href="${item.path}" class="btn btn-download" download>⬇ Download</a>
            <button class="btn btn-delete">🗑 Delete</button>
          </div>
        `;
      } else {
        div.innerHTML = `
          <img class="thumb" src="${item.thumbnail}" alt="snapshot">
          <div class="actions">
            <a href="${item.path}" class="btn btn-download" download>⬇ Download</a>
            <button class="btn btn-delete">🗑 Delete</button>
          </div>
        `;
      }

      const delBtn = div.querySelector(".btn-delete");
      delBtn.addEventListener("click", async () => {
        if (!confirm("Delete this item?")) return;
        const res = await fetch(`/api/gallery/delete/${item.name}`, { method: "DELETE" });
        if (res.ok) div.remove();
      });

      gallery.appendChild(div);
    });
  }

  loadGallery();
});
