# ============================================================
# 轻量化多阶段构建 Dockerfile（中国网络优化 + 稳定构建版）
# ============================================================

# ================== 构建阶段 ==================
FROM python:3.12-slim AS builder

WORKDIR /build

# 使用国内 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 国内源
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DEFAULT_TIMEOUT=300 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 复制 requirements.txt
COPY requirements.txt ./

# 安装依赖到临时目录（用于复制）
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ================== 运行时阶段 ==================
FROM python:3.12-slim AS runtime

# 使用国内 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources

LABEL maintainer="Vet-AI Team"
LABEL description="Lightweight Vet-AI API Server"
LABEL version="2.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/.local/bin:$PATH \
    MALLOC_ARENA_MAX=2 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 复制已安装的依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY backend/ ./backend/
COPY config/ ./config/
COPY core/ ./core/
COPY utils/ ./utils/

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
