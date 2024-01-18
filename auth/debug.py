from fastapi import Depends, APIRouter, Request
from sqlalchemy.orm import Session
from data.db import UserBase, get_cache
from auth.auth import get_current_active_user, oauth2_scheme, get_session_by_session_id

router = APIRouter()

@router.get("/me")
async def dump_users_info(user: UserBase = Depends(get_current_active_user), session_id: str = Depends(oauth2_scheme), cs: Session = Depends(get_cache)):
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
