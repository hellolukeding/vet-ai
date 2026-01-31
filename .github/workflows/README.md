# GitHub Actions 配置说明

本项目的 GitHub Actions 配置文件位于 `.github/workflows/` 目录下。

## 工作流说明

### 1. CI - 代码检查与测试 (`ci.yml`)
**触发条件**：
- 推送到 `main`, `langgraph`, `develop` 分支
- 创建 Pull Request 到 `main` 或 `langgraph`

**功能**：
- ✅ Ruff 代码质量检查
- ✅ Ruff 代码格式化检查
- ✅ MyPy 类型检查
- ✅ Docker 镜像构建测试

### 2. Docker - 构建与推送 (`docker-build.yml`)
**触发条件**：
- 推送到 `main`, `langgraph` 分支
- 创建版本标签（如 `v1.0.0`）
- 创建 Pull Request

**功能**：
- 🐳 构建 Docker 镜像
- 📦 推送到 GitHub Container Registry (ghcr.io)
- 🔒 Trivy 安全扫描
- 📊 上传安全报告到 GitHub Security

### 3. Deploy - 自动部署 (`deploy.yml`)
**触发条件**：
- 推送到 `main`, `langgraph` 分支
- 手动触发（workflow_dispatch）

**功能**：
- 🚀 自动部署到服务器
- 🔄 重启 Docker 服务
- 💚 健康检查

## 配置 GitHub Secrets

为了使 GitHub Actions 正常工作，需要在 GitHub 仓库中配置以下 Secrets：

### 基础配置

进入仓库设置：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

### 部署相关 Secrets

| Secret 名称 | 说明 | 示例值 | 必需 |
|------------|------|--------|------|
| `SSH_PRIVATE_KEY` | SSH私钥（用于连接服务器） | `-----BEGIN RSA PRIVATE KEY-----...` | ✅ |
| `SERVER_HOST` | 服务器IP地址或域名 | `192.168.1.100` 或 `example.com` | ✅ |
| `SERVER_USER` | 服务器用户名 | `root` 或 `ubuntu` | ✅ |
| `PROJECT_PATH` | 项目在服务器上的路径 | `/opt/vet-ai` | ❌ (默认: /opt/vet-ai) |
| `SERVER_PORT` | 服务端口 | `18082` | ❌ (默认: 18082) |

### SSH 密钥生成（如果还没有）

```bash
# 在本地机器上生成SSH密钥对
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions

# 将公钥复制到服务器
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server

# 将私钥内容添加到 GitHub Secrets
cat ~/.ssh/github_actions
```

复制输出的私钥内容（包括 `-----BEGIN` 和 `-----END` 行）到 GitHub Secret `SSH_PRIVATE_KEY`

## 使用说明

### 首次启用

1. **配置 Secrets**：按照上述说明配置所有必需的 Secrets
2. **推送代码**：将代码推送到 `main` 或 `langgraph` 分支
3. **查看 Actions**：在 GitHub 仓库页面点击 `Actions` 标签查看运行状态

### 手动触发部署

1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择 `Deploy - 自动部署` workflow
4. 点击 `Run workflow` 按钮
5. 选择分支并确认

### 查看 Workflow 运行日志

1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择对应的 workflow run
4. 点击具体的 job 查看详细日志

## 故障排除

### Workflow 不触发

**可能原因**：
- 分支名称不匹配
- Workflow 文件语法错误

**解决方法**：
```bash
# 检查分支名称
git branch -a

# 验证 workflow 语法
yamllint .github/workflows/*.yml
```

### SSH 连接失败

**可能原因**：
- `SSH_PRIVATE_KEY` 配置错误
- 服务器防火墙阻止连接
- SSH 公钥未添加到服务器

**解决方法**：
```bash
# 测试 SSH 连接
ssh -i ~/.ssh/github_actions user@server

# 检查服务器 SSH 配置
# /etc/ssh/sshd_config
# PubkeyAuthentication yes
```

### Docker 构建失败

**可能原因**：
- `GITHUB_TOKEN` 权限不足
- Dockerfile 语法错误
- 依赖安装失败

**解决方法**：
1. 检查仓库设置：`Settings` → `Actions` → `General` → `Workflow permissions`
2. 选择 `Read and write permissions`
3. 保存并重新运行 workflow

### 健康检查失败

**可能原因**：
- 服务未启动
- 端口配置错误
- 防火墙阻止访问

**解决方法**：
```bash
# 在服务器上检查容器状态
docker ps

# 查看容器日志
docker logs vet-ai-backend

# 手动测试健康检查
curl http://localhost:18082/health
```

## 本地测试 Workflow

在推送前，可以使用 `act` 工具本地测试 GitHub Actions：

```bash
# 安装 act (macOS)
brew install act

# 本地运行 workflow
act push

# 运行特定 job
act -j lint
```

## 注意事项

1. **Secrets 安全**：永远不要将 Secrets 提交到代码仓库
2. **SSH 密钥**：使用专用的密钥对，不要使用个人主密钥
3. **权限管理**：定期审查和更新 Secrets
4. **日志监控**：关注 workflow 运行日志，及时发现问题

## 进阶配置

### 自定义 Docker 标签

修改 `docker-build.yml` 中的标签策略：

```yaml
tags: |
  type=sha,prefix={{branch}}-
  type=raw,value=my-custom-tag,enable=true
```

### 添加通知

在 workflow 最后添加 Slack/Email 通知：

```yaml
- name: 发送通知
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: '部署完成！'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 多环境部署

复制 `deploy.yml` 并为不同环境（staging, production）创建不同的 workflow 和 secrets。

## 相关链接

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Trivy 安全扫描](https://aquasecurity.github.io/trivy/)
