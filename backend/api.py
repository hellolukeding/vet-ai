from contextlib import asynccontextmanager
import traceback

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend.routers import diagnosis
from config.logger import logger

from .settings import settings

FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{process} | {thread.name} | "
    "{name}:{function}:{line} | "
    "{message}"
)

logger.add("server.log", format=FORMAT, level="INFO", rotation="1 week", retention="90 days")

prefix = "/api/v1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("初始化系统资源")

    try:
        # 可以在这里添加初始化代码
        yield
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise

    finally:
        logger.info("正在清理应用资源...")
        # todo
        pass

def create_app() -> FastAPI:
    tags_metadata = []
    app = FastAPI(
        title="vet-ai restful api",
        description="""
## vet-ai RESTful API


        """.strip(),
        version="1.0.0",
        openapi_tags=tags_metadata,
        terms_of_service="https://example.com/terms/",
        contact={
            "name": "Bella API Support",
            "url": "https://example.com/contact/",
            "email": "api-support@example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,  # 添加生命周期管理
        # Custom Swagger UI configuration
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "operationsSorter": "method",
            "filter": True,
            "tagsSorter": "alpha",
            "tryItOutEnabled": True,
            "syntaxHighlight.theme": "monokai",
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
        max_age=settings.CORS_MAX_AGE,
    )

    # /*--------------------------------------- diagnosis ------------------------------------------*/
    app.include_router(
        diagnosis.router,
        prefix=prefix,
        tags=["diagnosis"],
        responses={
            404: {"description": "Diagnosis not found"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            500: {"description": "会话服务错误"},
        },
    )

    @app.get("/health", summary="健康检查", tags=["health"])
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "message": "服务运行正常"}

    return app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(
        "backend.api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

app = create_app()

def run_server() -> None:
    """Run the FastAPI server."""
    uvicorn.run(
        "bella-backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )

def main():
    run_server()

if __name__ == "__main__":

    main()