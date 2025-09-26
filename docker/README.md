# VET-AI 后端 Docker 部署指南

本文档描述如何使用 Docker Compose 部署 VET-AI 后端服务。

## 🏗️ 架构概览

部署包含以下服务：

- **vet-ai-backend**: FastAPI 应用服务器
- **mongo**: MongoDB 数据库
- **nginx**: 反向代理和负载均衡器 (可选)

## 📋 前置要求

1. **Docker** (版本 20.10+)
2. **Docker Compose** (版本 1.29+)
3. **至少 2GB 可用内存**
4. **至少 5GB 可用磁盘空间**

## 🚀 快速部署

### 1. 准备源码

```bash
# 将源码拉取到服务器
git clone <your-repo-url> vet-ai
cd vet-ai
```

### 2. 配置环境变量

```bash
# 开发环境
cp docker/.env.example docker/.env

# 生产环境 (可选)
cp docker/.env.prod.example docker/.env

# 编辑配置文件
vim docker/.env
```

**重要配置项**:

```bash
# AI模型API密钥 (必须修改)
API_KEY=your-actual-api-key

# 应用密钥 (生产环境必须修改)
SECRET_KEY=your-super-secret-key-for-production

# MongoDB 密码 (建议修改)
MONGO_INITDB_ROOT_PASSWORD=your-secure-mongo-password
```

### 3. 一键部署

```bash
# 使用部署脚本
./docker/deploy.sh
```

或手动部署：

```bash
# 构建镜像
docker-compose -f docker/docker-compose.yml build

# 启动服务
docker-compose -f docker/docker-compose.yml up -d
```

## 📊 服务访问

部署成功后，可以通过以下地址访问：

- **API 文档**: http://localhost:8080/docs
- **API 服务**: http://localhost:8080
- **通过 Nginx**: http://localhost:80
- **健康检查**: http://localhost:8080/health

## 🔧 环境变量配置

本部署使用 `.env` 文件进行环境变量管理，所有配置都通过 `env_file` 方式映射到容器中。

### 配置文件说明

- **`.env.example`**: 开发环境配置模板
- **`.env.prod.example`**: 生产环境配置模板
- **`.env`**: 实际使用的配置文件（需要自行创建）

### 环境变量分类

| 类别     | 变量名                       | 说明               |
| -------- | ---------------------------- | ------------------ |
| AI 模型  | `API_KEY`                    | AI 模型 API 密钥   |
| 应用配置 | `SECRET_KEY`                 | JWT 签名密钥       |
| 数据库   | `MONGO_INITDB_ROOT_PASSWORD` | MongoDB 管理员密码 |
| CORS     | `ALLOWED_HOSTS`              | 允许的域名列表     |

### 生产环境部署

```bash
# 使用生产环境配置
cp docker/.env.prod.example docker/.env
vim docker/.env  # 修改敏感信息

# 使用生产环境compose文件
docker-compose -f docker/docker-compose.prod.yml up -d
```

## 🔧 管理命令

### 查看服务状态

```bash
docker-compose -f docker/docker-compose.yml ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker/docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f docker/docker-compose.yml logs -f vet-ai-backend
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker/docker-compose.yml restart

# 重启特定服务
docker-compose -f docker/docker-compose.yml restart vet-ai-backend
```

### 停止服务

```bash
docker-compose -f docker/docker-compose.yml down
```

### 完全清理

```bash
# 停止并删除容器、网络和卷
docker-compose -f docker/docker-compose.yml down -v
docker system prune -f
```

## 📁 目录结构

```
docker/
├── Dockerfile              # 后端应用镜像定义
├── docker-compose.yml      # 服务编排配置
├── .dockerignore           # Docker 忽略文件
├── .env.example            # 环境变量模板
├── deploy.sh               # 一键部署脚本
├── nginx/
│   └── nginx.conf          # Nginx 配置
└── mongo-init/
    └── init-mongo.sh       # MongoDB 初始化脚本
```

## 🔐 安全配置

### 生产环境建议

1. **修改默认密码**

   ```bash
   # 生成强密码
   openssl rand -base64 32
   ```

2. **启用 HTTPS**

   - 将 SSL 证书放入 `docker/nginx/ssl/`
   - 取消注释 nginx.conf 中的 HTTPS 配置

3. **限制网络访问**

   ```yaml
   # 在 docker-compose.yml 中修改端口映射
   ports:
     - "127.0.0.1:8080:8080" # 只允许本地访问
   ```

4. **设置防火墙规则**
   ```bash
   # 只允许必要端口
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw deny 8080/tcp
   ```

## 🐛 故障排除

### 常见问题

1. **端口被占用**

   ```bash
   # 检查端口使用
   netstat -tulpn | grep :8080

   # 修改 docker-compose.yml 中的端口映射
   ports:
     - "8081:8080"  # 改为其他端口
   ```

2. **内存不足**

   ```bash
   # 检查内存使用
   free -h

   # 添加交换空间
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **API 连接失败**

   ```bash
   # 检查容器状态
   docker-compose -f docker/docker-compose.yml ps

   # 检查容器日志
   docker-compose -f docker/docker-compose.yml logs vet-ai-backend

   # 测试网络连接
   docker exec -it vet-ai-backend curl localhost:8080/health
   ```

4. **数据库连接失败**

   ```bash
   # 检查 MongoDB 容器
   docker-compose -f docker/docker-compose.yml logs mongo

   # 进入 MongoDB 容器
   docker exec -it vet-ai-mongo mongo
   ```

### 日志位置

- **应用日志**: `./logs/`
- **运行记录**: `./runs/`
- **Docker 日志**: `docker-compose logs`

## 🔄 更新部署

1. **拉取新代码**

   ```bash
   git pull origin main
   ```

2. **重建镜像**

   ```bash
   docker-compose -f docker/docker-compose.yml build --no-cache
   ```

3. **重启服务**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

## 📈 性能优化

### 资源限制

```yaml
# 在 docker-compose.yml 中添加
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 2G
    reservations:
      memory: 1G
```

### 水平扩展

```bash
# 启动多个后端实例
docker-compose -f docker/docker-compose.yml up -d --scale vet-ai-backend=3
```

## 📞 支持

如遇问题，请：

1. 检查日志文件
2. 查看本文档的故障排除部分
3. 提交 GitHub Issue

---

**注意**: 本部署配置适用于开发和小型生产环境。大规模生产部署建议使用 Kubernetes 或其他容器编排平台。
