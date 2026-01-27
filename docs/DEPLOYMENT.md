# GitHub Actions 自动化部署指南

## 🎯 概述

本文档说明如何配置GitHub Actions实现Vet-AI项目的自动化部署到生产服务器。

### 部署架构

```
GitHub → GitHub Actions → Docker Build → SSH → 服务器(129.204.9.209)
                                                       ↓
                                                 Docker Compose启动
```

---

## 📋 前置要求

### 本地环境

- ✅ Git客户端
- ✅ GitHub账号
- ✅ 服务器SSH访问权限

### 服务器环境

- ✅ Docker (>= 20.10)
- ✅ Docker Compose (>= 2.0)
- ✅ 开放端口: 18082

---

## 🔧 配置步骤

### 第一步：配置SSH密钥

#### 方式A：使用自动化脚本（推荐）

```bash
cd scripts
./setup-ssh.sh
```

脚本将自动：
1. 生成SSH密钥对
2. 复制公钥到服务器
3. 显示GitHub Secrets配置信息

#### 方式B：手动配置

```bash
# 1. 生成SSH密钥
ssh-keygen -t ed25519 -f ~/.ssh/vet_ai_deploy -N ""

# 2. 复制公钥到服务器
ssh-copy-id -i ~/.ssh/vet_ai_deploy.pub root@129.204.9.209

# 3. 测试连接
ssh -i ~/.ssh/vet_ai_deploy root@129.204.9.209
```

---

### 第二步：配置GitHub Secrets

1. **打开GitHub仓库**
   - 访问: `https://github.com/[YOUR-USERNAME]/vet-ai`

2. **进入Secrets配置**
   - Settings → Secrets and variables → Actions
   - 点击 "New repository secret"

3. **添加以下Secrets**

| Secret名称 | 值 | 说明 |
|-----------|---|------|
| `SERVER_HOST` | `129.204.9.209` | 服务器IP地址 |
| `SERVER_USER` | `root` | 服务器用户名 |
| `SSH_PRIVATE_KEY` | 私钥完整内容 | SSH私钥（见下方获取方式） |

#### 获取SSH_PRIVATE_KEY

```bash
# 显示私钥内容
cat ~/.ssh/vet_ai_deploy
```

复制**整个输出**，包括：
```
-----BEGIN OPENSSH PRIVATE KEY-----
... (密钥内容) ...
-----END OPENSSH PRIVATE KEY-----
```

---

### 第三步：验证配置

#### 测试SSH连接

```bash
ssh -i ~/.ssh/vet_ai_deploy root@129.204.9.209
```

如果成功登录，说明SSH配置正确。

#### 手动测试部署

```bash
# 复制文件到服务器
scp -r -i ~/.ssh/vet_ai_deploy \
  docker/ backend/ config/ core/ utils/ \
  pyproject.toml uv.lock \
  root@129.204.9.209:/opt/vet-ai/

# SSH到服务器
ssh -i ~/.ssh/vet_ai_deploy root@129.204.9.209

# 在服务器上运行部署脚本
cd /opt/vet-ai/docker
bash /opt/vet-ai/scripts/deploy-server.sh
```

---

## 🚀 自动部署触发

### 方式一：推送代码（自动触发）

```bash
# 推送到main/master分支
git add .
git commit -m "feat: 新功能"
git push origin main
```

**自动触发流程**：
1. GitHub Actions检测到推送
2. 构建Docker镜像
3. 部署到服务器
4. 运行健康检查
5. 发送部署报告

### 方式二：手动触发

1. 访问GitHub仓库
2. 点击 "Actions" 标签
3. 选择 "Build and Deploy to Production" 工作流
4. 点击 "Run workflow" 按钮
5. 选择分支和环境
6. 点击 "Run workflow" 确认

---

## 📊 部署工作流详解

### 工作流文件

**位置**: `.github/workflows/deploy.yml`

### 工作流步骤

#### Job 1: 构建并推送镜像

```yaml
- Checkout代码
- 设置Docker Buildx
- 登录Docker Hub
- 构建镜像
- 推送镜像
```

#### Job 2: 部署到服务器

```yaml
- Checkout代码
- 配置SSH密钥
- 复制文件到服务器
- SSH执行部署脚本:
  - 停止旧服务
  - 构建新镜像
  - 启动新服务
  - 健康检查
```

#### Job 3: 发送通知（可选）

- 部署成功/失败通知
- 部署报告

---

## 🔍 监控和日志

### 查看部署状态

1. **GitHub Actions界面**
   - 访问仓库的 "Actions" 标签
   - 查看工作流运行历史
   - 点击具体任务查看详细日志

2. **服务器日志**

```bash
# SSH到服务器
ssh root@129.204.9.209

# 查看应用日志
cd /opt/vet-ai/docker
docker-compose logs -f vet-ai

# 查看部署日志
cat /opt/vet-ai/docker/deploy.log
```

### 部署报告

每次部署后，GitHub Actions会生成部署报告，包含：
- 部署时间
- 提交SHA
- 服务状态
- 容器状态

---

## 🛠️ 服务器端部署脚本

### deploy-server.sh

**位置**: `scripts/deploy-server.sh`

**功能**：
- ✅ 检查系统要求
- ✅ 备份当前部署
- ✅ 停止旧服务
- ✅ 构建新镜像
- ✅ 启动新服务
- ✅ 健康检查
- ✅ 清理旧镜像
- ✅ 日志记录

**手动运行**：

```bash
ssh root@129.204.9.209
cd /opt/vet-ai
bash scripts/deploy-server.sh
```

---

## ⚠️ 故障排查

### 问题1: SSH连接失败

**症状**:
```
Permission denied (publickey)
```

**解决方案**:
1. 检查SSH密钥是否正确配置
2. 验证服务器authorized_keys文件
3. 测试SSH连接

```bash
ssh -i ~/.ssh/vet_ai_deploy root@129.204.9.209
```

### 问题2: Docker构建失败

**症状**:
```
ERROR: Docker build failed
```

**解决方案**:
1. 检查服务器Docker是否正常运行
2. 查看构建日志
3. 清理Docker缓存

```bash
ssh root@129.204.9.209
docker system prune -a -f
```

### 问题3: 服务启动失败

**症状**:
```
Service not responding
```

**解决方案**:
1. 查看服务日志
2. 检查环境变量配置
3. 验证端口是否被占用

```bash
cd /opt/vet-ai/docker
docker-compose logs vet-ai
docker-compose ps
netstat -tlnp | grep 18082
```

### 问题4: 健康检查失败

**症状**:
```
Health check timeout
```

**解决方案**:
1. 等待更长时间（服务可能需要更长启动时间）
2. 检查服务是否正常运行
3. 验证健康端点是否可访问

```bash
curl http://localhost:18082/health
```

---

## 🔒 安全建议

### ✅ 安全最佳实践

1. **使用SSH密钥认证**
   - ✅ 不使用密码登录
   - ✅ 密钥设置密码保护
   - ✅ 定期轮换密钥

2. **限制SSH访问**
   - 只允许必要的IP地址访问
   - 使用防火墙规则
   - 定期审查登录日志

3. **保护GitHub Secrets**
   - ✅ 不在代码中硬编码敏感信息
   - ✅ 使用GitHub Secrets存储密钥
   - ✅ 定期更新密钥

4. **更新和补丁**
   - 定期更新Docker
   - 定期更新系统包
   - 及时修复安全漏洞

---

## 📝 环境变量配置

### 服务器端 .env 文件

```bash
# LLM配置
MODEL_NAME=glm-4-plus
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
API_KEY=your_api_key_here

# 服务配置
DEBUG=false
ENABLE_DOCS=true
LOG_LEVEL=INFO

# CORS配置
ALLOWED_HOSTS=*
CORS_ALLOW_CREDENTIALS=true
```

**文件位置**: `/opt/vet-ai/docker/.env`

---

## 🎉 部署成功验证

### 访问服务

部署成功后，可通过以下URL访问：

- **Swagger UI**: http://129.204.9.209:18082/api/docs
- **ReDoc**: http://129.204.9.209:18082/api/redoc
- **健康检查**: http://129.204.9.209:18082/health

### 验证脚本

```bash
#!/bin/bash
# 验证部署

# 1. 健康检查
curl -f http://129.204.9.209:18082/health || exit 1

# 2. 检查API文档
curl -f http://129.204.9.209:18082/api/docs > /dev/null || exit 1

# 3. 测试API端点
curl -X POST http://129.204.9.209:18082/api/v1/pet-care/plan \
  -H "Content-Type: application/json" \
  -d '{"user_query":"测试","pet_species":"狗"}' \
  -f > /dev/null || exit 1

echo "✅ 所有验证通过！"
```

---

## 📚 相关文档

- [Docker部署指南](../docker/README.md)
- [API文档](../docker/FILES.md)
- [环境变量配置](../docker/.env.example)

---

## 💡 提示

1. **首次部署**: 建议先手动部署一次，确保所有配置正确
2. **测试环境**: 可以设置staging分支，先部署到测试环境
3. **回滚**: 如果部署失败，可以手动回滚到之前的备份
4. **监控**: 建议配置日志监控和告警

---

## 📞 支持

如有问题，请查看：
1. GitHub Actions运行日志
2. 服务器部署日志
3. Docker容器日志

---

**版本**: 1.0.0
**更新时间**: 2026-01-27
**维护者**: Vet-AI Team
