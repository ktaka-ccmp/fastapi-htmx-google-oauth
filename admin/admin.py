from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Response, status, Depends, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from data.db import get_cache

from admin.auth import get_session_by_session_id

router = APIRouter()

@router.get("/login")
def login_page():
    return HTMLResponse(
        """
        <form action="/admin/login" method="post">
        Admin Email: <input type="text" name="email" required>
        <br>
        ApiKey: <input type="text" name="apikey" required>
        <input type="submit" value="Login">
        </form>
        """
    )

@router.post("/login")
def login(response: Response, email: str = Form(...), apikey: str = Form(...), cs: Session = Depends(get_cache)):

    if not apikey or not email:
        return None

    session = get_session_by_session_id(apikey, cs)
    if not session:
        # raise HTTPException(
        #     status_code=status.HTTP_403_FORBIDDEN, detail="ApiKey not found"
        # )
        response = JSONResponse({"Error": "ApiKey not found"})
        response.delete_cookie("session_id")
        return response

    if email == session["email"]:
        max_age = 600
        expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
        # response = JSONResponse({"Authenticated_as": email})
        # response = RedirectResponse(url="/spa", status_code=status.HTTP_303_SEE_OTHER)
        response = RedirectResponse(url="/docs", status_code=status.HTTP_303_SEE_OTHER)
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
