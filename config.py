from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    origin_server: str
    google_oauth2_client_id: str
    admin_email: str
    session_max_age: int
    cache_store: str
    redis_host: str
    redis_port: int

    class Config:
        env_file = ".env"

settings=Settings()
