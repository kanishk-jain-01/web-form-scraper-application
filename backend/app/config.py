from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # AI API Key
    model_api_key: Optional[str] = None
    
    # Browser automation
    browserbase_api_key: Optional[str] = None
    browserbase_project_id: Optional[str] = None
    
    # JWT Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
