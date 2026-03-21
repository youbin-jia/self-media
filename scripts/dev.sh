#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.devrun"
LOG_DIR="$RUN_DIR/logs"
PID_DIR="$RUN_DIR/pids"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
WORKER_PID_FILE="$PID_DIR/worker.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
REDIS_PID_FILE="$PID_DIR/redis.pid"

mkdir -p "$LOG_DIR" "$PID_DIR"

print_usage() {
  cat <<'EOF'
Usage:
  ./scripts/dev.sh start    # 一键启动 Redis(可选)、API、Worker、Frontend
  ./scripts/dev.sh stop     # 一键停止本脚本启动的服务
  ./scripts/dev.sh status   # 查看服务状态
  ./scripts/dev.sh logs     # 查看日志路径
  ./scripts/dev.sh tail     # 实时查看服务日志（Ctrl+C 退出）
  ./scripts/dev.sh check-llm # 检查默认LLM配置与可用性
EOF
}

require_cmd() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[precheck] 缺少命令: $cmd"
    echo "           $hint"
    return 1
  fi
}

is_running() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

get_pid_by_port() {
  local port="$1"
  local line pid
  line="$(ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print; exit}')"
  pid="$(echo "$line" | sed -n 's/.*pid=\([0-9]\+\).*/\1/p')"
  if [[ -n "$pid" ]]; then
    echo "$pid"
    return 0
  fi
  return 1
}

is_pid_from_file() {
  local pid_file="$1"
  local pid="$2"
  [[ -f "$pid_file" ]] && [[ "$(cat "$pid_file" 2>/dev/null || true)" == "$pid" ]]
}

wait_for_pid_healthy() {
  local name="$1"
  local pid_file="$2"
  local timeout_s="${3:-5}"
  local waited=0
  while [[ $waited -lt $timeout_s ]]; do
    if is_running "$pid_file"; then
      sleep 1
      waited=$((waited + 1))
    else
      echo "[$name] 启动失败，请查看日志: $LOG_DIR/$name.log"
      return 1
    fi
  done
  return 0
}

wait_for_http_ok() {
  local name="$1"
  local url="$2"
  local timeout_s="${3:-30}"
  local waited=0
  while [[ $waited -lt $timeout_s ]]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[$name] 健康检查通过: $url"
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  echo "[$name] 健康检查失败: $url"
  return 1
}

verify_backend_routes() {
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/projects/any-project-id/steps/script/execute")"
  # route exists -> GET should be 405 (method not allowed). 404 means route missing.
  if [[ "$code" == "404" ]]; then
    echo "[backend] 关键路由缺失: /api/projects/{id}/steps/script/execute"
    echo "          当前服务可能不是最新代码，请重启并确认运行目录。"
    return 1
  fi
  echo "[backend] 路由检查通过 (HTTP $code)"
}

precheck_ports() {
  local backend_pid
  backend_pid="$(get_pid_by_port 8000 || true)"
  if [[ -n "$backend_pid" ]] && ! is_pid_from_file "$BACKEND_PID_FILE" "$backend_pid"; then
    local cmdline
    cmdline="$(tr '\0' ' ' </proc/"$backend_pid"/cmdline 2>/dev/null || true)"
    if echo "$cmdline" | awk '/uvicorn app.main:app/ {found=1} END{exit !found}'; then
      echo "[precheck] 发现外部旧后端进程占用 8000，自动停止 (pid=$backend_pid)"
      kill "$backend_pid" || true
      sleep 1
    else
      echo "[precheck] 端口 8000 被其他进程占用 (pid=$backend_pid)"
      echo "           请先释放端口后再执行 ./scripts/dev.sh start"
      return 1
    fi
  fi
}

run_prechecks() {
  require_cmd ss "请安装 iproute2（通常系统自带）"
  require_cmd curl "请安装 curl 用于健康检查"
  require_cmd npm "请先安装 Node.js / npm"
  precheck_ports
}

start_if_needed() {
  local name="$1"
  local pid_file="$2"
  local workdir="$3"
  local logfile="$4"
  shift 4

  if is_running "$pid_file"; then
    echo "[$name] 已在运行 (pid=$(cat "$pid_file"))"
    return 0
  fi

  (
    cd "$workdir"
    nohup "$@" >"$logfile" 2>&1 &
    echo $! >"$pid_file"
  )
  echo "[$name] 已启动 (pid=$(cat "$pid_file"))"

  wait_for_pid_healthy "$name" "$pid_file" 3
}

stop_if_running() {
  local name="$1"
  local pid_file="$2"

  if ! [[ -f "$pid_file" ]]; then
    echo "[$name] 未运行"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" || true
    fi
    echo "[$name] 已停止"
  else
    echo "[$name] 进程不存在，清理 PID 文件"
  fi
  rm -f "$pid_file"
}

ensure_backend_env() {
  if [[ ! -f "$ROOT_DIR/backend/.env" ]]; then
    cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
    echo "[backend] 已创建 backend/.env（来自 .env.example）"
  fi
  mkdir -p "$ROOT_DIR/backend/data"
}

ensure_frontend_deps() {
  if [[ ! -x "$ROOT_DIR/frontend/node_modules/.bin/vite" ]]; then
    echo "[frontend] 正在安装依赖 npm install ..."
    (cd "$ROOT_DIR/frontend" && npm install)
  fi
}

ensure_redis() {
  if command -v redis-cli >/dev/null 2>&1 && redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
    echo "[redis] 已可用 (localhost:6379)"
    return 0
  fi

  if ! command -v redis-server >/dev/null 2>&1; then
    echo "[redis] 未检测到 redis-server，请先安装或手动启动 Redis"
    return 1
  fi

  if is_running "$REDIS_PID_FILE"; then
    echo "[redis] PID 记录存在但不可用，尝试重启"
    stop_if_running "redis" "$REDIS_PID_FILE"
  fi

  nohup redis-server >"$LOG_DIR/redis.log" 2>&1 &
  echo $! >"$REDIS_PID_FILE"
  sleep 1

  if command -v redis-cli >/dev/null 2>&1 && redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
    echo "[redis] 已启动 (pid=$(cat "$REDIS_PID_FILE"))"
    return 0
  fi

  echo "[redis] 启动失败，请查看日志: $LOG_DIR/redis.log"
  return 1
}

build_backend_cmd() {
  if command -v uvicorn >/dev/null 2>&1; then
    echo "uvicorn app.main:app --reload"
  elif command -v conda >/dev/null 2>&1; then
    echo "conda run -n self-media uvicorn app.main:app --reload"
  else
    return 1
  fi
}

build_worker_cmd() {
  if command -v celery >/dev/null 2>&1; then
    echo "celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low"
  elif command -v conda >/dev/null 2>&1; then
    echo "conda run -n self-media celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low"
  else
    return 1
  fi
}

do_start() {
  run_prechecks
  ensure_backend_env
  ensure_frontend_deps
  ensure_redis

  local backend_cmd
  local worker_cmd
  backend_cmd="$(build_backend_cmd)" || {
    echo "[backend] 未找到 uvicorn，且 conda 不可用，请先安装或激活环境"
    return 1
  }
  worker_cmd="$(build_worker_cmd)" || {
    echo "[worker] 未找到 celery，且 conda 不可用，请先安装或激活环境"
    return 1
  }

  start_if_needed \
    "backend" \
    "$BACKEND_PID_FILE" \
    "$ROOT_DIR/backend" \
    "$LOG_DIR/backend.log" \
    bash -lc "$backend_cmd"

  start_if_needed \
    "worker" \
    "$WORKER_PID_FILE" \
    "$ROOT_DIR/backend" \
    "$LOG_DIR/worker.log" \
    bash -lc "$worker_cmd"

  start_if_needed \
    "frontend" \
    "$FRONTEND_PID_FILE" \
    "$ROOT_DIR/frontend" \
    "$LOG_DIR/frontend.log" \
    npm run dev

  wait_for_http_ok "backend" "http://127.0.0.1:8000/health" 30
  verify_backend_routes

  echo
  echo "启动完成："
  echo "  API      -> http://127.0.0.1:8000"
  echo "  Frontend -> 查看 $LOG_DIR/frontend.log 中的 Vite 地址"
  echo "  日志目录 -> $LOG_DIR"
}

do_stop() {
  stop_if_running "frontend" "$FRONTEND_PID_FILE"
  stop_if_running "worker" "$WORKER_PID_FILE"
  stop_if_running "backend" "$BACKEND_PID_FILE"
  stop_if_running "redis" "$REDIS_PID_FILE"
}

do_status() {
  if is_running "$REDIS_PID_FILE"; then
    echo "[redis] 运行中 (pid=$(cat "$REDIS_PID_FILE"))"
  elif command -v redis-cli >/dev/null 2>&1 && redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
    echo "[redis] 运行中 (外部进程)"
  else
    echo "[redis] 未运行"
  fi

  for item in \
    "backend:$BACKEND_PID_FILE" \
    "worker:$WORKER_PID_FILE" \
    "frontend:$FRONTEND_PID_FILE"
  do
    local_name="${item%%:*}"
    local_pid_file="${item##*:}"
    if is_running "$local_pid_file"; then
      echo "[$local_name] 运行中 (pid=$(cat "$local_pid_file"))"
    else
      echo "[$local_name] 未运行"
    fi
  done
}

do_logs() {
  echo "日志目录: $LOG_DIR"
  echo "可用日志:"
  ls -1 "$LOG_DIR" 2>/dev/null || true
}

do_tail() {
  local files=()
  [[ -f "$LOG_DIR/backend.log" ]] && files+=("$LOG_DIR/backend.log")
  [[ -f "$LOG_DIR/worker.log" ]] && files+=("$LOG_DIR/worker.log")
  [[ -f "$LOG_DIR/frontend.log" ]] && files+=("$LOG_DIR/frontend.log")
  [[ -f "$LOG_DIR/redis.log" ]] && files+=("$LOG_DIR/redis.log")

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "未找到日志文件，请先执行 ./scripts/dev.sh start"
    return 1
  fi

  echo "实时日志输出（Ctrl+C 退出）:"
  tail -f "${files[@]}"
}

build_python_cmd() {
  if command -v conda >/dev/null 2>&1; then
    echo "conda run --no-capture-output -n self-media python"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    return 1
  fi
}

do_check_llm() {
  ensure_backend_env
  local python_cmd
  python_cmd="$(build_python_cmd)" || {
    echo "[check-llm] 未找到 python（且 conda 不可用）"
    return 1
  }

  (
    cd "$ROOT_DIR/backend"
    bash -lc "$python_cmd - <<'PY'
import asyncio
import sys

from app.config import settings
from app.services.llm import llm_manager

provider_name = settings.DEFAULT_LLM_PROVIDER
print(f'[check-llm] DEFAULT_LLM_PROVIDER={provider_name}')

try:
    provider = llm_manager.get_provider(provider_name)
except Exception as exc:
    print(f'[check-llm] provider加载失败: {exc}')
    sys.exit(1)

model = getattr(provider, 'default_model', None) or (
    provider.available_models[0] if provider.available_models else 'unknown'
)
print(f'[check-llm] provider={provider.provider_name}, model={model}')

async def _check():
    text = await provider.generate(
        '请仅返回字符串OK',
        model=model,
        max_tokens=16,
        temperature=0.0
    )
    return text or ''

try:
    result = asyncio.run(_check()).strip().replace('\n', ' ')
    print(f'[check-llm] 调用成功, 响应预览: {result[:120]}')
except Exception as exc:
    print(f'[check-llm] 调用失败: {exc}')
    sys.exit(2)
PY"
  )
}

main() {
  local cmd="${1:-start}"
  case "$cmd" in
    start)
      do_start
      ;;
    stop)
      do_stop
      ;;
    status)
      do_status
      ;;
    logs)
      do_logs
      ;;
    tail)
      do_tail
      ;;
    check-llm)
      do_check_llm
      ;;
    *)
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
