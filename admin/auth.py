import urllib.parse
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import Depends, APIRouter, HTTPException, status, Response, Request, BackgroundTasks, Header, Cookie
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from data.db import User, UserBase, Sessions
from data.db import get_db
from admin.user import create as GetOrCreateUser

from typing import Annotated
from fastapi.security import APIKeyCookie

from google.oauth2 import id_token
from google.auth.transport import requests
from config import settings

from admin.cachestore import CacheStore, get_cache_store

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory='templates')

cookie_scheme = APIKeyCookie(name="session_id", description="Admin session_id is created by create_session.sh")

def hash_email(email: str):
    return hashlib.sha256(email.encode()).hexdigest()

def mutate_session(response: Response, old_session: dict, cs: CacheStore, immediate: bool = False):
    if not old_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if old_session["email"] == settings.admin_email:
        return old_session

    age_left = old_session["expires"] - int(datetime.now(timezone.utc).timestamp())
    if not immediate and age_left*2 > settings.session_max_age:
        print("Session still has much time: ", age_left, " seconds left.")
        return old_session

    print("Session expires soon in", age_left, ". Mutating the session.")
    session = cs.create_session(old_session["user_id"], old_session["email"])
    new_cookie(response, session)
    cs.delete_session(old_session["session_id"])
    return session

def new_cookie(response: Response, session: dict):
    if not session:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No session provided")

    max_age = settings.session_max_age
    # !!! Warining; It is very important to set httponly=True for the session_id cookie!!!
    response.set_cookie(key="session_id", value=session["session_id"], httponly=True,
                        samesite="Lax", secure=True, max_age=max_age, expires=session["expires"])
    response.set_cookie(key="csrf_token", value=session["csrf_token"], httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=session["expires"])
    response.set_cookie(key="user_token", value=hash_email(session["email"]), httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=session["expires"])
    return response

def delete_cookie(response: Response):
    max_age = 0
    expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
    response.set_cookie(key="session_id", value="", httponly=True,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
    response.set_cookie(key="csrf_token", value="", httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
    response.set_cookie(key="user_token", value="", httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
    return response

def csrf_verify(csrf_token: str, session: dict):
    print("### Debug: csrf_verify: ", csrf_token)
    if csrf_token == session['csrf_token']:
        return csrf_token
    elif csrf_token != session['csrf_token']:
        raise HTTPException(status_code=403, detail="CSRF token: "+csrf_token+" did not match the record.")
    else:
        raise HTTPException(status_code=403, detail="Unexpected things happend.")

def user_verify(user_token: str, session: dict):
    print("### Debug: user_verify: ", user_token)
    if user_token == hash_email(session["email"]):
        return user_token
    elif user_token != hash_email(session["email"]):
        raise HTTPException(status_code=403, detail="USER token: "+user_token+" did not match the record.")
    else:
        raise HTTPException(status_code=403, detail="Unexpected things happend.")

def get_user_by_user_id(user_id: int, ds: Session):
    user=ds.query(User).filter(User.id==user_id).first().__dict__
    return user

async def get_current_user(session_id: str = Depends(cookie_scheme),
                           ds: Session = Depends(get_db), cs: CacheStore = Depends(get_cache_store)):
    if not session_id:
        return None

    session = cs.get_session(session_id)
    if not session:
        return None

    user_dict = get_user_by_user_id(session["user_id"], ds)
    user=UserBase(**user_dict)
    return user

async def is_authenticated(session_id: str = Depends(cookie_scheme),
                           ds: Session = Depends(get_db), cs: CacheStore = Depends(get_cache_store)):

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

class RequiresLogin(Exception):
    pass

async def is_authenticated_admin(
                                 session_id: Annotated[str | None, Cookie()] = None,
                                 ds: Session = Depends(get_db),
                                 cs: CacheStore = Depends(get_cache_store)
                                 ):
    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)
    if not user:
        raise RequiresLogin("You must log in as Admin")
    if not user.disabled and user.admin:
        print("Authenticated as Admin.")
        return JSONResponse({"message": "Authenticated Admin"})
    raise RequiresLogin("You must log in as Admin")

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
async def login(request: Request, ds: Session = Depends(get_db), cs: CacheStore = Depends(get_cache_store)):

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

    response = JSONResponse({"Authenticated_as": user.name})
    session = cs.create_session(user.id, user.email)
    new_cookie(response, session)

    response.headers["HX-Trigger"] = "ReloadNavbar"

    return response

@router.get("/logout")
async def logout(response: Response,
                 session_id: Annotated[str | None, Cookie()] = None,
                 hx_request: Annotated[str | None, Header()] = None,
                 cs: CacheStore = Depends(get_cache_store)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    response = JSONResponse({"message": "user logged out"})
    response.headers["HX-Trigger"] = "ReloadNavbar, LogoutSecretContent"
    cs.delete_session(session_id)
    delete_cookie(response)
    return response

@router.get("/auth_navbar", response_class=HTMLResponse)
async def auth_navbar(request: Request,
                      session_id: Annotated[str|None, Cookie()] = None,
                      hx_request: Annotated[str|None, Header()] = None,
                      ds: Session = Depends(get_db), cs: CacheStore = Depends(get_cache_store)
                      ):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    # For authenticated users, return the menu.logout component.
    if user:
        logout_url = "/auth/logout"
        icon_url = "/img/logout.png"
        refresh_token_url = "/auth/refresh_token"
        mutate_user_url = "/auth/mutate_user"

        context = {"request": request, "logout_url":logout_url,
                   "icon_url": icon_url, "refresh_token_url": refresh_token_url, "mutate_user_url": mutate_user_url,
                   "name": user.name, "picture": user.picture, "userToken": hash_email(user.email)}
        return templates.TemplateResponse("auth_navbar.logout.j2", context)

    print("User not logged-in.")
    cs.cleanup_sessions()

    # For unauthenticated users, return the menu.login component.
    client_id = settings.google_oauth2_client_id
    login_url = "/auth/login"
    icon_url = "/img/icon.png"
    refresh_token_url = "/auth/refresh_token"
    mutate_user_url = "/auth/mutate_user"

    context = {"request": request, "client_id": client_id, "login_url": login_url,
               "icon_url": icon_url, "refresh_token_url": refresh_token_url, "mutate_user_url": mutate_user_url,
               "userToken": "anonymous"}
    response = templates.TemplateResponse("auth_navbar.login.j2", context)
    return response

@router.get("/check")
async def check(response: Response,
                session_id: Annotated[str|None, Cookie()] = None,
                hx_request: Annotated[str|None, Header()] = None,
                ds: Session = Depends(get_db), cs: CacheStore = Depends(get_cache_store)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    user = await get_current_user(session_id=session_id, cs=cs, ds=ds)

    if not user:
        response = JSONResponse({"message": "user logged out"})
        response.headers["HX-Trigger"] = "ReloadNavbar, LogoutSecretContent"
        return response

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/refresh_token")
async def refresh_token(response: Response,
                  hx_request: Annotated[str | None, Header()] = None,
                  session_id: Annotated[str | None, Cookie()] = None,
                  x_csrf_token: Annotated[str | None, Header()] = None,
                  x_user_token: Annotated[str | None, Header()] = None,
                  cs: CacheStore = Depends(get_cache_store)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point.")

    if not session_id:
        raise HTTPException(status_code=403, detail="No session_id in the request")

    session = cs.get_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="No session found for the session_id: "+session_id)

    try:
        csrf_verify(x_csrf_token, session)
        user_verify(x_user_token, session)
        new_session = mutate_session(response, session, cs, False)
        if new_session != session:
            print("Session mutated, new_session: ", new_session)
            response.headers["HX-Trigger"] = "ReloadNavbar"
        return {"ok": True, "new_session_id": new_session["session_id"]}
    except HTTPException as e:
        response = JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        response.headers["HX-Trigger"] = "ReloadNavbar, LogoutSecretContent"
        return response

@router.get("/mutate_user")
async def refresh_token(
                  hx_request: Annotated[str | None, Header()] = None,
                  x_user_token: Annotated[str | None, Header()] = None,
                  ):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point.")

    response = JSONResponse({"User mutated, new user": x_user_token})
    response.headers["HX-Trigger"] = "ReloadNavbar, LogoutSecretContent"
    return response

@router.get("/logout_content")
async def logout_content(request: Request,
                         hx_request: Annotated[str|None, Header()] = None):
    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    context = {"request": request, "message": "User logged out"}
    return templates.TemplateResponse("content.error.j2", context)

@router.get("/cleanup_sessions")
async def cleanup_sessions(
                         background_tasks: BackgroundTasks,
                         session_id: Annotated[str|None, Cookie()] = None,
                         cs: CacheStore = Depends(get_cache_store)):
    if not session_id:
        return {"message": "Session CleanUp not triggered. Please login first."}

    background_tasks.add_task(cs.cleanup_sessions)
    return {"message": "Session CleanUp triggered."}
