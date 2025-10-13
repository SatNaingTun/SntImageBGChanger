from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


# Import routers from subpackage
from routers import webcam

app = FastAPI(title="FastAPI Camera App")

# Mount static files and set template directory

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.mount("/images/upload", NoCacheStaticFiles(directory="images/upload"), name="upload")
app.mount("/images/changed", NoCacheStaticFiles(directory="images/changed"), name="changed")
app.mount("/images/background", NoCacheStaticFiles(directory="images/background"), name="background")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.mount("/video/changed", StaticFiles(directory="video/changed"), name="video_changed")
from routers import video_api
app.include_router(video_api.router)

from routers import webcam, stream_modnet, background_api, image_page, modenet_api
from routers import image_api

app.include_router(image_api.router)
app.include_router(webcam.router)
app.include_router(stream_modnet.router)
app.include_router(background_api.router)
app.include_router(modenet_api.router)
app.include_router(image_page.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main home page"""
    return templates.TemplateResponse("index.html", {"request": request})
