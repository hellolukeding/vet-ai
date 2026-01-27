# ============================================================
# 轻量化多阶段构建 Dockerfile
# Modified by Gemini: Added China Mirror support
# ============================================================

# ================== 构建阶段 ==================
FROM python:3.12-slim AS builder

# 设置工作目录
WORKDIR /build

# 1. 优化 apt 源（可选，如果 apt 很慢可以解开注释，但在 slim 镜像通常不是瓶颈）
# RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装构建依赖
# 为了防止 apt 卡住，我们这里清理列表更彻底一点
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# ================== 关键修改开始 ==================
# 2. 配置 uv 使用清华源（解决 uv sync 超时/卡死问题）
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 增加网络超时容忍度（防止网络波动导致中断）
ENV UV_HTTP_TIMEOUT=300

# 4. 执行安装
# 增加 -v 参数，这样如果报错可以看到具体是哪个包卡住了
# --compile-bytecode: 编译字节码，虽然增加一点体积，但能加快容器启动速度（可选）
RUN uv sync --frozen --no-dev -v
# ================== 关键修改结束 ==================

# ================== 运行时阶段 ==================
FROM python:3.12-slim AS runtime

# 设置标签
LABEL maintainer="Vet-AI Team"
LABEL description="Lightweight Vet-AI API Server"
LABEL version="2.0.0"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MALLOC_ARENA_MAX=2 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 只从builder复制虚拟环境
COPY --from=builder /build/.venv /app/.venv

# 复制应用代码
COPY backend/ ./backend/
COPY config/ ./config/
COPY core/ ./core/
COPY utils/ ./utils/

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app/logs

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# 启动命令
CMD [".venv/bin/uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]