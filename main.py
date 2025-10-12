from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Import routers from subpackage
from routers import webcam

app = FastAPI(title="FastAPI Camera App")

# Mount static files and set template directory
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include router
app.include_router(webcam.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main home page"""
    return templates.TemplateResponse("index.html", {"request": request})
