# Vet-AI Docker 轻量化部署指南

## 🚀 快速开始

### 1. 环境准备

确保已安装：
- Docker (>= 20.10)
- Docker Compose (>= 2.0)

### 2. 配置环境变量

```bash
cd docker
cp .env.example .env
# 编辑 .env 文件，填写API密钥等配置
vi .env
```

### 3. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f vet-ai
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8080/health

# 访问API文档
open http://localhost:8080/api/docs
```

## 📊 镜像信息

### 轻量化优化

- **基础镜像**: `python:3.12-slim` (~150MB)
- **最终镜像**: ~300-400MB
- **构建时间**: ~3-5分钟
- **启动时间**: ~5-10秒

### 优化策略

1. **多阶段构建**: 分离构建和运行环境
2. **最小依赖**: 只安装运行时必需的包
3. **清理缓存**: 删除构建工具和临时文件
4. **使用uv**: 比pip更快的包管理器，依赖更小
5. **非root用户**: 提高安全性

## 🛠️ 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f vet-ai

# 进入容器
docker-compose exec vet-ai bash
```

### 构建相关

```bash
# 重新构建镜像
docker-compose build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache

# 构建并启动
docker-compose up -d --build
```

### 清理

```bash
# 停止并删除容器
docker-compose down

# 删除容器和卷
docker-compose down -v

# 清理未使用的镜像
docker image prune -a

# 查看镜像大小
docker images vet-ai
```

## 📝 配置说明

### 环境变量

主要配置项：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MODEL_NAME` | LLM模型名称 | `glm-4-plus` |
| `BASE_URL` | LLM API地址 | - |
| `API_KEY` | LLM API密钥 | - |
| `DEBUG` | 调试模式 | `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 资源限制

默认配置：
- **CPU**: 2核（限制），0.5核（预留）
- **内存**: 2GB（限制），512MB（预留）

可根据需要调整 `docker-compose.yml` 中的 `deploy.resources` 配置。

## 🔍 故障排查

### 服务无法启动

```bash
# 查看日志
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

# 查看详细日志
docker-compose logs --tail=100 vet-ai
```

### 内存不足

```bash
# 查看资源使用
docker stats vet-ai

# 调整内存限制（修改docker-compose.yml）
# deploy.resources.limits.memory: 4G
```

## 📦 生产环境建议

### 1. 使用具体版本标签

```dockerfile
# 替换
FROM python:3.12-slim

# 为
FROM python:3.12.2-slim
```

### 2. 启用日志轮转

日志会自动轮转，默认配置：
- 单个文件最大: 10MB
- 保留文件数: 3

### 3. 配置重启策略

当前配置：`unless-stopped`
- 自动重启（除非手动停止）
- 服务器重启后自动启动

### 4. 监控和告警

建议配置：
- 健康检查监控
- 日志聚合（如ELK）
- 指标采集（如Prometheus）

## 🔐 安全建议

1. ✅ 使用非root用户运行
2. ✅ 不要在镜像中硬编码密钥
3. ✅ 使用`.env`文件管理敏感信息
4. ✅ 限制容器资源
5. ✅ 定期更新基础镜像
6. ⚠️ 生产环境关闭DEBUG模式

## 📚 参考资料

- [Dockerfile最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose文档](https://docs.docker.com/compose/)
- [Python Docker化指南](https://docs.python.org/3/howto/docker.html)

## 💡 提示

- 首次构建可能需要下载依赖，耐心等待
- 如果构建失败，检查网络连接和API密钥
- 生产环境建议使用具体版本号而非`latest`
- 定期清理未使用的镜像和容器
