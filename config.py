from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    origin_server: str
    google_oauth2_client_id: str
    admin_email: str

    class Config:
        env_file = ".env"

settings=Settings()
