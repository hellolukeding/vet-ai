#!/bin/bash
# ============================================================
# SSH密钥配置脚本
# 用于设置GitHub Actions与服务器的SSH连接
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

SERVER_IP="129.204.9.209"
SERVER_USER="root"

echo ""
print_info "========================================"
print_info "SSH密钥配置向导"
print_info "========================================"
echo ""

print_step "步骤说明"
echo "此脚本将帮助您："
echo "  1. 生成SSH密钥对（如果不存在）"
echo "  2. 将公钥复制到服务器"
echo "  3. 配置GitHub Secrets"
echo ""

read -p "是否继续? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "操作已取消"
    exit 0
fi

# ============================================================
# 步骤1: 检查/生成SSH密钥
# ============================================================

print_step "步骤 1/3: 检查SSH密钥"

SSH_KEY_FILE="$HOME/.ssh/vet_ai_deploy"

if [ -f "$SSH_KEY_FILE" ]; then
    print_info "SSH密钥已存在: $SSH_KEY_FILE"
    read -p "是否重新生成? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$SSH_KEY_FILE" "$SSH_KEY_FILE.pub"
        print_warning "旧密钥已删除"
    fi
fi

if [ ! -f "$SSH_KEY_FILE" ]; then
    print_info "生成SSH密钥对..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_FILE" -N "" -C "vet-ai-deploy"
    print_info "密钥生成成功"
fi

# 设置正确的权限
chmod 600 "$SSH_KEY_FILE"
chmod 644 "$SSH_KEY_FILE.pub"

# ============================================================
# 步骤2: 复制公钥到服务器
# ============================================================

print_step "步骤 2/3: 配置服务器"

print_warning "现在需要将公钥复制到服务器"
print_info "服务器: $SERVER_USER@$SERVER_IP"
echo ""
print_info "服务器密码: aK3!eF4!bB3*cJ0]bH"
echo ""

# 复制公钥到服务器
print_info "正在复制公钥到服务器..."
ssh-copy-id -i "$SSH_KEY_FILE.pub" "$SERVER_USER@$SERVER_IP"

if [ $? -eq 0 ]; then
    print_info "✅ 公钥复制成功"
else
    print_warning "自动复制失败，尝试手动复制..."
    echo ""
    print_info "公钥内容:"
    cat "$SSH_KEY_FILE.pub"
    echo ""
    print_info "请手动执行以下命令："
    echo "  ssh $SERVER_USER@$SERVER_IP"
    echo "  mkdir -p ~/.ssh"
    echo "  chmod 700 ~/.ssh"
    echo "  echo '$(cat $SSH_KEY_FILE.pub)' >> ~/.ssh/authorized_keys"
    echo "  chmod 600 ~/.ssh/authorized_keys"
    echo ""
    read -p "完成后按回车继续..." -r
fi

# 测试SSH连接
print_info "测试SSH连接..."
if ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 "$SERVER_USER@$SERVER_IP" \
    "echo 'SSH连接成功'" 2>/dev/null; then
    print_info "✅ SSH连接测试成功"
else
    print_error "❌ SSH连接失败"
    exit 1
fi

# ============================================================
# 步骤3: 配置GitHub Secrets
# ============================================================

print_step "步骤 3/3: 配置GitHub Secrets"

print_info "私钥路径: $SSH_KEY_FILE"
print_info "私钥内容:"
echo ""
cat "$SSH_KEY_FILE"
echo ""

print_info "========================================"
print_info "GitHub Secrets 配置说明"
print_info "========================================"
echo ""
print_info "需要在GitHub仓库中配置以下Secrets:"
echo ""
echo "1️⃣  SERVER_HOST"
echo "   值: $SERVER_IP"
echo ""
echo "2️⃣  SERVER_USER"
echo "   值: $SERVER_USER"
echo ""
echo "3️⃣  SSH_PRIVATE_KEY"
echo "   值: (上面显示的私钥完整内容，包括"
echo "        -----BEGIN OPENSSH PRIVATE KEY-----"
echo "        和"
echo "        -----END OPENSSH PRIVATE KEY-----)"
echo ""
echo "配置步骤:"
echo "  1. 打开GitHub仓库"
echo "  2. 进入 Settings → Secrets and variables → Actions"
echo "  3. 点击 'New repository secret'"
echo "  4. 分别添加上述3个Secrets"
echo ""
print_info "========================================"

# 保存配置信息
CONFIG_FILE="./github-secrets-config.txt"
cat > "$CONFIG_FILE" << EOF
# GitHub Secrets 配置信息
# 生成时间: $(date)

## 服务器信息
SERVER_HOST=$SERVER_IP
SERVER_USER=$SERVER_USER

## SSH私钥文件
SSH_KEY_FILE=$SSH_KEY_FILE

## 配置步骤
1. 访问: https://github.com/[YOUR-REPO]/settings/secrets/actions
2. 添加以下Secrets:

   Name: SERVER_HOST
   Value: $SERVER_IP

   Name: SERVER_USER
   Value: $SERVER_USER

   Name: SSH_PRIVATE_KEY
   Value: $(cat $SSH_KEY_FILE | head -1)
   ... (完整的私钥内容)
   $(cat $SSH_KEY_FILE | tail -1)

3. 保存后，推送到main分支即可触发自动部署
EOF

print_info "配置信息已保存到: $CONFIG_FILE"

# ============================================================
# 完成
# ============================================================

echo ""
print_info "========================================"
print_info "✅ SSH配置完成！"
print_info "========================================"
echo ""
print_info "下一步操作:"
echo "  1. 配置GitHub Secrets（参考上述说明）"
echo "  2. 将代码推送到main分支"
echo "  3. GitHub Actions将自动部署"
echo ""
print_info "手动测试SSH连接:"
echo "  ssh -i $SSH_KEY_FILE $SERVER_USER@$SERVER_IP"
echo ""
