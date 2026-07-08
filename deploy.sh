#!/bin/bash

# 物理题库系统部署脚本 (macOS / Linux)

set -e  # 遇到错误立即退出

echo -e "\033[32m=== 开始构建物理题库系统 ===\033[0m"

# 检查 Docker
echo -e "\033[36m[检查] 检查 Docker 环境...\033[0m"
if ! command -v docker &> /dev/null; then
    echo -e "\033[31m错误：Docker 未安装\033[0m"
    echo -e "\033[33m请安装 Docker: https://docs.docker.com/get-docker/\033[0m"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "\033[31m错误：Docker 服务未启动\033[0m"
    echo -e "\033[33m请启动 Docker Desktop 或 Docker 服务\033[0m"
    exit 1
fi

echo -e "\033[32mDocker 已安装: $(docker --version)\033[0m"

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "\033[31m错误：docker-compose 未安装\033[0m"
    echo -e "\033[33m请安装 Docker Compose: https://docs.docker.com/compose/install/\033[0m"
    exit 1
fi

# 1. 构建前端
echo -e "\033[36m[1/4] 构建前端...\033[0m"
cd frontend

if ! npm install; then
    echo -e "\033[31m错误：npm install 失败\033[0m"
    cd ..
    exit 1
fi

if ! npm run build; then
    echo -e "\033[31m错误：npm run build 失败\033[0m"
    cd ..
    exit 1
fi

cd ..
echo -e "\033[32m前端构建完成\033[0m"

# 2. 构建 Docker 镜像
echo -e "\033[36m[2/4] 构建 Docker 镜像...\033[0m"
if ! docker-compose build; then
    echo -e "\033[31m错误：Docker 镜像构建失败\033[0m"
    exit 1
fi
echo -e "\033[32mDocker 镜像构建完成\033[0m"

# 3. 启动服务
echo -e "\033[36m[3/4] 启动服务...\033[0m"
if ! docker-compose up -d; then
    echo -e "\033[31m错误：启动服务失败\033[0m"
    exit 1
fi
echo -e "\033[32m服务启动完成\033[0m"

# 4. 初始化数据库
echo -e "\033[36m[4/4] 初始化数据库...\033[0m"
sleep 5

if docker-compose exec -T backend python -c "
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表创建成功')
"; then
    echo -e "\033[32m数据库初始化完成\033[0m"
else
    echo -e "\033[33m警告：数据库初始化可能失败，请手动检查\033[0m"
fi

echo ""
echo -e "\033[32m=== 部署完成 ===\033[0m"
echo -e "\033[36m访问地址: http://localhost\033[0m"
echo -e "\033[36mAPI 地址: http://localhost/api\033[0m"
echo ""
echo -e "\033[33m常用命令:\033[0m"
echo -e "  查看日志: docker-compose logs -f"
echo -e "  停止服务: docker-compose down"
echo -e "  重启服务: docker-compose restart"
echo ""
echo -e "\033[33m默认账号:\033[0m"
echo -e "  管理员: admin / admin1906"
echo -e "  教师和学生账号由管理员在系统内创建"
#!/bin/bash

# 物理题库系统部署脚本 (macOS / Linux)

set -e  # 遇到错误立即退出

echo -e "\033[32m=== 开始构建物理题库系统 ===\033[0m"

# 检查 Docker
echo -e "\033[36m[检查] 检查 Docker 环境...\033[0m"
if ! command -v docker &> /dev/null; then
    echo -e "\033[31m错误：Docker 未安装\033[0m"
    echo -e "\033[33m请安装 Docker: https://docs.docker.com/get-docker/\033[0m"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "\033[31m错误：Docker 服务未启动\033[0m"
    echo -e "\033[33m请启动 Docker Desktop 或 Docker 服务\033[0m"
    exit 1
fi

echo -e "\033[32mDocker 已安装: $(docker --version)\033[0m"

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "\033[31m错误：docker-compose 未安装\033[0m"
    echo -e "\033[33m请安装 Docker Compose: https://docs.docker.com/compose/install/\033[0m"
    exit 1
fi

# 1. 构建前端
echo -e "\033[36m[1/4] 构建前端...\033[0m"
cd frontend

if ! npm install; then
    echo -e "\033[31m错误：npm install 失败\033[0m"
    cd ..
    exit 1
fi

if ! npm run build; then
    echo -e "\033[31m错误：npm run build 失败\033[0m"
    cd ..
    exit 1
fi

cd ..
echo -e "\033[32m前端构建完成\033[0m"

# 2. 构建 Docker 镜像
echo -e "\033[36m[2/4] 构建 Docker 镜像...\033[0m"
if ! docker-compose build; then
    echo -e "\033[31m错误：Docker 镜像构建失败\033[0m"
    exit 1
fi
echo -e "\033[32mDocker 镜像构建完成\033[0m"

# 3. 启动服务
echo -e "\033[36m[3/4] 启动服务...\033[0m"
if ! docker-compose up -d; then
    echo -e "\033[31m错误：启动服务失败\033[0m"
    exit 1
fi
echo -e "\033[32m服务启动完成\033[0m"

# 4. 初始化数据库
echo -e "\033[36m[4/4] 初始化数据库...\033[0m"
sleep 5

if docker-compose exec -T backend python -c "
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表创建成功')
"; then
    echo -e "\033[32m数据库初始化完成\033[0m"
else
    echo -e "\033[33m警告：数据库初始化可能失败，请手动检查\033[0m"
fi

echo ""
echo -e "\033[32m=== 部署完成 ===\033[0m"
echo -e "\033[36m访问地址: http://localhost\033[0m"
echo -e "\033[36mAPI 地址: http://localhost/api\033[0m"
echo ""
echo -e "\033[33m常用命令:\033[0m"
echo -e "  查看日志: docker-compose logs -f"
echo -e "  停止服务: docker-compose down"
echo -e "  重启服务: docker-compose restart"
echo ""
echo -e "\033[33m默认账号:\033[0m"
echo -e "  管理员: admin / admin1906"
echo -e "  教师和学生账号由管理员在系统内创建"