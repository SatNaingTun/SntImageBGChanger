from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/webcam", tags=["Webcam"])

@router.get("/", response_class=HTMLResponse)
async def webcam_page(request: Request):
    """Render the webcam control page"""
    return templates.TemplateResponse("webcam.html", {"request": request})
