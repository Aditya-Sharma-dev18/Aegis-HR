from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    # App Info
    PROJECT_NAME: str = "Aegis-Core HR Engine"
    VERSION: str = "1.0.0"
    
    # AI APIs
    GROQ_API_KEY: SecretStr
    TAVILY_API_KEY: SecretStr
    COHERE_API_KEY: SecretStr
    
    # Vector DB
    PINECONE_API_KEY: SecretStr
    PINECONE_INDEX_NAME: str
    
    # Database (Async Postgres)
    DATABASE_URL: str
    
    # Security / JWT (RBAC Foundation)
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # This tells Pydantic to read from your .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
# Instantiate the settings so they can be imported anywhere in the app
settings = Settings()