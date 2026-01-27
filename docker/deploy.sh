#!/bin/bash
# ============================================================
# Vet-AI Docker 快速部署脚本
# ============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    print_info "检查Docker环境..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    print_info "Docker版本: $(docker --version)"
}

# 检查Docker Compose是否安装
check_docker_compose() {
    print_info "检查Docker Compose..."
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    print_info "Docker Compose已就绪"
}

# 检查.env文件
check_env_file() {
    print_info "检查环境变量配置..."
    if [ ! -f ".env" ]; then
        print_warning ".env文件不存在，从.env.example创建..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "请编辑.env文件，填写API密钥等配置"
            print_info "编辑命令: vi .env"
            read -p "是否现在编辑? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-vi} .env
            else
                print_warning "跳过编辑，请稍后手动配置.env文件"
            fi
        else
            print_error ".env.example文件不存在"
            exit 1
        fi
    else
        print_info ".env文件已存在"
    fi
}

# 构建镜像
build_image() {
    print_info "开始构建Docker镜像..."
    print_warning "这可能需要3-5分钟，请耐心等待..."
    docker-compose build
    print_info "镜像构建完成"
}

# 启动服务
start_service() {
    print_info "启动服务..."
    docker-compose up -d
    print_info "服务已启动"
}

# 等待服务就绪
wait_for_service() {
    print_info "等待服务就绪..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
            print_info "服务已就绪！"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo
    print_error "服务启动超时，请查看日志: docker-compose logs vet-ai"
    return 1
}

# 显示服务信息
show_service_info() {
    echo ""
    print_info "================================================"
    print_info "🎉 Vet-AI服务部署成功！"
    print_info "================================================"
    echo ""
    echo "📖 API文档: http://localhost:8080/api/docs"
    echo "🔍 ReDoc文档: http://localhost:8080/api/redoc"
    echo "💚 健康检查: http://localhost:8080/health"
    echo ""
    echo "📊 查看日志: docker-compose logs -f vet-ai"
    echo "🛑 停止服务: docker-compose down"
    echo "🔄 重启服务: docker-compose restart"
    echo ""
    print_info "================================================"
}

# 主函数
main() {
    echo ""
    print_info "Vet-AI Docker 轻量化部署脚本"
    print_info "================================================"
    echo ""

    # 检查环境
    check_docker
    check_docker_compose
    check_env_file

    echo ""
    read -p "是否开始构建并启动服务? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "部署已取消"
        exit 0
    fi

    echo ""
    # 构建和启动
    build_image
    start_service

    # 等待服务就绪
    if wait_for_service; then
        show_service_info
    else
        print_error "部署失败，请检查日志"
        exit 1
    fi
}

# 运行主函数
main
