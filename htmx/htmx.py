from typing import Optional
from fastapi import APIRouter, Request, Depends, Header 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from sqlalchemy.orm import Session
from data.db import Customer, get_db

router = APIRouter()
templates = Jinja2Templates(directory='templates')

# Ordinal API functions
@router.get("/")
async def json_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).offset(0).limit(100).all()
    return customers

# HTMX Response functions
@router.get("/list", response_class=HTMLResponse)
async def list(request: Request, skip: int = 0, limit: int = 1, reset: bool = False, hx_request: Optional[str] = Header(None), db: Session = Depends(get_db)):

    customers = db.query(Customer).offset(skip).limit(limit).all()

    if reset:
        skip_next = 0
    else:
        skip_next = skip+limit
    context = {"request": request, "skip_next": skip_next, "limit": limit, 'customers': customers}
 
    print("(skip, limit, reset) = (", skip, limit, reset,")")
    print("request.query_params:", dict(request.query_params))
    print("request.headers:", request.headers)

    if hx_request:
        if reset:
            return templates.TemplateResponse("list.reset.html", context)
        return templates.TemplateResponse("list.tbody.html", context)

    return templates.TemplateResponse("list.html", context)
