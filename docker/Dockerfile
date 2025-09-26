# 使用官方Python 3.9镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY config/ ./config/
COPY core/ ./core/
COPY utils/ ./utils/

# 安装uv包管理器
RUN pip install uv

# 使用uv安装依赖
RUN uv sync --frozen

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8080

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["uv", "run", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080"]
