import secrets
import urllib.parse
from fastapi import Depends, APIRouter, HTTPException, status, Response, Request, Header
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from data.db import User, UserBase, Sessions
from data.db import get_db, get_cache
from admin.user import create as GetOrCreateUser

from typing import Optional
from fastapi.security import OAuth2PasswordBearer

from google.oauth2 import id_token
from google.auth.transport import requests
from config import settings

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory='templates')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_session_by_session_id(session_id: str, cs: Session):
    try:
        session=cs.query(Sessions).filter(Sessions.session_id==session_id).first().__dict__
        session.pop('_sa_instance_state')
        return session
    except:
        return None

def create_session(user: UserBase, cs: Session):
    session_id=secrets.token_urlsafe(32)
    session = get_session_by_session_id(session_id, cs)
    if session:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Duplicate session_id")
    if not session:
        session_entry=Sessions(session_id=session_id, user_id=user.id, email=user.email)
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

# async def get_current_user(session_id: str, ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
# "dummy: str = Depends(oauth2_scheme)" is to show "Authorize" in swagger UI.
# The "lock icon" is also shown in routes that depend on "get_current_user".
async def get_current_user(session_id: str, ds: Session = Depends(get_db), cs: Session = Depends(get_cache), dummy: str = Depends(oauth2_scheme)):

    if not session_id:
        return None

    session = get_session_by_session_id(session_id, cs)
    if not session:
        return None

    user_dict = get_user_by_email(session["email"], ds)
    user=UserBase(**user_dict)

    print("Session_id: ", session_id)
    print("Session: ", session)
    print("session[\"email\"]: ", session["email"])
    print("user_dict: ", user_dict)
    print("user: ", user)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NotAuthenticated"
            )
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Disabled user"
            )

    return user

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

    if user:
        user_dict = get_user_by_email(user.email, ds)
        if not user_dict:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error: User not exist in User table in DB."
                )
        user = UserBase(**user_dict)
        session_id = create_session(user, cs)

        response = JSONResponse({"Authenticated_as": user.name})
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=600,
            expires=600,
        )

        return response
    else:
        return Response("Error: Auth failed")

@router.get("/logout")
async def logout(request: Request, response: Response, cs: Session = Depends(get_cache)):

    response = JSONResponse({"message": "Session deleted"})
    response.headers["HX-Trigger"] = "showComponent"
    response.delete_cookie("session_id")

    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id, cs)
    else:
        print("No session_id found.")

    return response

@router.get("/auth_component", response_class=HTMLResponse)
async def auth_component(request: Request, hx_request: Optional[str] = Header(None), ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):

    if not hx_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HX request is allowed to this end point."
            )

    # For authenticated users, return the logout component.
    try:
        session_id = request.cookies.get("session_id")
        user = await get_current_user(session_id=session_id, cs=cs, ds=ds)
        context = {"request": request, "session_id": session_id, "name": user.name, "picture": user.picture, "email": user.email}
        return templates.TemplateResponse("auth.logout.j2", context)
    except:
        print("User not logged-in.")

    # For unauthenticated users, return the login component.
    client_id = settings.google_oauth2_client_id
    login_url = settings.origin_server + "/api/login"

    context = {"request": request, "client_id": client_id, "login_url": login_url}
    return templates.TemplateResponse("auth.login.google.j2", context)
