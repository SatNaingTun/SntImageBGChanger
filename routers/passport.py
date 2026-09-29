# app/routes/passport.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def render_template(template_name: str, request: Request, **context):
    template = templates.get_template(template_name)
    return HTMLResponse(template.render(request=request, **context))


@router.get("/passport")
def passport_page(request: Request):
    return render_template("passport.html", request)
