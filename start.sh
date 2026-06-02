#!/bin/bash

# 物理竞赛题库系统启动脚本

echo "========================================="
echo "  物理竞赛题库系统 - 启动脚本"
echo "========================================="

# 进入项目目录
cd /home/redaunt/physics

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装后端依赖
echo "安装后端依赖..."
pip install -r backend/requirements.txt -q

# 初始化数据库和默认数据
echo "初始化数据库..."
cd backend
python init_data.py
cd ..

# 启动后端服务
echo "启动后端服务..."
cd backend
source ../venv/bin/activate
python -m app &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 启动前端开发服务器
echo "启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  服务启动完成！"
echo "========================================="
echo ""
echo "  后端API: http://localhost:5000"
echo "  前端页面: http://localhost:3000"
echo ""
echo "  默认账号:"
echo "    管理员: admin / admin123"
echo "    教师: teacher / teacher123"
echo "    学生: student / student123"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================="

# 等待子进程
wait $BACKEND_PID $FRONTEND_PID
