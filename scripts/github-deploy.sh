#!/usr/bin/env bash

set -euo pipefail

SSH_OPTIONS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
RSYNC_EXCLUDES=(
  ".git"
  ".agents"
  ".claude"
  ".deploy"
  ".env"
  ".github"
  ".vscode"
  "docker/.env"
  "docs"
  "frontend"
  "node_modules"
  "__pycache__"
  "*.pyc"
  ".venv"
  "logs"
  ".pytest_cache"
  "skills"
  "test"
  "tests"
  "*.log"
)

trim() {
  printf '%s' "${1:-}" | xargs
}

require_env() {
  local name="$1"
  local value="${!name:-}"

  if [[ -z "$(trim "$value")" ]]; then
    echo "缺少必需环境变量: $name" >&2
    exit 1
  fi
}

sshpass_ssh() {
  sshpass -p "$SERVER_PASSWORD" ssh "${SSH_OPTIONS[@]}" "${SERVER_USER}@${SERVER_HOST}" "$@"
}

rsync_with_retry() {
  local source="$1"
  local target="$2"
  shift 2

  local attempt
  for attempt in 1 2 3; do
    if sshpass -p "$SERVER_PASSWORD" rsync "$@" -e "ssh ${SSH_OPTIONS[*]}" "$source" "$target"; then
      return 0
    fi

    if [[ "$attempt" -lt 3 ]]; then
      echo "rsync 失败，${attempt}/3，15 秒后重试..."
      sleep 15
    fi
  done

  return 1
}

build_env_file() {
  TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TEMP_DIR"' EXIT

  MODEL_NAME="${MODEL_NAME:-Qwen/Qwen3-235B-A22B-Instruct-2507}"
  BASE_URL="${BASE_URL:-https://api-inference.modelscope.cn/v1}"
  SERVER_PORT="${SERVER_PORT:-18082}"

  cat > "${TEMP_DIR}/docker.env" <<EOF
MODEL_NAME=${MODEL_NAME}
BASE_URL=${BASE_URL}
API_KEY=${API_KEY}
EOF
}

configure_ssh() {
  echo "配置 SSH known_hosts..."
  mkdir -p ~/.ssh
  ssh-keyscan -H "$SERVER_HOST" >> ~/.ssh/known_hosts
  chmod 644 ~/.ssh/known_hosts
}

verify_connection() {
  echo "测试服务器连接..."
  sshpass_ssh "echo '连接成功！' && pwd && ls -la /opt/vet-ai"
}

upload_env_file() {
  echo "上传 docker/.env 到服务器..."
  rsync_with_retry \
    "${TEMP_DIR}/docker.env" \
    "${SERVER_USER}@${SERVER_HOST}:/opt/vet-ai/docker/.env" \
    -avz
}

sync_code() {
  echo "同步代码到服务器..."

  local rsync_args=(-rlptDz --delete --no-perms --no-owner --no-group --omit-dir-times)
  local pattern

  for pattern in "${RSYNC_EXCLUDES[@]}"; do
    rsync_args+=("--exclude=${pattern}")
  done

  rsync_with_retry \
    "./" \
    "${SERVER_USER}@${SERVER_HOST}:/opt/vet-ai/" \
    "${rsync_args[@]}"
}

restart_services() {
  echo "重启 Docker 服务..."
  sshpass -p "$SERVER_PASSWORD" ssh "${SSH_OPTIONS[@]}" "${SERVER_USER}@${SERVER_HOST}" <<'ENDSSH'
set -euo pipefail
cd /opt/vet-ai

if [[ ! -f docker/.env ]]; then
  echo "缺少 docker/.env，停止部署"
  exit 1
fi

if ! grep -Eq '^API_KEY=.+' docker/.env; then
  echo "docker/.env 中缺少有效 API_KEY，停止部署"
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose -f docker/docker-compose.yml"
else
  DC="docker compose -f docker/docker-compose.yml"
fi

echo "使用经典 Docker builder 预构建镜像..."
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
timeout 45m bash -lc "$DC build vet-ai"

echo "使用已构建镜像更新服务..."
eval "$DC up -d --no-build"

echo "清理未使用的镜像..."
docker image prune -f
echo "查看容器状态..."
eval "$DC ps"
ENDSSH
}

check_health() {
  echo "等待服务启动..."
  sleep 30

  local health_url="http://${SERVER_HOST}:${SERVER_PORT}/readyz"
  local body_file
  local status_code
  local i

  echo "执行健康检查: ${health_url}"

  for i in {1..10}; do
    echo "尝试 ${i}/10..."
    body_file="$(mktemp)"
    status_code="$(curl -sS -o "$body_file" -w '%{http_code}' --connect-timeout 10 --max-time 30 "$health_url" || true)"
    cat "$body_file"
    rm -f "$body_file"

    if [[ "$status_code" == "200" ]]; then
      echo "健康检查通过！"
      return 0
    fi

    echo "健康检查未通过，HTTP 状态码: ${status_code}"
    echo "等待服务启动... (${i}/10)"
    sleep 10
  done

  echo "远程容器最近日志："
  sshpass_ssh "cd /opt/vet-ai && if command -v docker-compose >/dev/null 2>&1; then docker-compose -f docker/docker-compose.yml logs --tail=200 vet-ai redis; else docker compose -f docker/docker-compose.yml logs --tail=200 vet-ai redis; fi" || true
  echo "健康检查失败！服务未能在预期时间内启动。"
  return 1
}

show_success() {
  echo "========================================="
  echo "       部署成功！"
  echo "========================================="
  echo "服务地址: http://${SERVER_HOST}:${SERVER_PORT}"
  echo "健康检查: http://${SERVER_HOST}:${SERVER_PORT}/health"
  echo "API文档: http://${SERVER_HOST}:${SERVER_PORT}/docs"
  echo "========================================="
}

main() {
  require_env SERVER_HOST_RAW
  require_env SERVER_USER_RAW
  require_env SERVER_PASSWORD
  require_env API_KEY

  SERVER_HOST="$(trim "$SERVER_HOST_RAW")"
  SERVER_USER="$(trim "$SERVER_USER_RAW")"

  build_env_file
  configure_ssh
  verify_connection
  upload_env_file
  sync_code
  restart_services
  check_health
  show_success
}

main "$@"
