from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from sqlalchemy.orm import Session
from data.db import Customer, get_db

router = APIRouter()
templates = Jinja2Templates(directory='templates')

def get_customer_table_context(request, skip, limit, reset, db):
    customers = db.query(Customer).offset(skip).limit(limit).all()
    if reset:
        skip_next = 0
    else:
        skip_next = skip+limit
    context = {"request": request, "skip_next": skip_next, "limit": limit, 'customers': customers, "title": "Incremental hx-get demo"}
    return context

# Normal Response function
@router.get("/list", response_class=HTMLResponse)
async def list(request: Request, skip: int = 0, limit: int = 1, reset: bool = False, db: Session = Depends(get_db)):
    context = get_customer_table_context(request, skip, limit, reset, db)
    return templates.TemplateResponse("list.j2", context)

# HTMX Response function
@router.get("/hx_list", response_class=HTMLResponse)
async def hx_list(request: Request, skip: int = 0, limit: int = 1, reset: bool = False, hx_request: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )
    context = get_customer_table_context(request, skip, limit, reset, db)
    if reset:
        return templates.TemplateResponse("list.tbody_empty.j2", context)
    return templates.TemplateResponse("list.tbody.j2", context)
