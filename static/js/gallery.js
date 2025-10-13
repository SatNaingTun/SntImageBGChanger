document.addEventListener("DOMContentLoaded", () => {
  const gallery = document.getElementById("gallery");
  const loading = document.getElementById("loading");
  let observer;

  async function loadGallery() {
    try {
      const res = await fetch("/api/gallery/list");
      if (!res.ok) throw new Error("Failed to fetch gallery list");
      const data = await res.json();

      gallery.innerHTML = "";
      loading.textContent = "";

      if (!data.gallery || data.gallery.length === 0) {
        loading.textContent = "No recordings or snapshots yet.";
        return;
      }

      data.gallery.forEach(item => {
        const div = document.createElement("div");
        div.className = "item";

        if (item.type === "video") {
          // Thumbnail preview
          const img = document.createElement("img");
          img.className = "thumb";
          img.dataset.src = item.thumbnail;
          img.alt = "video thumbnail";
          img.addEventListener("click", () => {
            const video = document.createElement("video");
            video.src = item.path;
            video.controls = true;
            video.autoplay = true;
            video.style.width = "100%";
            video.style.height = "180px";
            div.replaceChild(video, img);
          });
          div.appendChild(img);
        } else {
          const img = document.createElement("img");
          img.className = "thumb";
          img.dataset.src = item.thumbnail;
          img.alt = "snapshot";
          div.appendChild(img);
        }

        const actions = document.createElement("div");
        actions.className = "actions";
        actions.innerHTML = `
          <a href="${item.path}" class="btn btn-download" download>⬇ Download</a>
          <button class="btn btn-delete">🗑 Delete</button>
        `;
        div.appendChild(actions);

        // Delete handler
        actions.querySelector(".btn-delete").addEventListener("click", async () => {
          if (!confirm("Delete this item?")) return;
          const res = await fetch(`/api/gallery/delete/${item.name}`, { method: "DELETE" });
          if (res.ok) div.remove();
        });

        gallery.appendChild(div);
      });

      // Lazy-load thumbnails
      if (observer) observer.disconnect();
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const el = entry.target;
            if (el.dataset.src) {
              el.src = el.dataset.src;
              el.removeAttribute("data-src");
            }
            observer.unobserve(el);
          }
        });
      });
      document.querySelectorAll(".thumb[data-src]").forEach(el => observer.observe(el));

    } catch (err) {
      loading.textContent = "⚠️ Error loading gallery.";
      console.error(err);
    }
  }

  // 🌍 Make function globally available for external trigger
  window.refreshGallery = loadGallery;

  // Initial + auto-refresh
  loadGallery();
  setInterval(loadGallery, 10000);
});
