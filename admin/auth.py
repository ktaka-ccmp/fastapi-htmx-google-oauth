import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from fastapi import Depends, APIRouter, HTTPException, status, Response, Request, BackgroundTasks, Header, Cookie
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from data.db import User, UserBase, Sessions
from data.db import get_db, get_cache
from admin.user import create as GetOrCreateUser

from typing import Annotated
from fastapi.security import APIKeyCookie

from google.oauth2 import id_token
from google.auth.transport import requests
from config import settings

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory='templates')

cookie_scheme = APIKeyCookie(name="session_id", description="Admin session_id is created by create_session.sh")

def get_session_by_session_id(session_id: str, cs: Session):
    try:
        session=cs.query(Sessions).filter(Sessions.session_id==session_id).first().__dict__
        session.pop('_sa_instance_state')
        return session
    except:
        return None

def create_session(user: UserBase, expires: int, cs: Session):
    session_id=secrets.token_urlsafe(64)
    session = get_session_by_session_id(session_id, cs)
    if session:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Duplicate session_id")
    if not session:
        session_entry=Sessions(session_id=session_id, user_id=user.id, email=user.email, expires=expires)
        cs.add(session_entry)
        cs.commit()
        cs.refresh(session_entry)
    return session_id

def delete_session(session_id: str, cs: Session):
    session=cs.query(Sessions).filter(Sessions.session_id==session_id).first()
    print("delete session: ", session.__dict__)
    cs.delete(session)
    cs.commit()

def get_user_by_email(email: str, ds: Session):
    user=ds.query(User).filter(User.email==email).first().__dict__
    user.pop('_sa_instance_state')
    print("get_user_by_email -> user: ", user)
    return user

async def get_current_user(session_id: str = Depends(cookie_scheme),
                           ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
    if not session_id:
        return None

    session = get_session_by_session_id(session_id, cs)
    if not session:
        return None

    user_dict = get_user_by_email(session["email"], ds)
    user=UserBase(**user_dict)
    return user

async def is_authenticated(session_id: str = Depends(cookie_scheme),
                           ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NotAuthenticated"
        )
    elif user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Disabled user"
        )
    else:
        print("Authenticated.")
        return JSONResponse({"message": "Authenticated"})

async def VerifyToken(jwt: str):
    try:
        idinfo = id_token.verify_oauth2_token(
            jwt,
            requests.Request(),
            settings.google_oauth2_client_id)
    except ValueError:
        print("Error: Failed to validate JWT token with GOOGLE_OAUTH2_CLIENT_ID=" + settings.google_oauth2_client_id +".")
        return None

    print("idinfo: ", idinfo)
    return idinfo

@router.post("/login")
async def login(request: Request, ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):

    body = await request.body()
    jwt = dict(urllib.parse.parse_qsl(body.decode('utf-8'))).get('credential')

    idinfo = await VerifyToken(jwt)
    if not idinfo:
        print("Error: Failed to validate JWT token")
        return  Response("Error: Failed to validate JWT token")

    user = await GetOrCreateUser(idinfo, ds)
    if not user:
        print("Error: Failed to GetOrCreateUser")
        return  Response("Error: Failed to GetOrCreateUser for the JWT")

    max_age = 60
    expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)

    session_id = create_session(user, int(expires.timestamp()), cs)
    if not session_id:
        print("Error: Failed to create session for", user.name)
        return  Response("Error: Failed to create session for"+user.name)

    response = JSONResponse({"Authenticated_as": user.name})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        # secure=True,
        # domain="",
        max_age=max_age,
        expires=expires,
    )
    response.headers["HX-Trigger"] = "ReloadNavbar"

    return response

@router.get("/logout")
async def logout(response: Response,
                 session_id: Annotated[str | None, Cookie()] = None,
                 hx_request: Annotated[str | None, Header()] = None,
                 cs: Session = Depends(get_cache)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    response = JSONResponse({"message": "user logged out"})
    response.headers["HX-Trigger"] = "ReloadNavbar, LogoutContent"

    # The response.delete_cookie() must be called after response is defined, i.e. should be below the "response = ....".
    if session_id:
        delete_session(session_id, cs)
        response.delete_cookie("session_id") # delete key="session_id" from cookie of response

    return response

@router.get("/auth_navbar", response_class=HTMLResponse)
async def auth_navbar(request: Request,
                      session_id: Annotated[str|None, Cookie()] = None,
                      hx_request: Annotated[str|None, Header()] = None,
                      ds: Session = Depends(get_db), cs: Session = Depends(get_cache)
                      ):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    # For authenticated users, return the menu.logout component.
    if user:
        logout_url = settings.origin_server + "/auth/logout"
        icon_url = settings.origin_server + "/img/logout.png"

        context = {"request": request, "session_id": session_id, "logout_url":logout_url, "icon_url": icon_url,
                   "name": user.name, "picture": user.picture, "email": user.email}
        return templates.TemplateResponse("auth_navbar.logout.j2", context)

    print("User not logged-in.")
    do_cleanup_sessions(cs)

    # For unauthenticated users, return the menu.login component.
    client_id = settings.google_oauth2_client_id
    login_url = settings.origin_server + "/auth/login"
    icon_url = settings.origin_server + "/img/icon.png"

    context = {"request": request, "client_id": client_id, "login_url": login_url, "icon_url": icon_url}
    response = templates.TemplateResponse("auth_navbar.login.j2", context)
    return response

@router.get("/check")
async def check(response: Response,
                session_id: Annotated[str|None, Cookie()] = None,
                hx_request: Annotated[str|None, Header()] = None,
                ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    if not user:
        response = JSONResponse({"message": "user logged out"})
        response.headers["HX-Trigger"] = "ReloadNavbar, LogoutContent"
        return response

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/logout_content")
async def logout_content(request: Request,
                         session_id: Annotated[str|None, Cookie()] = None,
                         hx_request: Annotated[str|None, Header()] = None,
                         ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    if not user:
        context = {"request": request, "message": "User logged out"}
        return templates.TemplateResponse("content.error.j2", context)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

def do_cleanup_sessions(cs: Session):
    now = int(datetime.now().timestamp())
    session=cs.query(Sessions).filter(Sessions.expires<=now).all()
    for row in session:
        print("delete session: ", row.__dict__)
    session=cs.query(Sessions).filter(Sessions.expires<=now).delete()
    cs.commit()
    print("Finished do_cleanup_sessions")

@router.get("/cleanup_sessions")
async def cleanup_sessions(
                         background_tasks: BackgroundTasks,
                         session_id: Annotated[str|None, Cookie()] = None,
                         cs: Session = Depends(get_cache)):
    if not session_id:
        return {"message": "Session CleanUp not triggered. Please login first."}

    background_tasks.add_task(do_cleanup_sessions, cs)
    return {"message": "Session CleanUp triggered."}
