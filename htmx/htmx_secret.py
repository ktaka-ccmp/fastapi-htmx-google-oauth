from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory='templates')

# Normal Response function
@router.get("/content.secret1", response_class=HTMLResponse)
async def content_secret1(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    img_url = settings.origin_server + "/img/secret1.png"
    context = {"request": request, "title": "Oops, my secret's been revealed!", "img_url": img_url}
    return templates.TemplateResponse("content.secret.j2", context)

@router.get("/content.secret2", response_class=HTMLResponse)
async def content_secret2(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    img_url = settings.origin_server + "/img/secret2.png"
    context = {"request": request, "title": "Believe it or not, it's absolutely not me!", "img_url": img_url}
    return templates.TemplateResponse("content.secret.j2", context)
