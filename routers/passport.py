# app/routes/passport.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/passport")
def passport_page(request: Request):
    return templates.TemplateResponse(
        "passport.html",
        {"request": request}
    )
