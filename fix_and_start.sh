#!/bin/bash

# 修复并启动脚本
cd "$(dirname "$0")"

echo "========================================="
echo "  物理竞赛题库系统 - 修复并启动"
echo "========================================="

# 检查并安装pip
if ! command -v pip3 &> /dev/null; then
    echo "安装pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# 检查并安装虚拟环境
if ! python3 -m venv --help &> /dev/null; then
    echo "安装python3-venv..."
    sudo apt-get install -y python3-venv
fi

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 验证虚拟环境
echo "Python路径: $(which python3)"

# 安装后端依赖
echo "安装后端依赖..."
venv/bin/pip install -r backend/requirements.txt

# 初始化数据库
echo "初始化数据库..."
cd backend
../venv/bin/python init_data.py
cd ..

# 启动后端
echo "启动后端服务..."
cd backend
../venv/bin/python run.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "等待后端启动..."
sleep 5

# 检查后端是否启动成功
if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo "后端服务启动成功！"
else
    echo "后端服务可能未启动，请检查日志"
fi

# 安装前端依赖
echo "安装前端依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi

# 启动前端
echo "启动前端服务..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  服务启动完成！"
echo "========================================="
echo ""
echo "  前端页面: http://localhost:3000 (或3001)"
echo "  后端API: http://localhost:5000"
echo ""
echo "  默认账号:"
echo "    管理员: admin / admin1906"
echo "    教师和学生账号由管理员在系统内创建"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "========================================="

wait $BACKEND_PID $FRONTEND_PID
