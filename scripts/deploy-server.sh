#!/bin/bash
# ============================================================
# 服务器端部署脚本
# 在生产服务器上运行，用于部署Vet-AI应用
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# ============================================================
# 配置
# ============================================================
WORK_DIR="/opt/vet-ai"
DOCKER_DIR="$WORK_DIR/docker"
BACKUP_DIR="$WORK_DIR/backups"
LOG_FILE="$DOCKER_DIR/deploy.log"

# ============================================================
# 函数
# ============================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    print_step "检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        log "ERROR: Docker未安装"
        exit 1
    fi
    print_info "Docker版本: $(docker --version)"

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose未安装"
        log "ERROR: Docker Compose未安装"
        exit 1
    fi
    print_info "Docker Compose已就绪"

    # 检查磁盘空间
    available_space=$(df -h / | awk 'NR==2 {print $4}')
    print_info "可用磁盘空间: $available_space"

    log "系统要求检查完成"
}

backup_current_deployment() {
    print_step "备份当前部署..."

    if [ -d "$DOCKER_DIR" ]; then
        mkdir -p "$BACKUP_DIR"

        backup_name="backup_$(date +%Y%m%d_%H%M%S)"
        backup_path="$BACKUP_DIR/$backup_name"

        # 备份docker-compose.yml和.env
        cp "$DOCKER_DIR/docker-compose.yml" "$backup_path/" 2>/dev/null || true
        cp "$DOCKER_DIR/.env" "$backup_path/" 2>/dev/null || true

        # 备份日志
        cp -r "$DOCKER_DIR/logs" "$backup_path/" 2>/dev/null || true

        print_info "备份完成: $backup_path"
        log "备份完成: $backup_path"

        # 清理7天前的备份
        find "$BACKUP_DIR" -type d -name "backup_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    else
        print_warning "没有找到现有部署，跳过备份"
    fi
}

stop_services() {
    print_step "停止现有服务..."

    cd "$DOCKER_DIR"

    if docker-compose ps | grep -q "Up"; then
        print_info "停止服务..."
        docker-compose down
        log "服务已停止"
    else
        print_info "服务未运行"
    fi
}

build_image() {
    print_step "构建Docker镜像..."
    print_warning "这可能需要3-5分钟，请耐心等待..."

    cd "$DOCKER_DIR"

    # 清理构建缓存
    docker builder prune -f || true

    # 构建镜像
    if docker-compose build --no-cache; then
        print_info "镜像构建成功"
        log "镜像构建成功"
    else
        print_error "镜像构建失败"
        log "ERROR: 镜像构建失败"
        exit 1
    fi

    # 显示镜像大小
    image_size=$(docker images vet-ai-backend:latest --format "{{.Size}}")
    print_info "镜像大小: $image_size"
}

start_services() {
    print_step "启动服务..."

    cd "$DOCKER_DIR"

    # 启动服务
    docker-compose up -d

    log "服务已启动"
}

wait_for_service() {
    print_step "等待服务就绪..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
            print_info "✅ 服务已就绪！"
            log "服务已就绪"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo
    print_error "服务启动超时"
    log "ERROR: 服务启动超时"
    return 1
}

check_service_health() {
    print_step "检查服务健康状态..."

    cd "$DOCKER_DIR"

    # 检查容器状态
    print_info "容器状态:"
    docker-compose ps

    # 检查健康端点
    print_info "健康检查:"
    if curl -sf http://localhost:8080/health | python -m json.tool; then
        print_info "✅ 健康检查通过"
        log "健康检查通过"
    else
        print_warning "健康检查失败，但服务可能正在启动中"
    fi

    # 显示最近日志
    print_info "最近日志 (最后50行):"
    docker-compose logs --tail=50 vet-ai
}

cleanup_old_images() {
    print_step "清理旧镜像..."

    # 清理未使用的镜像
    docker image prune -a -f

    # 清理未使用的卷
    docker volume prune -f

    print_info "清理完成"
    log "清理完成"
}

show_service_info() {
    echo ""
    print_info "========================================"
    print_info "🎉 部署完成！"
    print_info "========================================"
    echo ""
    echo "📖 API文档: http://129.204.9.209:18082/api/docs"
    echo "🔍 健康检查: http://129.204.9.209:18082/health"
    echo ""
    echo "📂 项目目录: /opt/vet-ai"
    echo "📊 查看日志: cd $DOCKER_DIR && docker-compose logs -f vet-ai"
    echo "🔄 重启服务: cd $DOCKER_DIR && docker-compose restart"
    echo "🛑 停止服务: cd $DOCKER_DIR && docker-compose down"
    echo ""
    print_info "========================================"

    log "部署完成"
}

# ============================================================
# 主流程
# ============================================================

main() {
    echo ""
    print_info "========================================"
    print_info "Vet-AI 服务器部署脚本"
    print_info "========================================"
    echo ""

    log "========== 开始部署 =========="

    # 检查要求
    check_requirements

    # 备份
    backup_current_deployment

    # 停止服务
    stop_services

    # 构建镜像
    build_image

    # 启动服务
    start_services

    # 等待服务就绪
    if wait_for_service; then
        # 健康检查
        check_service_health

        # 清理
        cleanup_old_images

        # 显示信息
        show_service_info

        log "========== 部署成功 =========="
        exit 0
    else
        print_error "部署失败，请查看日志"
        log "========== 部署失败 =========="

        # 显示错误日志
        cd "$DOCKER_DIR"
        docker-compose logs --tail=100 vet-ai

        exit 1
    fi
}

# 运行主函数
main "$@"
