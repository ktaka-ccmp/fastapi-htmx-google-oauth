from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Response, status, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from data import db
from admin import auth

router = APIRouter()

@router.post("/login")
def login(response: Response, email: str = Form(...), apikey: str = Form(...), cs: Session = Depends(db.get_cache)):

    if not apikey or not email:
        return None

    session = auth.get_session_by_session_id(apikey, cs)
    if not session:
        response = JSONResponse({"Error": "ApiKey not found"})
        response.delete_cookie("session_id")
        return response

    if email == session["email"]:
        max_age = 600
        expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
        response = RedirectResponse(url="/admin/docs", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="session_id",
            value=apikey,
            httponly=True,
            samesite="lax",
            # secure=True,
            # domain="",
            max_age=max_age,
            expires=expires,
        )
        return response

    response = JSONResponse({"Error": "Invalid ApiKey"})
    response.delete_cookie("session_id")
    return response
