#!/bin/bash

# 物理竞赛题库系统启动脚本

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "========================================="
echo "  物理竞赛题库系统 - 启动脚本"
echo "========================================="

if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "安装后端依赖..."
pip install -r backend/requirements.txt -q

echo "初始化数据库..."
(
  cd backend
  python init_data.py
)

echo "启动后端服务..."
(
  cd backend
  python run.py
) &
BACKEND_PID=$!

sleep 3

if [ ! -d "frontend/node_modules" ]; then
    echo "安装前端依赖..."
    (cd frontend && npm install)
fi

echo "启动前端服务..."
(
  cd frontend
  npm run dev
) &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "========================================="
echo "  服务启动完成！"
echo "========================================="
echo ""
echo "  后端API: http://localhost:5000"
echo "  前端页面: http://localhost:3000"
echo ""
echo "  默认账号:"
echo "    管理员: admin / admin1906"
echo "    教师和学生账号由管理员在系统内创建"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================="

wait "$BACKEND_PID" "$FRONTEND_PID"
