import os
import asyncio
import importlib
from time import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ✅ Lightweight routers first
from routers import ImageView, VideoView, gallery_api
from routers import CleanFiles

app = FastAPI(title="SNT Background Changer App")

# ---------------- Templates ----------------
templates = Jinja2Templates(directory="templates")

def static_version(path: str) -> str:
    """Append ?v=timestamp to static files for cache busting."""
    full_path = os.path.join("static", path.lstrip("/"))
    version = int(os.path.getmtime(full_path)) if os.path.exists(full_path) else int(time())
    return f"/static/{path}?v={version}"

templates.env.globals["static_version"] = static_version

# ---------------- Static Mounts ----------------
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/video", StaticFiles(directory="video"), name="video")
app.mount("/video/changed", StaticFiles(directory="video/changed"), name="video_changed")
app.mount("/images/upload", NoCacheStaticFiles(directory="images/upload"), name="upload")
app.mount("/images/changed", NoCacheStaticFiles(directory="images/changed"), name="changed")
app.mount("/images/background", NoCacheStaticFiles(directory="images/background"), name="background")

# ---------------- Lightweight Routers ----------------
app.include_router(VideoView.router)
app.include_router(ImageView.router)
app.include_router(gallery_api.router)
app.include_router(CleanFiles.router)

# ---------------- Async Heavy Routers ----------------
async def async_import_router(module_name: str):
    """Import routers asynchronously to prevent blocking startup."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, importlib.import_module, module_name)

@app.on_event("startup")
async def load_heavy_routers():
    """Load heavy routers concurrently on startup."""
    heavy_modules = [
        "routers.video_api",
        "routers.record_api",
        "routers.image_api",
        "routers.background_api",
        "routers.modenet_api",
    ]

    print("🚀 Loading routers asynchronously...")
    modules = await asyncio.gather(*[async_import_router(m) for m in heavy_modules])

    for mod in modules:
        app.include_router(mod.router)
        print(f"✅ Loaded router: {mod.__name__}")

    print("✅ All routers loaded asynchronously.")

# ---------------- Web Pages ----------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home Page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request):
    """Gallery Page"""
    return templates.TemplateResponse("gallery.html", {"request": request})

# ---------------- Server Entry ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
