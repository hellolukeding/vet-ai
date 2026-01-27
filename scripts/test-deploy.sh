#!/bin/bash
# ============================================================
# 部署后测试脚本
# 用于验证部署是否成功
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 服务器配置
SERVER_HOST="129.204.9.209"
SERVER_PORT="18082"
BASE_URL="http://$SERVER_HOST:$SERVER_PORT"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_fail() {
    echo -e "${RED}[✗]${NC} $1"
}

# 测试函数
test_health_check() {
    print_info "测试 1/5: 健康检查"

    if curl -sf "$BASE_URL/health" > /dev/null; then
        print_success "健康检查通过"
        return 0
    else
        print_fail "健康检查失败"
        return 1
    fi
}

test_api_docs() {
    print_info "测试 2/5: API文档访问"

    if curl -sf "$BASE_URL/api/docs" > /dev/null; then
        print_success "Swagger UI 可访问"
    else
        print_fail "Swagger UI 不可访问"
        return 1
    fi

    if curl -sf "$BASE_URL/api/redoc" > /dev/null; then
        print_success "ReDoc 可访问"
    else
        print_fail "ReDoc 不可访问"
        return 1
    fi
}

test_openapi() {
    print_info "测试 3/5: OpenAPI规范"

    if curl -sf "$BASE_URL/api/openapi.json" > /dev/null; then
        print_success "OpenAPI JSON 可访问"
    else
        print_fail "OpenAPI JSON 不可访问"
        return 1
    fi
}

test_api_endpoint() {
    print_info "测试 4/5: API端点测试"

    # 测试健康端点返回JSON
    response=$(curl -s "$BASE_URL/health")
    if echo "$response" | python -m json.tool > /dev/null 2>&1; then
        print_success "健康端点返回有效JSON"
    else
        print_fail "健康端点返回无效JSON"
        return 1
    fi
}

test_docker_status() {
    print_info "测试 5/5: Docker容器状态"

    # 这里需要SSH到服务器检查
    print_info "需要SSH访问来检查容器状态"
    echo ""
    echo "在服务器上运行以下命令："
    echo "  docker-compose ps"
    echo "  docker-compose logs vet-ai | tail -20"
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "Vet-AI 部署测试"
    echo "=========================================="
    echo ""
    echo "服务器: $SERVER_HOST:$SERVER_PORT"
    echo "基础URL: $BASE_URL"
    echo ""
    echo "开始测试..."
    echo ""

    all_passed=true

    # 运行测试
    if ! test_health_check; then
        all_passed=false
    fi
    echo ""

    if ! test_api_docs; then
        all_passed=false
    fi
    echo ""

    if ! test_openapi; then
        all_passed=false
    fi
    echo ""

    if ! test_api_endpoint; then
        all_passed=false
    fi
    echo ""

    test_docker_status
    echo ""

    # 总结
    echo "=========================================="
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}✓ 所有测试通过！${NC}"
        echo ""
        echo "🎉 部署成功！"
        echo ""
        echo "访问地址:"
        echo "  Swagger UI: $BASE_URL/api/docs"
        echo "  ReDoc:      $BASE_URL/api/redoc"
        echo "  健康检查:   $BASE_URL/health"
    else
        echo -e "${RED}✗ 部分测试失败！${NC}"
        echo ""
        echo "请检查："
        echo "  1. 服务是否正常启动"
        echo "  2. 端口 $SERVER_PORT 是否开放"
        echo "  3. 防火墙规则"
        echo ""
        echo "查看日志:"
        echo "  ssh root@$SERVER_HOST"
        echo "  cd /root/vet-ai/docker"
        echo "  docker-compose logs vet-ai"
    fi
    echo "=========================================="
}

# 运行测试
main "$@"
