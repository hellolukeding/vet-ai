# ============================================================
# 轻量化多阶段构建 Dockerfile
# 基础镜像大小: ~150MB (slim) vs ~900MB (full)
# 最终镜像大小: ~300-400MB
# ============================================================

# ================== 构建阶段 ==================
FROM python:3.12-slim AS builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安装uv包管理器（比pip更快，依赖更小）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 使用uv安装依赖到虚拟环境
# --frozen: 确保依赖版本一致
# --no-dev: 不安装开发依赖，节省空间
RUN uv sync --frozen --no-dev

# ================== 运行时阶段 ==================
FROM python:3.12-slim AS runtime

# 设置标签
LABEL maintainer="Vet-AI Team"
LABEL description="Lightweight Vet-AI API Server"
LABEL version="2.0.0"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # 优化Python内存使用
    MALLOC_ARENA_MAX=2 \
    # 减少Python启动时间
    PYTHONHASHSEED=random \
    # 不生成.pyc文件
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 只从builder复制虚拟环境（不包含构建工具）
COPY --from=builder /build/.venv /app/.venv

# 复制应用代码（只复制必要的目录）
COPY backend/ ./backend/
COPY config/ ./config/
COPY core/ ./core/
COPY utils/ ./utils/

# 创建非root用户（安全性）
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    # 设置目录权限
    && chown -R appuser:appuser /app \
    # 创建日志目录
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
# 使用虚拟环境中的uvicorn
CMD [".venv/bin/uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
