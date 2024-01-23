from config import settings
from fastapi import Depends, APIRouter, Request
from sqlalchemy.orm import Session
from data.db import Sessions, UserBase, get_cache
from admin.auth import get_current_user, get_session_by_session_id

router = APIRouter()

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
