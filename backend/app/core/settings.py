from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    # Application Configuration
    app_name: str = "FinanceBot API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # DynamoDB Configuration
    dynamodb_endpoint_url: str = "http://localhost:8000"  # For local development
    dynamodb_region: str = "us-east-1"
    dynamodb_access_key: str = "local"  # For local development
    dynamodb_secret_key: str = "local"  # For local development
    dynamodb_table_prefix: str = ""

    # JWT Configuration
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-large"

    # Pinecone Configuration
    pinecone_api_key: str = ""
    pinecone_index_name: str = "finance-bot"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # CORS Configuration
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Pagination
    default_page_size: int = 3
    max_page_size: int = 3

    class Config:
        env_file = ".env.local"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


# Create settings instance
settings = Settings()
