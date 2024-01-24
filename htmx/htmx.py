from typing import Optional, Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse

from sqlalchemy.orm import Session
from data.db import Customer, get_db

router = APIRouter()
templates = Jinja2Templates(directory='templates')

@router.get("/spa", response_class=HTMLResponse)
async def spa(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("spa.j2", context)

@router.get("/content.top", response_class=HTMLResponse)
async def spa_content(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "title": "Htmx Spa Top"}
    return templates.TemplateResponse("content.top.j2", context)

# HTMX Incremental table update
@router.get("/content.list", response_class=HTMLResponse)
async def content_list(request: Request, skip: int = 0, limit: int = 2, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "skip_next": skip, "limit": limit, "title": "Incremental hx-get demo"}
    return templates.TemplateResponse("content.list.j2", context)

@router.get("/content.list.tbody", response_class=HTMLResponse)
async def content_list_tbody(request: Request, skip: int = 0, limit: int = 1, hx_request: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    customers = db.query(Customer).offset(skip).limit(limit).all()
    context = {"request": request, "skip_next": skip+limit, "limit": limit, 'customers': customers}
    return templates.TemplateResponse("content.list.tbody.j2", context)

# HTMX Login status change
@router.get("/content.error", response_class=HTMLResponse)
async def content_error(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "message": "Login status changed"}
    return templates.TemplateResponse("content.error.j2", context)
