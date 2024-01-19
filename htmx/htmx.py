from typing import Optional
from fastapi import APIRouter, Request, Response, status, Depends, Header, HTTPException 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

from sqlalchemy.orm import Session
from data.db import Customer, UserBase, get_db, get_cache

from auth.auth import get_current_active_user, get_current_user, delete_session, VerifyToken, GetOrCreateUser, get_user_by_name,create_session
import urllib.parse

router = APIRouter()
templates = Jinja2Templates(directory='htmx/templates')

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

@router.get("/auth_component", response_class=HTMLResponse)
async def list(request: Request, hx_request: Optional[str] = Header(None), ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
    try:
        session_id = request.cookies.get("session_id")
        user = await get_current_user(session_id=session_id, cs=cs, ds=ds)
        user = await get_current_active_user(user)
    except:
        print("Exception getting user")

    if hx_request:
        if session_id:
            context = {"request": request, "session_id": session_id, "username": user.name}
            return templates.TemplateResponse("auth.logout.html", context)
        else:
            context = {"request": request}
            return templates.TemplateResponse("auth.google.html", context)

    context = {"request": request, "session_id": session_id}
    return templates.TemplateResponse("auth.google.html", context)

@router.get("/logout")
async def logout(request: Request, response: Response, cs: Session = Depends(get_cache)):

    # context = {"request": request}
    # response = templates.TemplateResponse("auth.google.html", context)

    response = JSONResponse({"message": "Session deleted"})

    response.headers["HX-Trigger"] = "showComponent"
    response.delete_cookie("session_id")

    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id, cs)
    else:
        print("No session_id found.")

    return response

@router.post("/login")
async def login(request: Request, ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
    body = await request.body()
    jwt = dict(urllib.parse.parse_qsl(body.decode('utf-8'))).get('credential')

    # referer = request.headers.get("Referer")
    # print("##### Referer: " + referer)

    idinfo = await VerifyToken(jwt)
    if not idinfo:
        print("Error: Failed to validate JWT token")
        return  Response("Error: Failed to validate JWT token")

    user = await GetOrCreateUser(idinfo, ds)

    if user:
        user_dict = get_user_by_name(user.name, ds)
        if not user_dict:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: User not exist in User table in DB.")
        user = UserBase(**user_dict)
        session_id = create_session(user, cs)

        # context = {"request": request, "session_id": session_id, "username": user.name}
        # response = templates.TemplateResponse("auth.logout.html", context)

        # response = RedirectResponse(referer, status_code=status.HTTP_303_SEE_OTHER)
        response = JSONResponse({"Authenticated_as": user.name})

        # response.headers["HX-Trigger"] = "showComponent"
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=180,
            expires=180,
        )
        return response
    else:
        return Response("Error: Auth failed")
