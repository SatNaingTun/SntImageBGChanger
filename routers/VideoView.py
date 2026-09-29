from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def render_template(template_name: str, request: Request, **context):
    template = templates.get_template(template_name)
    return HTMLResponse(template.render(request=request, **context))


router = APIRouter(prefix="/videoview", tags=["Video View"])

@router.get("/", response_class=HTMLResponse)
async def VideoView(request: Request):
    """Render the video control page"""
    return render_template("VideoView.html", request)
