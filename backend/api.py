"""宠物医院AI诊断系统后端API入口文件"""

# 导入日志配置
import os
import sys
import traceback
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入诊断路由
from backend.routers import diagnosis_router, graph_router, pet_care_router

# 导入应用配置
from backend.settings import settings
from backend.runtime_checks import get_readiness_status
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
logger.add(
    "server.log", format=FORMAT, level="INFO", rotation="1 week", retention="90 days"
)

# API前缀
prefix = "/api/v1"


# 应用生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理函数"""
    logger.info("初始化系统资源")
    readiness = get_readiness_status()
    if readiness["ready"]:
        logger.info("运行时自检通过")
        if readiness.get("warnings"):
            logger.warning(f"运行时自检告警: {readiness['warnings']}")
    else:
        logger.warning(f"运行时自检未通过: {readiness['issues']}")

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
            "name": "西医诊断",
            "description": """
**西医智能诊断服务（LangGraph 高级版）**

基于 LangGraph 工作流的先进西医诊断系统：

### 🧠 核心特性
- **文献搜索**：自动搜索医学文献支持诊断（6-10条）
- **多步推理**：6节点工作流，CoT 推理
- **诊断审查**：双重质量保证机制
- **安全检查**：每个药物包含独立安全警告
- **工作流可视化**：实时追踪诊断过程

### 🔄 工作流节点
1. LiteratureSearch - 文献搜索
2. Diagnosis - CoT 推理诊断
3. DiagnosisReview - 诊断质量审查
4. Pharmacist - 用药建议
5. SafetyCheck - 安全检查（每个药物独立警告）
6. Report - 生成最终报告

### ⚡ 性能
- 同步模式：3-6 分钟（包含文献搜索和多步推理）
- 异步模式：支持任务队列，适合复杂诊断任务

### 📋 返回内容
- **diagnosis**：诊断结果（疾病名称、依据、概率）
- **medications**：用药建议（每个药物包含 safety_warning）
            """.strip(),
        },
        {
            "name": "中医诊断",
            "description": """
**中医智能诊断服务（LangGraph 高级版）**

基于 LangGraph 工作流的先进中医诊断系统：

### 🌿 核心特性
- **文献搜索**：自动搜索中医古籍和现代中医文献（6条）
- **多步推理**：5节点工作流，中医辨证论治
- **辨证论治**：四诊合参、脏腑辨证、气血津液分析
- **方剂推荐**：基础方、加减方、急救方（15个方剂）
- **动态护理**：根据证型动态生成护理建议

### 🔄 工作流节点
1. HerbLiteratureSearch - 中医文献搜索
2. HerbDiagnosis - 中医辨证论治（6步 CoT 推理）
3. HerbPharmacist - 方剂推荐（经典方剂）
4. HerbNursing - 动态护理建议（根据证型生成）
5. HerbReport - 生成最终报告

### ⚡ 性能
- 同步模式：3-5 分钟（包含文献搜索和多步推理）
- 异步模式：支持任务队列，适合复杂辨证任务

### 📋 返回内容
- **zhengming**：证型判断（如脾胃虚弱、寒湿困脾）
- **prescriptions**：方剂推荐（基础方、加减方、急救方）
- **nursing**：动态护理建议（饮食、观察、就医指征）
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
        # API文档配置：可通过ENABLE_DOCS环境变量独立控制
        docs_url="/api/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/api/redoc" if settings.ENABLE_DOCS else None,
        openapi_url="/api/openapi.json" if settings.ENABLE_DOCS else None,
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

    @app.get("/readyz", summary="就绪检查", tags=["health"])
    async def readiness_check():
        """运行时就绪检查端点"""
        status = get_readiness_status()
        return JSONResponse(
            status_code=200 if status["ready"] else 503,
            content=status,
        )

    return app


# 主程序入口
if __name__ == "__main__":
    app = create_app()
    uvicorn.run(
        "backend.api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
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
