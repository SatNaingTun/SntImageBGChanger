from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Import routers from subpackage
from routers import webcam

app = FastAPI(title="FastAPI Camera App")

# Mount static files and set template directory
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images/upload", StaticFiles(directory="images/upload"), name="upload")
app.mount("/images/changed", StaticFiles(directory="images/changed"), name="changed")
app.mount("/images/background", StaticFiles(directory="images/background"), name="background")

templates = Jinja2Templates(directory="templates")

from routers import webcam, stream_modnet, background_api, image_page, modenet_api

app.include_router(webcam.router)
app.include_router(stream_modnet.router)
app.include_router(background_api.router)
app.include_router(modenet_api.router)
app.include_router(image_page.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main home page"""
    return templates.TemplateResponse("index.html", {"request": request})
