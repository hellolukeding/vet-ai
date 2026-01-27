# Docker 文件清单

本目录包含 Vet-AI 项目的轻量化 Docker 部署配置。

## 📁 文件说明

### 核心配置文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `Dockerfile` | Docker镜像构建配置 | 定义轻量化多阶段构建流程 |
| `docker-compose.yml` | Docker Compose配置 | 定义服务编排和资源配置 |
| `.dockerignore` | Docker排除文件 | 减少构建上下文大小 |
| `.env.example` | 环境变量示例 | 配置模板，需复制为.env并填写 |

### 辅助文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `deploy.sh` | 快速部署脚本 | 一键构建和启动服务 |
| `README.md` | 部署指南 | 详细的使用说明和故障排查 |
| `OPTIMIZATION.md` | 优化说明 | Docker轻量化优化详解 |

## 🚀 快速开始

### 方式一：使用部署脚本（推荐）

```bash
cd docker
./deploy.sh
```

### 方式二：手动部署

```bash
cd docker

# 1. 配置环境变量
cp .env.example .env
vi .env

# 2. 构建镜像
docker-compose build

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f vet-ai
```

## 📊 轻量化优化

### 优化成果

- ✅ **镜像大小**: 从 ~800MB 降至 ~300-400MB（减少 50-60%）
- ✅ **构建速度**: 从 10-15分钟 降至 3-5分钟（提升 60-70%）
- ✅ **启动时间**: 从 10-15秒 降至 5-10秒（提升 30%）
- ✅ **内存占用**: 从 200-300MB 降至 150-200MB（减少 20%）

### 关键优化技术

1. **基础镜像**: python:3.12-slim（~150MB）
2. **多阶段构建**: 分离构建和运行环境
3. **uv包管理器**: 更快更小的依赖管理
4. **层缓存优化**: 依赖在前，代码在后
5. **完善.dockerignore**: 减少构建上下文

详见：[OPTIMIZATION.md](OPTIMIZATION.md)

## 🔗 服务访问

部署完成后，可通过以下URL访问服务：

- **Swagger UI**: http://localhost:8080/api/docs
- **ReDoc**: http://localhost:8080/api/redoc
- **健康检查**: http://localhost:8080/health
- **OpenAPI JSON**: http://localhost:8080/api/openapi.json

## 🛠️ 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f vet-ai

# 重新构建
docker-compose build --no-cache

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec vet-ai bash
```

## 📝 配置说明

### 环境变量

主要配置项（在 .env 文件中设置）：

```bash
# LLM配置
MODEL_NAME=glm-4-plus
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
API_KEY=your_api_key_here

# 服务配置
HOST=0.0.0.0
PORT=8080
DEBUG=false

# 日志配置
LOG_LEVEL=INFO
```

### 资源限制

默认配置（可在 docker-compose.yml 中调整）：

```yaml
deploy:
  resources:
    limits:
      cpus: '2'      # CPU限制
      memory: 2G     # 内存限制
    reservations:
      cpus: '0.5'    # CPU预留
      memory: 512M   # 内存预留
```

## 🔍 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs vet-ai

# 检查配置
docker-compose config

# 验证环境变量
docker-compose exec vet-ai env | grep API_KEY
```

### 健康检查失败

```bash
# 手动健康检查
docker-compose exec vet-ai curl http://localhost:8080/health
```

### 重新构建

```bash
# 完全重建（清除缓存）
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📚 更多文档

- [部署指南](README.md) - 详细的部署和使用说明
- [优化说明](OPTIMIZATION.md) - Docker轻量化优化详解
- [项目README](../README.md) - 项目整体说明

## 💡 提示

1. 首次构建需要下载依赖，请耐心等待 3-5 分钟
2. 确保 `.env` 文件中的 API_KEY 已正确配置
3. 生产环境建议设置 `DEBUG=false`
4. 定期清理未使用的镜像：`docker image prune -a`

## 📞 支持

如有问题，请查阅：
1. [README.md](README.md) - 部署指南
2. [项目Issues](https://github.com/your-repo/issues)
3. [Docker文档](https://docs.docker.com/)

---

**版本**: 2.0.0
**更新时间**: 2026-01-27
**维护者**: Vet-AI Team
