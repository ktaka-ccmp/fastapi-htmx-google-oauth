import secrets
import urllib.parse
from fastapi import Depends, APIRouter, HTTPException, status, Response, Request, Header
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from data.db import User, UserBase, Sessions
from data.db import get_db, get_cache
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR
from admin.user import create as GetOrCreateUser

from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm, OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

from google.oauth2 import id_token
from google.auth.transport import requests
from config import settings

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory='templates')

class OAuth2Cookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str = None,
        scopes: dict = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        session_id: str = request.cookies.get("session_id")
        if not session_id:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            else:
                return None
        return session_id

def fake_hash_password(password: str):
    return "fakehashed_" + password

@router.post("/signin")
async def signin(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
    user_dict = get_user_by_name(form_data.username, ds)
    if not user_dict:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Incorrect username or password")
    if not user_dict['admin']:
        raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="No Admin Privilege"
                )
    if user_dict['disabled']:
        raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Disabled Admin"
                )
    user = UserBase(**user_dict)

    if user.password == None:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Empty Password not Allowed for Admin")

    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user.password:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    session_id=create_session(user, cs)
    response.set_cookie(
                  key="session_id",
                  value=session_id,
                  httponly=True,
                  max_age=1800,
                  expires=1800,
    )
    return {"access_token": user.name, "token_type": "bearer"}

oauth2_scheme = OAuth2Cookie(tokenUrl="/api/signin", auto_error=False)

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
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Duplicate session_id")
    if not session:
        session_entry=Sessions(session_id=session_id, user_id=user.id, name=user.name)
        cs.add(session_entry)
        cs.commit()
        cs.refresh(session_entry)
    return session_id

def delete_session(session_id: str, cs: Session):
    session=cs.query(Sessions).filter(Sessions.session_id==session_id).first()
    print("delete session: ", session.__dict__)
    cs.delete(session)
    cs.commit()

def get_user_by_name(name: str, ds: Session):
    user=ds.query(User).filter(User.name==name).first().__dict__
    user.pop('_sa_instance_state')
    print("get_user_by_name -> user: ", user)
    return user

async def get_current_user(ds: Session = Depends(get_db), cs: Session = Depends(get_cache), session_id: str = Depends(oauth2_scheme)):

    if not session_id:
        return None
    session = get_session_by_session_id(session_id, cs)
    if not session:
        return None

    username = session["name"]
    user_dict = get_user_by_name(username, ds)
    user=UserBase(**user_dict)
    print("Session_id: ", session_id)
    print("Session: ", session)
    print("session[\"name\"]: ", session["name"])
    print("user_dict: ", user_dict)
    print("user: ", user)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="NotAuthenticated")
    if current_user.disabled:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    print("CurrentUser: ", current_user)
    if not current_user.admin:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Admin Privilege Required")
    return current_user

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
        user_dict = get_user_by_name(user.name, ds)
        if not user_dict:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: User not exist in User table in DB.")
        user = UserBase(**user_dict)
        session_id = create_session(user, cs)

        response = JSONResponse({"Authenticated_as": user.name})
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

@router.get("/user/")
async def get_user(user: UserBase = Depends(get_current_active_user)):
    try:
        return {"username": user.name, "email": user.email,}
    except:
        return None

@router.get("/auth_component", response_class=HTMLResponse)
async def list(request: Request, hx_request: Optional[str] = Header(None), ds: Session = Depends(get_db), cs: Session = Depends(get_cache)):
    try:
        session_id = request.cookies.get("session_id")
        user = await get_current_user(session_id=session_id, cs=cs, ds=ds)
        user = await get_current_active_user(user)
    except:
        print("Exception getting user")

    client_id = settings.google_oauth2_client_id
    login_url = settings.origin_server + "/api/login"

    if hx_request:
        if session_id:
            try:
                context = {"request": request, "session_id": session_id, "name": user.name, "picture": user.picture, "email": user.email}
                return templates.TemplateResponse("auth.logout.html", context)
            except:
                pass
        context = {"request": request, "client_id": client_id, "login_url": login_url}
        return templates.TemplateResponse("auth.login.google.html", context)

    context = {"request": request, "session_id": session_id}
    return templates.TemplateResponse("auth.login.google.html", context)
