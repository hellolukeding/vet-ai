#!/bin/bash

# VET-AI 后端部署脚本

set -e

echo "=== VET-AI 后端部署开始 ==="

# 检查Docker和Docker Compose是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 进入项目目录
cd "$(dirname "$0")/.."

# 检查是否存在环境变量文件
if [ ! -f "docker/.env" ]; then
    echo "正在创建环境变量文件..."
    cp docker/.env.example docker/.env
    echo "✅ 已创建环境变量文件: docker/.env"
    echo ""
    echo "⚠️  请编辑 docker/.env 文件，设置正确的配置值："
    echo "   - API_KEY: AI模型API密钥"
    echo "   - SECRET_KEY: JWT签名密钥"
    echo "   - MONGO_INITDB_ROOT_PASSWORD: MongoDB root密码"
    echo ""
    read -p "按回车键继续..."
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p logs runs docker/nginx/ssl

# 构建和启动服务
echo "构建Docker镜像..."
docker-compose -f docker/docker-compose.yml build

echo "启动服务..."
docker-compose -f docker/docker-compose.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker-compose -f docker/docker-compose.yml ps

# 检查健康状态
echo "检查API健康状态..."
if curl -f http://localhost:8080/health &> /dev/null; then
    echo "✅ API服务运行正常"
else
    echo "❌ API服务可能未正常启动，请检查日志"
fi

echo "=== 部署完成 ==="
echo ""
echo "服务访问地址:"
echo "  - API服务: http://localhost:8080"
echo "  - 通过Nginx: http://localhost:80"
echo "  - MongoDB: localhost:27017"
echo ""
echo "管理命令:"
echo "  查看日志: docker-compose -f docker/docker-compose.yml logs -f"
echo "  停止服务: docker-compose -f docker/docker-compose.yml down"
echo "  重启服务: docker-compose -f docker/docker-compose.yml restart"
echo "  查看状态: docker-compose -f docker/docker-compose.yml ps"
