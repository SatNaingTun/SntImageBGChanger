import os
import asyncio
from time import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from concurrent.futures import ThreadPoolExecutor

# Import lightweight routers immediately
from routers import (
    video_api,
    record_api,
    image_api,
    webcam,
    background_api,
    image_page,
    gallery_api,
)

# Prepare FastAPI app
app = FastAPI(title="FastAPI Camera App")

# Setup templates
templates = Jinja2Templates(directory="templates")

# ========== Static file versioning helper ==========
def static_version(path: str) -> str:
    """Append ?v=timestamp for cache busting."""
    full_path = os.path.join("static", path.lstrip("/"))
    version = int(os.path.getmtime(full_path)) if os.path.exists(full_path) else int(time())
    return f"/static/{path}?v={version}"

templates.env.globals["static_version"] = static_version

# ========== Mount Static Directories ==========
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

# ========== Include Routers (lightweight first) ==========
app.include_router(video_api.router)
app.include_router(record_api.router)
app.include_router(image_api.router)
app.include_router(webcam.router)
app.include_router(background_api.router)
app.include_router(image_page.router)
app.include_router(gallery_api.router)


# ========== Async Heavy Router Loading ==========
async def async_import_router(module_name: str):
    """Import router module asynchronously (non-blocking)."""
    import importlib
    loop = asyncio.get_running_loop()
    module = await loop.run_in_executor(None, importlib.import_module, module_name)
    return module

@app.on_event("startup")
async def load_heavy_routers():
    """Load heavy routers like MODNet asynchronously on startup."""
    heavy_modules = ["routers.stream_modnet", "routers.modenet_api"]
    print("🚀 Starting async router initialization...")

    modules = await asyncio.gather(*[async_import_router(m) for m in heavy_modules])
    for m in modules:
        app.include_router(m.router)

    print("✅ All heavy routers loaded asynchronously.")


# ========== Routes ==========
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home Page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request):
    """Gallery Page"""
    return templates.TemplateResponse("gallery.html", {"request": request})


# ========== Run Server ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
