from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, status, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi import docs, utils
from sqlalchemy.orm import Session

from data import db
from admin import auth
from config import settings

router = APIRouter()

@router.post("/login")
def login(response: Response, email: str = Form(...),
          apikey: str = Form(...), cs: Session = Depends(db.get_cache)):

    if not apikey or not email:
        return None

    session = auth.get_session_by_session_id(apikey, cs)
    if not session:
        response = JSONResponse({"Error": "ApiKey not found"})
        response.delete_cookie("session_id")
        return response

    if email == session["email"]:
        max_age = settings.session_max_age
        expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
        response = RedirectResponse(url="/docs",
                                    status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="session_id", value=apikey, httponly=True,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
        response.set_cookie(key="csrf_token", value=session["csrf_token"], httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
        response.set_cookie(key="user_token", value=auth.hash_email(email), httponly=False,
                        samesite="Lax", secure=True, max_age=max_age, expires=expires,)
        return response

    response = JSONResponse({"Error": "Invalid ApiKey"})
    response.delete_cookie("session_id")
    return response

doc_router = APIRouter()

@doc_router.get("/docs")
async def get_documentation():
    return docs.get_swagger_ui_html(
        openapi_url="/openapi.json", title="docs")

@doc_router.get("/redoc")
async def get_redoc_documentation():
    return docs.get_redoc_html(
        openapi_url="/openapi.json", title="docs")

@doc_router.get("/openapi.json")
async def openapi(request: Request):
    return utils.get_openapi(
        title= request.app.title,
        version=request.app.version,
        routes=request.app.routes)
