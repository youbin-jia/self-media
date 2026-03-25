#!/bin/bash
# scripts/start_all.sh
# 一键启动所有服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "   Self-Media Platform - Start All"
echo "=========================================="

cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 1. 检查环境
echo ""
echo "=== Checking Environment ==="

if command -v node &> /dev/null; then
    print_status "Node.js: $(node --version)"
else
    print_error "Node.js is not installed"
    exit 1
fi

if command -v python3 &> /dev/null; then
    print_status "Python: $(python3 --version)"
else
    print_error "Python3 is not installed"
    exit 1
fi

if command -v redis-cli &> /dev/null; then
    print_status "Redis CLI: available"
else
    print_warning "Redis CLI not found (optional for local dev)"
fi

# 2. 启动 Redis (如果未运行)
echo ""
echo "=== Starting Redis ==="
if redis-cli ping > /dev/null 2>&1; then
    print_status "Redis is already running"
else
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
        sleep 1
        print_status "Redis started"
    else
        print_warning "Redis not installed, skipping..."
    fi
fi

# 3. 启动 DailyHotApi
echo ""
echo "=== Starting DailyHotApi ==="
if lsof -i :6688 > /dev/null 2>&1; then
    print_status "DailyHotApi is already running on port 6688"
else
    bash "$SCRIPT_DIR/start_dailyhot.sh"
fi

# 4. 启动后端
echo ""
echo "=== Starting Backend ==="
if lsof -i :8000 > /dev/null 2>&1; then
    print_status "Backend is already running on port 8000"
else
    cd "$PROJECT_ROOT/backend"

    # 检查虚拟环境
    if [ -d "../venv" ]; then
        source ../venv/bin/activate
        print_status "Activated virtual environment"
    fi

    # 启动后端
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!

    # 等待启动
    for i in {1..15}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Backend started on http://localhost:8000"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_error "Backend failed to start. Check /tmp/backend.log"
    fi
fi

# 5. 启动前端
echo ""
echo "=== Starting Frontend ==="
if lsof -i :3000 > /dev/null 2>&1; then
    print_status "Frontend is already running on port 3000"
else
    cd "$PROJECT_ROOT/frontend"

    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    # 启动前端
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!

    # 等待启动
    for i in {1..15}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_status "Frontend started on http://localhost:3000"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_error "Frontend failed to start. Check /tmp/frontend.log"
    fi
fi

# 6. 刷新热榜数据
echo ""
echo "=== Refreshing Hot Topics ==="
sleep 2
if curl -s -X POST http://localhost:8000/api/topics/refresh > /dev/null 2>&1; then
    print_status "Hot topics refreshed"
else
    print_warning "Failed to refresh hot topics"
fi

# 7. 打开浏览器
echo ""
echo "=========================================="
echo "   All Services Started Successfully!"
echo "=========================================="
echo ""
echo "Services:"
echo "  • Frontend:    http://localhost:3000"
echo "  • Backend:     http://localhost:8000"
echo "  • DailyHotApi: http://localhost:6688"
echo ""
echo "Log files:"
echo "  • Backend:     /tmp/backend.log"
echo "  • Frontend:    /tmp/frontend.log"
echo "  • DailyHotApi: $PROJECT_ROOT/services/dailyhot-api/logs/dailyhot.log"
echo ""

# 打开浏览器
if command -v open &> /dev/null; then
    echo "Opening browser..."
    open http://localhost:3000
fi
