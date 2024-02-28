from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory='templates')

@router.get("/", response_class=HTMLResponse)
@router.get("/{page}", response_class=HTMLResponse)
async def spa(request: Request, page: str | None = None):
    if page == None:
        page = "content.top"
    context = {"request": request, "page": page}
    return templates.TemplateResponse("spa.j2", context)
