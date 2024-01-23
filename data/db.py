# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Boolean

DATA_STORE_URI = "sqlite:///data/data.db"

DataStore = create_engine(
    DATA_STORE_URI, connect_args={"check_same_thread": False}, echo=False
)
SessionDATA = sessionmaker(autocommit=False, autoflush=False, bind=DataStore)

CACHE_STORE_URI = "sqlite:///data/cache.db"

CacheStore = create_engine(
    CACHE_STORE_URI, connect_args={"check_same_thread": False}, echo=False
)
SessionCACHE = sessionmaker(autocommit=False, autoflush=False, bind=CacheStore)

DataStoreBase = declarative_base()
CacheStoreBase = declarative_base()

# models.py
from sqlalchemy import Boolean, Column, Integer, String

class Customer(DataStoreBase):
    __tablename__ = 'customer'
    id = Column('id', Integer, primary_key = True, autoincrement = True)
    name = Column('name', String(30))
    email = Column('email', String(254))

class User(DataStoreBase):
    __tablename__ = 'user'
    id = Column('id', Integer, primary_key = True, autoincrement = True)
    name = Column('name', String(30))
    email = Column('email', String(254))
    disabled = Column('disabled', Boolean, default=False)
    admin = Column('admin', Boolean, default=False)
    password = Column('password', String(254))
    picture = Column('picture', String(1024))

class Sessions(CacheStoreBase):
    __tablename__ = 'sessions'
    id = Column('id', Integer, primary_key = True, autoincrement = True)
    session_id = Column('session_id', String(64))
    user_id = Column('user_id', Integer)
    email = Column('email', String(254))

# schemas.py
from pydantic import BaseModel, EmailStr, HttpUrl

class CustomerBase(BaseModel):
    id: int
    name: str
    email: EmailStr
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    id: int
    name: str
    email: EmailStr
    disabled: bool
    admin: bool
    password: str | None
    picture: HttpUrl | None
    class Config:
        from_attributes = True

DataStoreBase.metadata.create_all(bind=DataStore)
CacheStoreBase.metadata.create_all(bind=CacheStore)

def get_db():
    ds = SessionDATA()
    try:
        yield ds
    finally:
        ds.close()

def get_cache():
    cs = SessionCACHE()
    try:
        yield cs
    finally:
        cs.close()

