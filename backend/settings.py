"""Application configuration using Pydantic settings."""

from typing import Any, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def parse_list_env(value: Any) -> List[str]:
    """解析环境变量中的列表值

    支持以下格式：
    - "*" 或 "all" -> ["*"] (允许所有来源)
    - JSON 字符串: '["http://example.com", "https://example.com"]'
    - 逗号分隔: "http://example.com,https://example.com"
    - None 或空字符串 -> 返回默认值
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        # 处理空字符串
        if not value.strip():
            return []

        # 处理通配符
        if value.strip() in ["*", "all"]:
            return ["*"]

        # 尝试解析 JSON
        try:
            import json
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # 使用逗号分隔
        return [item.strip() for item in value.split(",") if item.strip()]

    return []


class Settings(BaseSettings):
    """Application settings."""

    # Basic app settings
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(default=8080, description="Port to bind the server to")

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT tokens")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration time in minutes")

    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS requests")
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"], description="Allowed HTTP methods for CORS")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="Allowed headers for CORS requests")
    CORS_EXPOSE_HEADERS: List[str] = Field(default=[], description="Headers exposed to the browser")
    CORS_MAX_AGE: int = Field(default=600, description="Maximum age for CORS preflight cache (in seconds)")

    # Database Configuration
    MONGO_URI: str = Field(default="", description="MongoDB connection URI")
    MONGO_DB_NAME: str = Field(default="vet_ai", description="MongoDB database name")

    # WebSocket Manager Configuration
    WORKSPACE_ROOT: str = Field(default="/tmp/vet-ai-workspace", description="WebSocket管理器的内部工作空间根目录")
    EXTERNAL_WORKSPACE_ROOT: str = Field(default="/tmp/vet-ai-external-workspace", description="WebSocket管理器的外部工作空间根目录")
    INSIDE_DOCKER: bool = Field(default=False, description="应用是否运行在Docker容器内")

    # LLM Configuration
    MODEL_NAME: Optional[str] = Field(default="deepseek-ai/DeepSeek-V3", description="Model name for LLM")
    BASE_URL: Optional[str] = Field(default="https://api-inference.modelscope.cn/v1", description="Base URL for LLM API")
    API_KEY: Optional[str] = Field(default="", description="API key for LLM service")

    # API Documentation Configuration
    ENABLE_DOCS: bool = Field(default=True, description="Enable API documentation (Swagger UI, ReDoc)")

    # Task Queue Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL for task queue")
    TASK_QUEUE_MAX_CONCURRENT: int = Field(default=5, description="Maximum concurrent tasks for the queue")
    TASK_TIMEOUT: int = Field(default=600, description="Task timeout in seconds")
    TASK_RESULT_EXPIRE: int = Field(default=3600, description="Task result cache time in seconds")

    # Legacy database settings (kept for compatibility but not used)
    DATABASE_ECHO: bool = Field(default=False, description="Legacy setting, not used with MongoDB")

    # 添加字段验证器来处理 List[str] 类型的环境变量
    @field_validator('ALLOWED_HOSTS', 'CORS_ALLOW_METHODS', 'CORS_ALLOW_HEADERS', 'CORS_EXPOSE_HEADERS', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Any) -> List[str]:
        """验证并解析列表类型的字段"""
        return parse_list_env(v)

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