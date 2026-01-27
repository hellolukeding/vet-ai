#!/bin/bash
# ============================================================
# 服务器路径验证脚本
# 用于验证服务器上的部署路径配置是否正确
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

SERVER_IP="129.204.9.209"
SERVER_USER="root"
DEPLOY_DIR="/opt/vet-ai"

echo ""
echo "=========================================="
echo "Vet-AI 服务器路径验证"
echo "=========================================="
echo ""
echo "服务器: $SERVER_IP"
echo "部署路径: $DEPLOY_DIR"
echo ""

# 检查是否能SSH连接
print_step "检查SSH连接..."
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    $SERVER_USER@$SERVER_IP "echo 'SSH连接成功'" 2>/dev/null; then
    print_info "SSH连接正常"
else
    print_error "SSH连接失败"
    echo "请检查："
    echo "  1. 服务器IP是否正确: $SERVER_IP"
    echo "  2. 服务器是否可达"
    echo "  3. SSH服务是否运行"
    exit 1
fi
echo ""

# 检查部署目录
print_step "检查部署目录..."
if ssh $SERVER_USER@$SERVER_IP "test -d $DEPLOY_DIR"; then
    print_info "部署目录存在: $DEPLOY_DIR"
else
    print_warning "部署目录不存在，将创建: $DEPLOY_DIR"
    read -p "是否创建目录? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOY_DIR"
        print_info "目录已创建"
    else
        print_error "取消操作"
        exit 1
    fi
fi
echo ""

# 检查目录权限
print_step "检查目录权限..."
permissions=$(ssh $SERVER_USER@$SERVER_IP "ls -ld $DEPLOY_DIR | awk '{print \$1,\$3,\$4}'")
print_info "目录权限: $permissions"

# 检查磁盘空间
print_step "检查磁盘空间..."
disk_info=$(ssh $SERVER_USER@$SERVER_IP "df -h $DEPLOY_DIR | tail -1")
echo "$disk_info"
echo ""

# 检查Docker
print_step "检查Docker..."
if ssh $SERVER_USER@$SERVER_IP "command -v docker > /dev/null"; then
    docker_version=$(ssh $SERVER_USER@$SERVER_IP "docker --version")
    print_info "Docker已安装: $docker_version"
else
    print_error "Docker未安装"
    echo "请先安装Docker"
fi
echo ""

# 检查Docker Compose
print_step "检查Docker Compose..."
if ssh $SERVER_USER@$SERVER_IP "docker-compose version > /dev/null 2>&1 || docker compose version > /dev/null 2>&1"; then
    compose_version=$(ssh $SERVER_USER@$SERVER_IP "docker-compose version --short 2>/dev/null || docker compose version --short 2>/dev/null")
    print_info "Docker Compose已安装: $compose_version"
else
    print_error "Docker Compose未安装"
    echo "请先安装Docker Compose"
fi
echo ""

# 检查端口占用
print_step "检查端口18082..."
if ssh $SERVER_USER@$SERVER_IP "netstat -tlnp 2>/dev/null | grep -q ':18082'"; then
    print_warning "端口18082已被占用"
    echo "占用进程:"
    ssh $SERVER_USER@$SERVER_IP "netstat -tlnp 2>/dev/null | grep ':18082' || ss -tlnp | grep ':18082'"
else
    print_info "端口18082可用"
fi
echo ""

# 显示目录结构
print_step "当前目录结构..."
echo ""
ssh $SERVER_USER@$SERVER_IP "ls -la $DEPLOY_DIR 2>/dev/null || echo '目录为空或不存在'"
echo ""

# 配置建议
print_step "配置建议..."
echo ""
echo "确保以下配置正确："
echo ""
echo "1️⃣  目录权限:"
echo "   ssh $SERVER_USER@$SERVER_IP 'chown -R root:root $DEPLOY_DIR'"
echo "   ssh $SERVER_USER@$SERVER_IP 'chmod -R 755 $DEPLOY_DIR'"
echo ""
echo "2️⃣  Docker目录:"
echo "   ssh $SERVER_USER@$SERVER_IP 'mkdir -p $DEPLOY_DIR/docker'"
echo "   ssh $SERVER_USER@$SERVER_IP 'mkdir -p $DEPLOY_DIR/logs'"
echo "   ssh $SERVER_USER@$SERVER_IP 'mkdir -p $DEPLOY_DIR/backups'"
echo ""
echo "3️⃣  环境变量:"
echo "   ssh $SERVER_USER@$SERVER_IP 'vi $DEPLOY_DIR/docker/.env'"
echo ""
echo "4️⃣  防火墙:"
echo "   确保以下端口开放："
echo "   • 18082 (HTTP API)"
echo "   • 22 (SSH)"
echo ""

# 生成验证报告
echo "=========================================="
echo "✅ 验证完成"
echo "=========================================="
echo ""
echo "📋 服务器信息:"
echo "  IP地址: $SERVER_IP"
echo "  用户: $SERVER_USER"
echo "  部署目录: $DEPLOY_DIR"
echo "  Docker目录: $DEPLOY_DIR/docker"
echo ""
echo "🚀 下一步:"
echo "  1. 配置SSH密钥: cd scripts && ./setup-ssh.sh"
echo "  2. 配置GitHub Secrets"
echo "  3. 推送代码触发部署"
echo ""
echo "📖 详细文档:"
echo "  • docs/QUICK_START.md - 快速部署指南"
echo "  • docs/DEPLOYMENT.md - 完整部署指南"
echo ""
echo "=========================================="
