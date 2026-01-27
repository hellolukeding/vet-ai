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
        # 启动任务队列Worker
        logger.info("正在启动任务队列Worker...")
        from core.tasks.worker import start_worker
        await start_worker()
        logger.info("任务队列Worker已启动")

        yield

    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise

    finally:
        logger.info("正在清理应用资源...")

        # 停止任务队列Worker
        try:
            from core.tasks.worker import stop_worker
            await stop_worker()
            logger.info("任务队列Worker已停止")
        except Exception as e:
            logger.error(f"停止Worker失败: {e}")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    # 定义API标签元数据
    tags_metadata = [
        {
            "name": "pet-care",
            "description": """
**宠物护理计划生成服务**

基于LangGraph工作流的智能宠物护理计划生成系统，提供：
- 🍽️ **营养计划**：每日卡路里需求、营养比例、推荐食物、禁忌食物、喂养时间表
- 💊 **补充剂建议**：根据宠物健康状况推荐营养补充剂
- 🏥 **护理计划**：美容护理、医疗护理、运动建议、疫苗接种计划
- 🏠 **环境管理**：生活环境优化建议

**工作流程**：提取宠物信息 → 并行生成营养和护理计划 → 输出结构化结果

**性能**：同步模式约2分钟，异步模式支持任务队列
            """.strip(),
        },
        {
            "name": "diagnosis",
            "description": """
**宠物疾病诊断服务**

智能诊断系统，支持：
- 🩺 **症状分析**：根据宠物症状描述生成可能疾病列表
- 💊 **用药建议**：提供针对性的治疗药物推荐
- 📊 **诊断结果**：包含疾病描述、症状说明、治疗方案

**两种诊断模式**：
1. **基础诊断** (`/diagnosis`)：快速诊断，适合常见疾病
2. **中医诊断** (`/vet/herb`)：中医辨证论治，草本治疗方案

**异步支持**：提供任务队列机制，支持长时间诊断任务
            """.strip(),
        },
        {
            "name": "graph",
            "description": """
**LangGraph智能诊断服务**

基于LangGraph的先进诊断系统：
- 🧠 **多步推理**：通过状态机实现复杂诊断流程
- 🔄 **工作流管理**：支持诊断过程的可视化和管理
- 📈 **增强准确性**：通过多轮对话和验证提高诊断准确率

**适用场景**：
- 复杂疑难病例
- 需要多系统分析的综合诊断
- 需要详细推理过程的诊断

**特性**：状态追踪、流程可视化、异步任务支持
            """.strip(),
        },
        {
            "name": "health",
            "description": """
**健康检查服务**

系统状态监控端点：
- ✅ 服务可用性检查
- 📊 系统状态监控
- 🔧 服务版本信息

**端点**：`GET /health` - 返回服务健康状态
            """.strip(),
        },
    ]

    app = FastAPI(
        title="Vet-AI 宠物医疗智能诊断与护理系统",
        description="""
## 🐾 Vet-AI RESTful API

欢迎使用Vet-AI宠物医疗智能诊断与护理系统API。

### 系统概述

Vet-AI是一个基于人工智能的宠物医疗辅助系统，提供疾病诊断、中医辨证、营养计划和护理建议等综合服务。

### 核心功能

1. **智能诊断** 🩺
   - 症状分析 → 疾病识别 → 治疗建议
   - 支持西医诊断和中医辨证
   - 基于LangGraph的多步推理诊断

2. **护理计划** 📋
   - 营养计划生成（卡路里、营养比例、推荐食物）
   - 护理建议（美容、医疗、运动、环境）
   - 个性化定制，根据宠物品种、年龄、健康状况调整

3. **任务管理** ⚙️
   - 同步/异步双模式
   - 任务队列管理
   - 进度追踪和状态查询

### 技术栈

- **框架**：FastAPI + LangGraph
- **LLM**：智谱AI GLM-4.7
- **架构**：异步任务队列 + 工作流编排

### 使用方式

**同步模式**（适合快速响应）：
```bash
curl -X POST "http://localhost:8080/api/v1/pet-care/plan" \
  -H "Content-Type: application/json" \
  -d '{"user_query":"我的3岁金毛犬Lucky最近食欲不好"}'
```

**异步模式**（适合长时间任务）：
```bash
# 1. 提交任务
curl -X POST "http://localhost:8080/api/v1/pet-care/plan?async_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"user_query":"..."}'

# 2. 查询结果
curl "http://localhost:8080/api/v1/pet-care/plan/task/{task_id}"
```

### 文档导航

- 📖 [Swagger UI](/api/docs) - 交互式API文档
- 📕 [ReDoc](/api/redoc) - 美观的API文档
- 📄 [OpenAPI JSON](/api/openapi.json) - OpenAPI规范

### 联系方式

- **问题反馈**：请通过GitHub Issues提交
- **技术支持**：api-support@example.com
- **许可证**：MIT License
        """.strip(),
        version="2.0.0",
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
