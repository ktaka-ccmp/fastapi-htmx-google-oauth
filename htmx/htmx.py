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
    context = {"request": request, "title": "Spa Top Page"}
    return templates.TemplateResponse("spa.j2", context)

@router.get("/content", response_class=HTMLResponse)
async def spa_content(request: Request, hx_request: Optional[str] = Header(None)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = {"request": request, "title": "Spa Top Page"}
    return templates.TemplateResponse("content.j2", context)

# HTMX Response function
@router.get("/content.list.tbody", response_class=HTMLResponse)
async def content_list_tbody(request: Request, skip: int = 0, limit: int = 1, reset: bool = False, hx_request: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = get_customer_table_context(request, skip, limit, reset, db)
    return templates.TemplateResponse("content.list.tbody.j2", context)

@router.get("/content.list", response_class=HTMLResponse)
async def content_list(request: Request, skip: int = 0, limit: int = 2, reset: bool = False, hx_request: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = get_customer_table_context(request, skip, limit, reset, db)
    return templates.TemplateResponse("content.list.j2", context)

def get_customer_table_context(request, skip, limit, reset, db):
    customers = db.query(Customer).offset(skip).limit(limit).all()
    if reset:
        skip_next = 0
    else:
        skip_next = skip+limit
    context = {"request": request, "skip_next": skip_next, "limit": limit, 'customers': customers, "title": "Incremental hx-get demo"}
    return context


@router.get("/icon.png")
async def main():
    return FileResponse("images/unknown-person-icon.png")

@router.get("/logout.png")
async def main():
    return FileResponse("images/door-check-out-icon.png")