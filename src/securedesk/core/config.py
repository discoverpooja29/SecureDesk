from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    refresh_session_days: int = Field(default=7, gt=0)
    
    model_config = SettingsConfigDict(env_file="src/securedesk/.env")
    
settings = Settings() #pyright: ignore[reportCallIssue]