// static/js/passport.js
(() => {
  const fileEl = document.getElementById("file");
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");

  const modeEl = document.getElementById("mode");
  const mmBox = document.getElementById("mmBox");
  const pxBox = document.getElementById("pxBox");

  const wmmEl = document.getElementById("wmm");
  const hmmEl = document.getElementById("hmm");
  const dpiEl = document.getElementById("dpi");
  const wpxEl = document.getElementById("wpx");
  const hpxEl = document.getElementById("hpx");

  const bgEl = document.getElementById("bg");
  const bgHexEl = document.getElementById("bghex");
  const marginEl = document.getElementById("margin");
  const fmtEl = document.getElementById("fmt");

  const downloadBtn = document.getElementById("download");
  const resetBtn = document.getElementById("reset");

  let img = new Image();
  let imgLoaded = false;

  // View transform for interactive positioning
  let scale = 1.0;
  let offsetX = 0;
  let offsetY = 0;

  // Dragging
  let dragging = false;
  let lastX = 0, lastY = 0;

  // Crop box (fixed on screen, aspect changes based on output)
  function getAspect() {
    if (modeEl.value === "px") {
      const w = Math.max(1, parseFloat(wpxEl.value || "1"));
      const h = Math.max(1, parseFloat(hpxEl.value || "1"));
      return w / h;
    } else {
      const w = Math.max(1e-6, parseFloat(wmmEl.value || "35"));
      const h = Math.max(1e-6, parseFloat(hmmEl.value || "45"));
      return w / h;
    }
  }

  function getCropRectScreen() {
    // Keep a big crop box centered
    const pad = 70;
    const W = canvas.width;
    const H = canvas.height;
    const aspect = getAspect();

    let cw = W - 2 * pad;
    let ch = H - 2 * pad;

    if (cw / ch > aspect) {
      cw = ch * aspect;
    } else {
      ch = cw / aspect;
    }

    const x = (W - cw) / 2;
    const y = (H - ch) / 2;
    return { x, y, w: cw, h: ch };
  }

  function resetView() {
    if (!imgLoaded) return;

    // Fit image to canvas reasonably
    const fitScale = Math.min(canvas.width / img.width, canvas.height / img.height) * 0.9;
    scale = fitScale;

    offsetX = (canvas.width - img.width * scale) / 2;
    offsetY = (canvas.height - img.height * scale) / 2;

    draw();
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background checker-ish
    ctx.fillStyle = "#f7f7f7";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!imgLoaded) {
      ctx.fillStyle = "#666";
      ctx.font = "16px system-ui";
      ctx.fillText("Upload an image to start...", 20, 30);
      return;
    }

    // Draw transformed image
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0);
    ctx.restore();

    // Crop rect
    const r = getCropRectScreen();
    ctx.save();
    ctx.strokeStyle = "#111";
    ctx.lineWidth = 2;
    ctx.strokeRect(r.x, r.y, r.w, r.h);

    // Dim outside crop
    ctx.fillStyle = "rgba(0,0,0,0.18)";
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    ctx.rect(r.x, r.y, r.w, r.h);
    ctx.fill("evenodd");
    ctx.restore();
  }

  function screenToImage(px, py) {
    // Invert transform:
    // screen = offset + scale * image
    const ix = (px - offsetX) / scale;
    const iy = (py - offsetY) / scale;
    return { ix, iy };
  }

  function getCropRectImageCoords() {
    // Convert crop rect corners from screen to image coords
    const r = getCropRectScreen();
    const p0 = screenToImage(r.x, r.y);
    const p1 = screenToImage(r.x + r.w, r.y + r.h);

    const x = Math.min(p0.ix, p1.ix);
    const y = Math.min(p0.iy, p1.iy);
    const w = Math.abs(p1.ix - p0.ix);
    const h = Math.abs(p1.iy - p0.iy);

    // Clamp in JS too (backend clamps again)
    return {
      x: Math.max(0, Math.min(x, img.width - 1)),
      y: Math.max(0, Math.min(y, img.height - 1)),
      w: Math.max(1, Math.min(w, img.width)),
      h: Math.max(1, Math.min(h, img.height)),
    };
  }

  // Events
  fileEl.addEventListener("change", () => {
    const f = fileEl.files?.[0];
    if (!f) return;

    const url = URL.createObjectURL(f);
    img = new Image();
    img.onload = () => {
      imgLoaded = true;
      resetView();
    };
    img.src = url;
  });

  modeEl.addEventListener("change", () => {
    mmBox.style.display = modeEl.value === "mm" ? "" : "none";
    pxBox.style.display = modeEl.value === "px" ? "" : "none";
    draw();
  });

  [wmmEl, hmmEl, dpiEl, wpxEl, hpxEl].forEach(el => {
    el.addEventListener("input", draw);
  });

  canvas.addEventListener("mousedown", (e) => {
    dragging = true;
    lastX = e.offsetX;
    lastY = e.offsetY;
  });

  window.addEventListener("mouseup", () => dragging = false);

  canvas.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const dx = e.offsetX - lastX;
    const dy = e.offsetY - lastY;
    offsetX += dx;
    offsetY += dy;
    lastX = e.offsetX;
    lastY = e.offsetY;
    draw();
  });

  canvas.addEventListener("wheel", (e) => {
    if (!imgLoaded) return;
    e.preventDefault();

    const zoom = (e.deltaY < 0) ? 1.06 : 0.94;

    // Zoom about mouse position
    const mx = e.offsetX;
    const my = e.offsetY;

    const before = screenToImage(mx, my);
    scale *= zoom;
    scale = Math.max(0.05, Math.min(scale, 20));

    const afterX = before.ix * scale + offsetX;
    const afterY = before.iy * scale + offsetY;

    offsetX += (mx - afterX);
    offsetY += (my - afterY);

    draw();
  }, { passive: false });

  resetBtn.addEventListener("click", resetView);

  downloadBtn.addEventListener("click", async () => {
    const f = fileEl.files?.[0];
    if (!f) {
      alert("Please upload an image first.");
      return;
    }

    if (!imgLoaded) return;

    const crop = getCropRectImageCoords();

    const fd = new FormData();
    fd.append("file", f);

    // Output sizing
    if (modeEl.value === "px") {
      fd.append("out_width_px", String(parseInt(wpxEl.value || "0", 10)));
      fd.append("out_height_px", String(parseInt(hpxEl.value || "0", 10)));
    } else {
      fd.append("out_width_mm", String(parseFloat(wmmEl.value || "35")));
      fd.append("out_height_mm", String(parseFloat(hmmEl.value || "45")));
      fd.append("dpi", String(parseInt(dpiEl.value || "300", 10)));
    }

    // Crop coords in original image space
    fd.append("crop_x", String(crop.x));
    fd.append("crop_y", String(crop.y));
    fd.append("crop_w", String(crop.w));
    fd.append("crop_h", String(crop.h));

    // Style
    fd.append("bg", bgEl.value);
    fd.append("bg_hex", bgHexEl.value || "#FFFFFF");
    fd.append("margin_pct", String((parseFloat(marginEl.value || "6") / 100.0)));
    fd.append("fmt", fmtEl.value);

    const res = await fetch("/api/passport/render", { method: "POST", body: fd });
    if (!res.ok) {
      const msg = await res.text();
      alert("Error: " + msg);
      return;
    }

    const blob = await res.blob();
    const ext = (fmtEl.value === "png") ? "png" : "jpg";
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `passport_photo.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });

  draw();
})();
