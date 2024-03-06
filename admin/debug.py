from config import settings
from fastapi import APIRouter, HTTPException, Response, Request, Depends, Cookie, Header, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Annotated
from sqlalchemy.orm import Session
from data.db import Sessions, UserBase, get_cache
from admin.auth import get_current_user, get_session_by_session_id

router = APIRouter()
templates = Jinja2Templates(directory='templates')

@router.get("/sessions")
async def list_sessions(cs: Session = Depends(get_cache)):
    return cs.query(Sessions).offset(0).limit(100).all()

@router.get("/env/")
async def env():
    print("settings: ", settings)
    return {
        "origin_server": settings.origin_server,
        "google_oauth2_client_id": settings.google_oauth2_client_id,
        }

@router.get("/me")
async def dump_users_info(request: Request, user: UserBase = Depends(get_current_user), cs: Session = Depends(get_cache)):
    session_id = request.cookies.get("session_id")
    session = get_session_by_session_id(session_id, cs)
    try:
        return {"user": user, "session": session}
    except:
        return None

@router.get("/debug_headers")
async def debug_headers(request: Request):
    headers = request.headers
    print("Headers: ", headers)
    return{"Headers": headers}

from admin import auth

@router.get("/refresh_token")
def refresh_token(response: Response,
                  session_id: Annotated[str | None, Cookie()] = None,
                  cs: Session = Depends(get_cache)):
    print("session_id: ", session_id)
    try:
        new_session_id, new_csrf_token = auth.mutate_session(response, session_id, cs)
        return {"ok": True, "new_token": new_session_id, "csrf_token": new_csrf_token}
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

@router.get("/csrf_js")
async def debug_csrf(request: Request):
    context = {"request": request, "url":"/debug/csrf_js"}
    return templates.TemplateResponse("debug_csrf_js.j2", context)

@router.post("/csrf_js")
def csrf_protect(
                # x_csrf_token: str = Header(...),
                x_csrf_token: Annotated[str | None, Header()] = None,
                session_id: Annotated[str | None, Cookie()] = None,
                cs: Session = Depends(get_cache)):
    csrf_token = x_csrf_token
    session = get_session_by_session_id(session_id,cs)
    if not session or csrf_token != session['csrf_token']:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
    return {"ok": True, "csrf_token": csrf_token}

@router.get("/csrf_html", response_class=HTMLResponse)
async def get_form(request: Request,
                   csrf_token: Annotated[str | None, Cookie()] = None):
    print("csrf_token: ", csrf_token)
    context = {"request": request, "csrf_token": csrf_token, "url":"/debug/csrf_html"}
    response = templates.TemplateResponse("debug_csrf_html.j2", context)
    return response

@router.post("/csrf_html")
async def submit_form(csrf_token: Annotated[str | None, Form()] = None,
                      session_id: Annotated[str | None, Cookie()] = None,
                      cs: Session = Depends(get_cache)):
    session = get_session_by_session_id(session_id,cs)
    if not session or csrf_token != session['csrf_token']:
            raise HTTPException(status_code=403, detail="CSRF token mismatch")
    return {"ok": True, "csrf_token": csrf_token}
