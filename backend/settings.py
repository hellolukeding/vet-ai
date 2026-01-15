"""Application configuration using Pydantic settings."""

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Basic app settings
    DEBUG: bool = Field(description="Enable debug mode")
    HOST: str = Field(description="Host to bind the server to")
    PORT: int = Field(description="Port to bind the server to")

    # Security
    SECRET_KEY: str = Field(description="Secret key for JWT tokens")
    ALGORITHM: str = Field(description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(description="Access token expiration time in minutes")

    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(description="Allowed CORS origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(description="Allow credentials in CORS requests")
    CORS_ALLOW_METHODS: List[str] = Field(description="Allowed HTTP methods for CORS")
    CORS_ALLOW_HEADERS: List[str] = Field(description="Allowed headers for CORS requests")
    CORS_EXPOSE_HEADERS: List[str] = Field(description="Headers exposed to the browser")
    CORS_MAX_AGE: int = Field(description="Maximum age for CORS preflight cache (in seconds)")

    # Database Configuration
    MONGO_URI: str = Field(description="MongoDB connection URI")
    MONGO_DB_NAME: str = Field(description="MongoDB database name")

    # WebSocket Manager Configuration
    WORKSPACE_ROOT: str = Field(description="WebSocket管理器的内部工作空间根目录")
    EXTERNAL_WORKSPACE_ROOT: str = Field(description="WebSocket管理器的外部工作空间根目录")
    INSIDE_DOCKER: bool = Field(description="应用是否运行在Docker容器内")

    # LLM Configuration
    MODEL_NAME: Optional[str] = Field(default="deepseek-ai/DeepSeek-V3", description="Model name for LLM")
    BASE_URL: Optional[str] = Field(default="https://api-inference.modelscope.cn/v1", description="Base URL for LLM API")
    API_KEY: Optional[str] = Field(default="", description="API key for LLM service")

    # Task Queue Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL for task queue")
    TASK_QUEUE_MAX_CONCURRENT: int = Field(default=5, description="Maximum concurrent tasks for the queue")
    TASK_TIMEOUT: int = Field(default=600, description="Task timeout in seconds")
    TASK_RESULT_EXPIRE: int = Field(default=3600, description="Task result cache time in seconds")

    # Legacy database settings (kept for compatibility but not used)
    DATABASE_ECHO: bool = Field(description="Legacy setting, not used with MongoDB")

    class Config:
        """Pydantic configuration class."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def WEBSOCKET_CONFIG(self) -> dict:
        """获取WebSocket管理器配置"""
        return {
            "workspace_root": self.WORKSPACE_ROOT,
            "external_workspace_root": self.EXTERNAL_WORKSPACE_ROOT,
            "inside_docker": self.INSIDE_DOCKER,
            "debug": self.DEBUG
        }


settings = Settings()