#!/bin/bash
# scripts/stop_all.sh
# 停止所有服务

set -e

echo "=========================================="
echo "   Self-Media Platform - Stop All"
echo "=========================================="

# 颜色输出
GREEN='\033[0;32m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# 停止前端
echo "Stopping Frontend..."
if lsof -i :3000 > /dev/null 2>&1; then
    lsof -ti :3000 | xargs kill -15 2>/dev/null || true
    print_status "Frontend stopped"
else
    echo "  Frontend is not running"
fi

# 停止后端
echo "Stopping Backend..."
if lsof -i :8000 > /dev/null 2>&1; then
    lsof -ti :8000 | xargs kill -15 2>/dev/null || true
    print_status "Backend stopped"
else
    echo "  Backend is not running"
fi

# 停止 DailyHotApi
echo "Stopping DailyHotApi..."
if lsof -i :6688 > /dev/null 2>&1; then
    lsof -ti :6688 | xargs kill -15 2>/dev/null || true
    print_status "DailyHotApi stopped"
else
    echo "  DailyHotHotApi is not running"
fi

echo ""
echo "All services stopped."
