document.addEventListener("DOMContentLoaded", () => {

  const gallery = document.getElementById("gallery");
  const loading = document.getElementById("loading");

  // Overlay elements
  const overlay = document.getElementById("viewerOverlay");
  const viewerContainer = document.getElementById("viewerContainer");
  const viewerTitle = document.getElementById("viewerTitle");

  const viewerSub = document.querySelector(".channel-sub");
  const btnClose = document.getElementById("viewerClose");
  const btnPrev = document.getElementById("viewerPrev");
  const btnNext = document.getElementById("viewerNext");

  let items = [];
  let currentIndex = 0;
  let observer = null;

  // =============== LOAD GALLERY ===============
  async function loadGallery() {
    try {
      const res = await fetch("/api/gallery/list");
      const data = await res.json();
      items = data.gallery || [];

      gallery.innerHTML = "";
      loading.textContent = "";

      items.forEach((item, index) => {
        const box = document.createElement("div");
        box.className = "item";
        box.dataset.index = index;

        // ---------- Thumbnail ----------
        if (item.type === "video") {
          box.classList.add("video");

          const wrap = document.createElement("div");
          wrap.className = "thumb video-thumb";

          const img = document.createElement("img");
          img.className = "thumb-img";
          img.dataset.src = item.thumbnail;

          const play = document.createElement("div");
          play.className = "play-overlay";

          wrap.appendChild(img);
          wrap.appendChild(play);
          wrap.addEventListener("click", () => openViewer(index));

          box.appendChild(wrap);
        } else {
          const img = document.createElement("img");
          img.className = "thumb";
          img.dataset.src = item.thumbnail;
          img.addEventListener("click", () => openViewer(index));
          box.appendChild(img);
        }

        // ---------- Name ----------
        const name = document.createElement("div");
        name.style.textAlign = "center";
        name.style.padding = "6px 0";
        name.style.fontWeight = "600";
        name.textContent = item.name;
        box.appendChild(name);

        // ---------- Actions ----------
        const actions = document.createElement("div");
        actions.className = "actions";
        actions.innerHTML = `
          <a href="${item.path}" download class="btn btn-download">⬇ Download</a>
          <button class="btn btn-delete">🗑 Delete</button>
        `;
        box.appendChild(actions);

        actions.querySelector(".btn-delete").addEventListener("click", async () => {
          if (!confirm("Delete file?")) return;
          await fetch(`/api/gallery/delete/${item.name}`, { method: "DELETE" });
          loadGallery();
        });

        gallery.appendChild(box);
      });

      // Lazy-load thumbnails
      if (observer) observer.disconnect();
      observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            const el = e.target;
            if (el.dataset.src) {
              el.src = el.dataset.src;
              el.removeAttribute("data-src");
            }
            observer.unobserve(el);
          }
        });
      });

      document.querySelectorAll("[data-src]").forEach(el => observer.observe(el));

    } catch (err) {
      loading.textContent = "Error loading gallery.";
      console.error(err);
    }
  }

  // =============== OPEN VIEWER ===============
  function openViewer(i) {
    currentIndex = i;
    const item = items[i];

    viewerContainer.innerHTML = "";

    // ----- Set HEADER -----
    viewerTitle.textContent = item.name;
    viewerSub.textContent = "Viewed on " + new Date().toLocaleDateString();

    // ----- Show Media -----
    if (item.type === "video") {
      const vid = document.createElement("video");
      vid.src = item.path;
      vid.controls = true;
      vid.autoplay = true;
      vid.id = "activeVideo";
      viewerContainer.appendChild(vid);

      // Double-click = PiP
      vid.addEventListener("dblclick", async () => {
        if (document.pictureInPictureElement) {
          document.exitPictureInPicture();
        } else {
          try { await vid.requestPictureInPicture(); }
          catch (e) { console.warn("PiP not available"); }
        }
      });

    } else {
      const img = document.createElement("img");
      img.src = item.path;
      viewerContainer.appendChild(img);
    }

    overlay.classList.remove("hidden");
  }

  // =============== OVERLAY CONTROLS ===============

  function closeViewer() {
    overlay.classList.add("hidden");
    viewerContainer.innerHTML = "";
  }

  function next() {
    currentIndex = (currentIndex + 1) % items.length;
    openViewer(currentIndex);
  }

  function prev() {
    currentIndex = (currentIndex - 1 + items.length) % items.length;
    openViewer(currentIndex);
  }

  btnClose.onclick = closeViewer;
  btnNext.onclick = next;
  btnPrev.onclick = prev;

  // Keyboard navigation
  document.addEventListener("keydown", e => {
    if (overlay.classList.contains("hidden")) return;
    if (e.key === "Escape") closeViewer();
    if (e.key === "ArrowRight") next();
    if (e.key === "ArrowLeft") prev();
  });

  // Click outside to close
  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeViewer();
  });

  // Init
  loadGallery();
  setInterval(loadGallery, 10000); // auto-refresh
});
