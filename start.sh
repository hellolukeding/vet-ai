#!/bin/bash

# 启动后端服务
echo "启动后端服务..."
cd /Users/lukeding/Desktop/playground/2025/vet-ai
PYTHONPATH=/Users/lukeding/Desktop/playground/2025/vet-ai uv run start-server &
BACKEND_PID=$!

# 等待后端服务启动
sleep 5

# 启动前端服务
echo "启动前端服务..."
cd /Users/lukeding/Desktop/playground/2025/vet-ai/frontend/vet-ai
npm run dev

# 当脚本被终止时，同时终止后端进程
trap "kill $BACKEND_PID" EXIT