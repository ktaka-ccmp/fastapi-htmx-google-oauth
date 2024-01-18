from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from data.db import User, UserBase
from data.db import get_db

router = APIRouter()

def get_user_by_name(db_session: Session, name: str):
    return db_session.query(User).filter(User.name==name).first()

def get_user_by_email(db_session: Session, email: str):
    return db_session.query(User).filter(User.email==email).first()

def get_user_by_id(db_session: Session, user_id: int):
    return db_session.query(User).filter(User.id==user_id).first()

@router.get("/users/")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()

@router.get("/user/{name}")
def read_user_by_name(name: str, db_session: Session = Depends(get_db)):
    user = get_user_by_name(db_session, name)
    return user

async def create(idinfo: str, db_session: Session):
    email = idinfo['email']
    db_user = User(name=email, email=email)
    user = await create_user(db_user, db_session)
    return user

@router.post("/user/")
async def create_user(user: UserBase, db_session: Session = Depends(get_db)):
    db_user = get_user_by_email(db_session, user.email)
    if db_user:
        return db_user
    if not db_user:
        user_model = User(name=user.name, email=user.email)
        db_session.add(user_model)
        db_session.commit()
        db_session.refresh(user_model)
        db_user = get_user_by_email(db_session, user.email)
        return db_user

@router.delete("/user/{name}")
def delete_user(name: str, db_session: Session = Depends(get_db)):
    user = get_user_by_name(db_session, name)
    if not user:
        raise HTTPException(status_code=400, detail=f"\'{name}\' does not exist.")
    if user:
            db_session.delete(user)
            db_session.commit()
    return {"status": f"\'{name}\' has been deleted."}
