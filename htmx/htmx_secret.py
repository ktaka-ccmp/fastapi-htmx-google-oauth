from typing import Optional, Annotated
from fastapi import APIRouter, Request, HTTPException, status, Header, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory='templates')

# Normal Response function
@router.get("/secret1", response_class=HTMLResponse)
async def secret1(request: Request, hx_request: Optional[str] = Header(None), session_id: Annotated[str | None, Cookie()] = None,):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "title": "You've reached Secret Page #1 !"}
    return templates.TemplateResponse("secret.j2", context)

@router.get("/secret2", response_class=HTMLResponse)
async def secret2(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "title": "You've reached Secret Page #2 !"}
    return templates.TemplateResponse("secret.j2", context)
