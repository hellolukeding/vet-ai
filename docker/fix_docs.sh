#!/bin/bash
# ============================================================
# 快速修复：启用API文档访问
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo ""
print_info "=========================================="
print_info "API文档访问修复脚本"
print_info "=========================================="
echo ""

print_info "问题：Swagger文档在DEBUG=false时返回404"
print_info "解决方案：添加ENABLE_DOCS环境变量"
echo ""

print_warning "此脚本将："
echo "  1. 停止当前运行的Docker容器"
echo "  2. 重新构建Docker镜像（包含代码修复）"
echo "  3. 启动更新后的服务"
echo ""

read -p "是否继续? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "操作已取消"
    exit 0
fi

echo ""
print_info "步骤 1/3: 停止服务..."
docker-compose down

print_info "步骤 2/3: 重新构建镜像（需要3-5分钟）..."
docker-compose build --no-cache

print_info "步骤 3/3: 启动服务..."
docker-compose up -d

echo ""
print_info "等待服务就绪..."
sleep 10

# 检查服务状态
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    print_info "✅ 服务已启动！"
else
    print_warning "服务启动中，请稍等片刻..."
    print_info "查看日志: docker-compose logs -f vet-ai"
fi

echo ""
print_info "=========================================="
print_info "🎉 修复完成！"
print_info "=========================================="
echo ""
echo "📖 访问API文档:"
echo "   Swagger UI:  http://localhost:8080/api/docs"
echo "   ReDoc:       http://localhost:8080/api/redoc"
echo "   OpenAPI:     http://localhost:8080/api/openapi.json"
echo ""
echo "💡 提示:"
echo "   - 现在即使 DEBUG=false，文档也可访问"
echo "   - 文档访问由 ENABLE_DOCS 环境变量控制"
echo "   - 查看日志: docker-compose logs -f vet-ai"
echo ""
print_info "=========================================="
