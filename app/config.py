"""
Configuration management for the Centuries Mutual Home App
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    """Application settings with environment variable support"""
    
    # Application Configuration
    app_name: str = Field(default="Centuries Mutual Home App", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Dropbox Configuration
    dropbox_access_token: str = Field(..., env="DROPBOX_ACCESS_TOKEN")
    dropbox_app_key: str = Field(..., env="DROPBOX_APP_KEY")
    dropbox_app_secret: str = Field(..., env="DROPBOX_APP_SECRET")
    
    # RabbitMQ Configuration
    rabbitmq_host: str = Field(default="localhost", env="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, env="RABBITMQ_PORT")
    rabbitmq_username: str = Field(default="guest", env="RABBITMQ_USERNAME")
    rabbitmq_password: str = Field(default="guest", env="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(default="/", env="RABBITMQ_VHOST")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Security Configuration
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Rate Limiting
    daily_message_limit: int = Field(default=10, env="DAILY_MESSAGE_LIMIT")
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    
    # Webhook Configuration
    webhook_secret: str = Field(..., env="WEBHOOK_SECRET")
    webhook_base_url: str = Field(..., env="WEBHOOK_BASE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
