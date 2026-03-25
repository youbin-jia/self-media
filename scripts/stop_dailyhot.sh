#!/bin/bash
# scripts/stop_dailyhot.sh
# 停止 DailyHotApi 服务

set -e

PORT=${PORT:-6688}

echo "=== Stopping DailyHotApi Service ==="

# 检查并杀死进程
if lsof -i :$PORT > /dev/null 2>&1; then
    echo "Stopping DailyHotApi on port $PORT..."
    lsof -ti :$PORT | xargs kill -15 2>/dev/null || true
    sleep 2

    # 强制杀死
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo "Force killing..."
        lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    fi

    echo "✓ DailyHotApi stopped"
else
    echo "DailyHotApi is not running"
fi
