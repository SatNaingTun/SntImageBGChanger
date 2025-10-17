from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/videoview", tags=["Video View"])

@router.get("/", response_class=HTMLResponse)
async def VideoView(request: Request):
    """Render the video control page"""
    return templates.TemplateResponse("VideoView.html", {"request": request})
