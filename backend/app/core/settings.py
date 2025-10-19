from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Application Configuration
    app_name: str = "FinanceBot API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = os.getenv("ENVIRONMENT")

    # DynamoDB Configuration
    dynamodb_endpoint_url: str = os.getenv("DYNAMODB_ENDPOINT_URL")
    dynamodb_region: str = os.getenv("DYNAMODB_REGION")
    dynamodb_access_key: str = os.getenv("DYNAMODB_ACCESS_KEY")
    dynamodb_secret_key: str = os.getenv("DYNAMODB_SECRET_KEY")
    dynamodb_table_prefix: str = os.getenv("DYNAMODB_TABLE_PREFIX")

    # JWT Configuration
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = os.getenv("ALGORITHM")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "2")
    )  # 2 minutes
    refresh_token_expire_minutes: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "4")
    )  # 5 minutes

    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL")

    # Pinecone Configuration
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME")

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL")

    # CORS Configuration
    allowed_origins: List[str] = (
        os.getenv("ALLOWED_ORIGINS").split(",") if os.getenv("ALLOWED_ORIGINS") else []
    )

    # Rate Limiting
    rate_limit_per_minute: int = os.getenv("RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = os.getenv("RATE_LIMIT_BURST")

    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY")

    # Pagination
    default_page_size: int = os.getenv("DEFAULT_PAGE_SIZE")
    max_page_size: int = os.getenv("MAX_PAGE_SIZE")

    # RAG
    similarity_threshold: float = os.getenv("SIMILARITY_THRESHOLD")
    default_top_k: int = os.getenv("DEFAULT_TOP_K")

    class Config:
        env_file = ".env.local"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


# Create settings instance
settings = Settings()
