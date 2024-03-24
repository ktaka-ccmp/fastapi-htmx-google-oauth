import secrets, json
import redis
from typing import Optional
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from fastapi import HTTPException, status, Depends
from sqlalchemy.exc import SQLAlchemyError, NoResultFound

from data.db import Sessions, get_cache
from config import settings

class CacheStore(ABC):

    @abstractmethod
    def get_session(self, session_id: str):
        pass

    @abstractmethod
    def create_session(self, user_id: int, email: str):
        pass

    @abstractmethod
    def delete_session(self, session_id: str):
        pass

    @abstractmethod
    def cleanup_sessions(self):
        pass

class SQLCacheStore(CacheStore):
    def __init__(self, db_session):
        self.cs = db_session

    def get_session(self, session_id: str):
        try:
            session = self.cs.query(Sessions).filter(Sessions.session_id == session_id).one()
            return session.__dict__
        except NoResultFound:
            return None
        except SQLAlchemyError as e:
            print(f"An error occurred while retrieving the session: {e}")
            return None

    def create_session(self, user_id: int, email: str):
        session_id = secrets.token_urlsafe(64)
        csrf_token = secrets.token_urlsafe(32)

        session = self.get_session(session_id)
        if session:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Duplicate session_id")

        expires = int((datetime.now(timezone.utc) 
                       + timedelta(seconds=settings.session_max_age)).timestamp())

        session_entry = Sessions(session_id=session_id, csrf_token=csrf_token,
                                 user_id=user_id, email=email, expires=expires)
        self.cs.add(session_entry)
        self.cs.commit()
        self.cs.refresh(session_entry)
        return session_entry.__dict__

    def delete_session(self, session_id: str):
        session = self.cs.query(Sessions).filter(Sessions.session_id == session_id).first()
        if session:
            self.cs.delete(session)
            self.cs.commit()

    def cleanup_sessions(self):
        now = int(datetime.now().timestamp())
        expired_sessions = self.cs.query(Sessions).filter(Sessions.expires <= now).all()
        for session in expired_sessions:
            print("Cleaning up expired session: ", session.session_id)
            self.cs.delete(session)
        self.cs.commit()
        
class RedisCacheStore(CacheStore):

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True)

    def get_session(self, session_id: str) -> Optional[dict]:
        session_data = self.redis_client.get(f"session:{session_id}")
        return json.loads(session_data) if session_data else None

    def create_session(self, user_id: int, email: str):
        session_id = secrets.token_urlsafe(64)
        csrf_token = secrets.token_urlsafe(32)
        expires = settings.session_max_age
        session_data = {
            "session_id": session_id,
            "csrf_token": csrf_token,
            "user_id": user_id,
            "email": email,
            "expires": int((datetime.now(timezone.utc) + timedelta(seconds=expires)).timestamp())
        }
        self.redis_client.setex(f"session:{session_id}", expires, json.dumps(session_data))
        return session_data

    def delete_session(self, session_id: str):
        self.redis_client.delete(f"session:{session_id}")

    def cleanup_sessions(self):
        # Redis handles session expiration automatically based on the TTL set during creation.
        pass

def get_cache_store():
    if settings.cache_store == 'redis':
        return RedisCacheStore()
    elif settings.cache_store == 'sql':
        cs = next(get_cache())
        return SQLCacheStore(cs)


def example_route(cs: CacheStore = Depends(get_cache_store)):
    session_id = "example_session_id" # Normally, you would get this from the request cookies
    session = cs.get_session(session_id)
    if session:
        return {"message": "Session found", "session": session}
    else:
        return {"message": "Session not found"}


