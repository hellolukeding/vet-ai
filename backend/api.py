"""宠物医院AI诊断系统后端API入口文件"""

# 导入日志配置
import os
import sys
import traceback
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 导入FastAPI相关模块
from fastapi.openapi.utils import get_openapi

# 导入诊断路由
from backend.routers import diagnosis_router, graph_router, pet_care_router
# 导入应用配置
from backend.settings import settings
from config.logger import logger

# 将项目根目录添加到Python路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 定义日志格式
FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{process} | {thread.name} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# 配置日志文件输出
logger.add("server.log", format=FORMAT, level="INFO",
           rotation="1 week", retention="90 days")

# API前缀
prefix = "/api/v1"


# 应用生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理函数"""
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
    """创建FastAPI应用实例"""
    # 定义API标签元数据
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
        # 自定义Swagger UI配置
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

    # 添加CORS中间件
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
    # 注册诊断路由
    app.include_router(
        diagnosis_router,
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

    # graph
    app.include_router(
        graph_router,
        prefix=prefix,
        tags=["graph"],
        responses={
            404: {"description": "Graph not found"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            500: {"description": "会话服务错误"},
        },
    )

    # pet care plan
    app.include_router(
        pet_care_router,
        prefix=prefix,
        tags=["pet-care"],
        responses={
            404: {"description": "Pet care plan not found"},
            400: {"description": "Bad request"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            500: {"description": "服务错误"},
        },
    )

    # 健康检查端点
    @app.get("/health", summary="健康检查", tags=["health"])
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "message": "服务运行正常"}

    return app


# 主程序入口
if __name__ == "__main__":
    app = create_app()
    uvicorn.run(
        "backend.api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

# 创建应用实例
app = create_app()


def run_server() -> None:
    """运行FastAPI服务器"""
    uvicorn.run(
        "backend.api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )


def main():
    """主函数"""
    run_server()


if __name__ == "__main__":
    main()
