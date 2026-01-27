# 快速部署指南

## 🚀 5分钟快速部署

### 前置条件检查

```bash
# 1. 检查Docker
docker --version
# 应显示: Docker version 20.10.x 或更高

# 2. 检查Docker Compose
docker-compose --version
# 应显示: Docker Compose version 2.x.x 或更高

# 3. 检查端口
netstat -tlnp | grep 18082
# 应该没有输出（端口未被占用）
```

---

## 🎯 部署步骤

### 方式A：自动部署（GitHub Actions）

#### 第一步：配置SSH

```bash
cd scripts
./setup-ssh.sh
```

#### 第二步：配置GitHub Secrets

在GitHub仓库中添加以下Secrets：

1. `SERVER_HOST` = `129.204.9.209`
2. `SERVER_USER` = `root`
3. `SSH_PRIVATE_KEY` = (私钥内容)

#### 第三步：推送代码触发部署

```bash
git add .
git commit -m "feat: 自动部署配置"
git push origin main
```

**完成！** GitHub Actions将自动部署到服务器。

---

### 方式B：手动部署

#### 第一步：准备服务器

```bash
# SSH到服务器
ssh root@129.204.9.209
# 密码: aK3!eF4!bB3*cJ0]bH

# 创建项目目录
mkdir -p /opt/vet-ai
cd /opt/vet-ai
```

#### 第二步：上传代码

```bash
# 在本地机器执行
rsync -avz --progress \
  docker/ backend/ config/ core/ utils/ \
  pyproject.toml uv.lock \
  root@129.204.9.209:/opt/vet-ai/
```

#### 第三步：配置环境变量

```bash
# SSH到服务器
ssh root@129.204.9.209

# 配置.env文件
cd /opt/vet-ai/docker
cp .env.example .env
vi .env  # 填写API密钥等配置
```

#### 第四步：部署

```bash
cd /opt/vet-ai
bash scripts/deploy-server.sh
```

**完成！** 服务将自动启动。

---

## ✅ 验证部署

### 健康检查

```bash
curl http://129.204.9.209:18082/health
```

应该返回：
```json
{
  "status": "healthy",
  "message": "服务运行正常"
}
```

### 访问API文档

浏览器访问：
- Swagger UI: http://129.204.9.209:18082/api/docs
- ReDoc: http://129.204.9.209:18082/api/redoc

### 查看日志

```bash
# SSH到服务器
ssh root@129.204.9.209

# 查看应用日志
cd /opt/vet-ai/docker
docker-compose logs -f vet-ai
```

---

## 🔄 更新部署

### 自动部署

```bash
# 只需推送代码
git add .
git commit -m "feat: 新功能"
git push origin main
```

### 手动更新

```bash
# 1. 上传新代码
rsync -avz --progress \
  docker/ backend/ config/ core/ utils/ \
  pyproject.toml uv.lock \
  root@129.204.9.209:/opt/vet-ai/

# 2. SSH到服务器重新部署
ssh root@129.204.9.209
cd /opt/vet-ai
bash scripts/deploy-server.sh
```

---

## 🛑 停止服务

```bash
ssh root@129.204.9.209
cd /opt/vet-ai/docker
docker-compose down
```

---

## 🔧 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f vet-ai

# 重启服务
docker-compose restart

# 进入容器
docker-compose exec vet-ai bash

# 查看资源使用
docker stats vet-ai-backend
```

---

## ⚠️ 常见问题

### Q: 端口被占用

```bash
# 查找占用进程
lsof -i :18082

# 杀死进程
kill -9 [PID]

# 或修改docker-compose.yml中的端口映射
```

### Q: 服务启动失败

```bash
# 查看详细日志
docker-compose logs vet-ai

# 检查环境变量
docker-compose exec vet-ai env | grep API_KEY

# 手动健康检查
docker-compose exec vet-ai curl http://localhost:8080/health
```

### Q: 镜像构建失败

```bash
# 清理Docker缓存
docker system prune -a -f

# 重新构建
docker-compose build --no-cache
```

---

## 📞 需要帮助？

查看详细文档：
- [完整部署指南](DEPLOYMENT.md)
- [Docker部署](../docker/README.md)
- [故障排查](../docker/README.md#故障排查)
