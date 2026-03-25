#!/bin/bash
# scripts/start_dailyhot.sh
# 启动 DailyHotApi 服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DAILYHOT_DIR="$PROJECT_ROOT/services/dailyhot-api"
LOG_FILE="$DAILYHOT_DIR/logs/dailyhot.log"

echo "=== Starting DailyHotApi Service ==="

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

echo "Node version: $(node --version)"

# 进入 DailyHotApi 目录
cd "$DAILYHOT_DIR"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# 创建日志目录
mkdir -p logs

# 检查端口是否被占用
PORT=${PORT:-6688}
if lsof -i :$PORT > /dev/null 2>&1; then
    echo "Warning: Port $PORT is already in use"
    echo "Checking if DailyHotApi is running..."
    if pgrep -f "dailyhot-api" > /dev/null; then
        echo "DailyHotApi is already running"
        exit 0
    else
        echo "Killing process on port $PORT..."
        lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    fi
fi

# 启动服务
echo "Starting DailyHotApi on port $PORT..."
echo "Log file: $LOG_FILE"

# 使用 nohup 后台运行
nohup npm run dev > "$LOG_FILE" 2>&1 &

# 等待服务启动
echo "Waiting for service to start..."
for i in {1..30}; do
    if curl -s "http://localhost:$PORT/weibo" > /dev/null 2>&1; then
        echo "✓ DailyHotApi is running on http://localhost:$PORT"
        echo ""
        echo "Supported platforms:"
        curl -s "http://localhost:$PORT/" 2>/dev/null | head -20 || echo "  (Check http://localhost:$PORT for available routes)"
        exit 0
    fi
    sleep 1
done

echo "Error: DailyHotApi failed to start. Check logs at: $LOG_FILE"
exit 1
