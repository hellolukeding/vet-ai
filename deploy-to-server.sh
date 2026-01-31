#!/bin/bash
# 服务器部署脚本 - 更新代码并重启服务

set -e

echo "========================================="
echo "  开始更新 Vet-AI 服务"
echo "========================================="

# 1. 进入项目目录
cd /opt/vet-ai
echo "✓ 进入项目目录: $(pwd)"

# 2. 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

# 3. 切换到 langgraph 分支
if [ "$CURRENT_BRANCH" != "langgraph" ]; then
    echo "→ 切换到 langgraph 分支..."
    git checkout langgraph
    echo "✓ 已切换到 langgraph 分支"
else
    echo "✓ 已经在 langgraph 分支"
fi

# 4. 拉取最新代码
echo "→ 拉取最新代码..."
git pull origin langgraph
echo "✓ 代码已更新"

# 5. 查看最新提交
echo "→ 最新提交:"
git log --oneline -3

# 6. 验证 settings.py 行数（应该有 parse_list_env 函数）
echo "→ 验证代码..."
if grep -q "def parse_list_env" backend/settings.py; then
    echo "✓ settings.py 包含 parse_list_env 函数"
else
    echo "✗ 错误: settings.py 没有包含 parse_list_env 函数"
    exit 1
fi

if grep -q "@field_validator" backend/settings.py; then
    echo "✓ settings.py 包含 field_validator"
else
    echo "✗ 错误: settings.py 没有包含 field_validator"
    exit 1
fi

# 7. 进入 docker 目录
cd docker

# 8. 修复 .env 文件中的 ALLOWED_HOSTS 格式
echo "→ 检查 .env 文件..."
if [ -f .env ]; then
    if grep -q "^ALLOWED_HOSTS=\*" .env; then
        echo "→ 修复 ALLOWED_HOSTS 格式..."
        sed -i 's/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=["*"]/' .env
        echo "✓ ALLOWED_HOSTS 已修改为: $(grep ALLOWED_HOSTS .env)"
    else
        echo "✓ ALLOWED_HOSTS 格式正确: $(grep ALLOWED_HOSTS .env)"
    fi
else
    echo "⚠ 警告: .env 文件不存在，将使用默认值"
fi

# 9. 停止并删除旧容器和镜像
echo "→ 停止旧服务..."
docker compose down
echo "✓ 容器已停止"

echo "→ 删除旧镜像..."
docker rmi docker-vet-ai 2>/dev/null || echo "  镜像不存在或已删除"

# 10. 重新构建镜像（不使用缓存）
echo "→ 重新构建镜像（不使用缓存）..."
docker compose build --no-cache
echo "✓ 镜像构建完成"

# 11. 启动服务
echo "→ 启动服务..."
docker compose up -d
echo "✓ 服务已启动"

# 12. 等待服务启动
echo "→ 等待服务启动..."
sleep 10

# 13. 检查容器状态
echo "→ 容器状态:"
docker compose ps

# 14. 查看日志
echo "→ 查看最新日志:"
docker compose logs vet-ai --tail 30

# 15. 测试健康检查
echo "→ 测试健康检查端点..."
sleep 5
if curl -f http://localhost:18082/health; then
    echo ""
    echo "========================================="
    echo "  ✓ 部署成功！服务正常运行"
    echo "========================================="
    echo "健康检查: http://localhost:18082/health"
    echo "API文档: http://localhost:18082/docs"
    echo "========================================="
else
    echo ""
    echo "========================================="
    echo "  ✗ 服务启动失败"
    echo "========================================="
    echo "请查看上方日志排查问题"
    exit 1
fi
