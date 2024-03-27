import secrets, json
import redis
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, NoResultFound

from data.db import Sessions, get_cache
from config import settings

class CacheStore(ABC):

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict]:
        pass

    def list_sessions(self) -> List[Dict]:
        pass

    @abstractmethod
    def create_session(self, user_id: int, email: str) -> Dict:
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        pass

    @abstractmethod
    def cleanup_sessions(self) -> None:
        pass

class SQLCacheStore(CacheStore):
    def __init__(self, db_session):
        self.cs = db_session

    def get_session(self, session_id: str) -> Optional[Dict]:
        try:
            session_data = self.cs.query(Sessions).filter(Sessions.session_id == session_id).one()
        except NoResultFound:
            return None
        except SQLAlchemyError as e:
            print(f"An error occurred while retrieving the session: {e}")
            raise RuntimeError(f"An error occurred while retrieving the session: {e}")

        if session_data:
            session = session_data.__dict__
            print("session: ", session)
            print("session_id: ", session["session_id"])
            return session
        else:
            return None

    def list_sessions(self) -> List[Dict]:
        sessions = self.cs.query(Sessions).offset(0).limit(100).all()
        return [session.__dict__ for session in sessions]

    def create_session(self, user_id: int, email: str) -> Dict:
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

    def delete_session(self, session_id: str) -> None:
        session = self.cs.query(Sessions).filter(Sessions.session_id == session_id).first()
        # session is not dict
        if session.email == settings.admin_email:
            return
        if session:
            self.cs.delete(session)
            self.cs.commit()

    def cleanup_sessions(self) -> None:
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
        session = json.loads(session_data) if session_data else None
        if session:
            print("session: ", session)
            print("session_id: ", session["session_id"])
        return session

    def list_sessions(self) -> List[Dict]:
        sessions = []
        for key in self.redis_client.scan_iter(match="session:*"):
            session_data = self.redis_client.get(key)
            session = json.loads(session_data)
            sessions.append(session)
        return sessions

    def create_session(self, user_id: int, email: str) -> Dict:
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

    def delete_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        # session is dict
        if session["email"] == settings.admin_email:
            return
        self.redis_client.delete(f"session:{session_id}")

    def cleanup_sessions(self) -> None:
        # Redis handles session expiration automatically based on the TTL set during creation.
        pass

def get_cache_store() -> CacheStore:
    if settings.cache_store == 'redis':
        return RedisCacheStore()
    elif settings.cache_store == 'sql':
        cs = next(get_cache())
        return SQLCacheStore(cs)

