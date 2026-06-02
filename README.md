# 物理题库系统

基于 Vue 3 + Flask 的物理题库管理与试卷生成系统。

## 功能特性

- 📚 **题库管理**：支持理论题和实验理论题的增删改查
- 🔍 **智能搜索**：支持按关键词、题型、难度、学院筛选
- 📄 **组卷功能**：可视化选题，自动生成 PDF 试卷
- 👨‍🏫 **班级管理**：教师可创建班级，分配试卷
- 🔐 **权限控制**：支持管理员、教师、学生三种角色
- 📱 **响应式设计**：支持桌面和移动端访问

## 技术栈

- **前端**：Vue 3 + Element Plus + Vite
- **后端**：Flask + SQLAlchemy + PostgreSQL
- **PDF 生成**：XeLaTeX（支持中文和数学公式）
- **部署**：Docker + Docker Compose

## 快速开始

### 环境要求

- Docker Desktop（推荐）或 Docker Engine + Docker Compose
- Git

### 一键部署（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd physics-question-bank

# 运行部署脚本
# macOS / Linux:
chmod +x deploy.sh
./deploy.sh

# Windows (PowerShell):
.\deploy.ps1
```

访问 http://localhost 即可使用系统。

### 手动部署

#### 1. 构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

#### 2. 启动服务

```bash
docker-compose up -d
```

#### 3. 初始化数据库

```bash
docker-compose exec backend python -c "
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库初始化完成')
"
```

## 跨平台部署指南

### macOS

#### 要求
- macOS 10.15 或更高版本
- Docker Desktop for Mac
- 至少 4GB 可用内存

#### 安装步骤

1. **安装 Docker Desktop**
   ```bash
   # 使用 Homebrew 安装
   brew install --cask docker
   
   # 或从官网下载：https://www.docker.com/products/docker-desktop
   ```

2. **启动 Docker**
   - 打开 Docker Desktop 应用
   - 等待状态栏显示 "Docker Desktop is running"

3. **部署应用**
   ```bash
   git clone <repository-url>
   cd physics-question-bank
   ./deploy.sh
   ```

4. **访问应用**
   - 打开浏览器访问 http://localhost
   - 默认管理员账号：admin / admin123

#### 常见问题

**问题1：端口被占用**
```bash
# 检查端口占用
lsof -i :80
lsof -i :5000
lsof -i :5432

# 停止占用端口的进程或修改 docker-compose.yml 中的端口映射
```

**问题2：内存不足**
```bash
# 在 Docker Desktop 设置中增加内存限制
# Preferences -> Resources -> Memory -> 建议 4GB 以上
```

**问题3：文件权限**
```bash
# 修复文件权限
sudo chown -R $(whoami) .
chmod +x deploy.sh
```

### Windows

#### 要求
- Windows 10/11 (64位)
- WSL2（Windows Subsystem for Linux 2）
- Docker Desktop for Windows
- PowerShell 5.0 或更高版本

#### 安装步骤

1. **启用 WSL2**
   ```powershell
   # 以管理员身份运行 PowerShell
   wsl --install
   # 重启电脑
   ```

2. **安装 Docker Desktop**
   - 下载地址：https://www.docker.com/products/docker-desktop
   - 安装时勾选 "Use WSL 2 instead of Hyper-V"
   - 启动 Docker Desktop

3. **部署应用**
   ```powershell
   # 克隆项目
git clone <repository-url>
   cd physics-question-bank
   
   # 运行部署脚本
   .\deploy.ps1
   ```

4. **访问应用**
   - 打开浏览器访问 http://localhost
   - 默认管理员账号：admin / admin123

#### 常见问题

**问题1：WSL2 未启用**
```powershell
# 检查 WSL 状态
wsl --status

# 设置 WSL 默认版本为 2
wsl --set-default-version 2

# 更新 WSL
wsl --update
```

**问题2：PowerShell 执行策略**
```powershell
# 以管理员身份运行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 验证
Get-ExecutionPolicy
```

**问题3：端口被占用**
```powershell
# 检查端口占用
netstat -ano | findstr :80
netstat -ano | findstr :5000

# 停止占用端口的进程
# 或修改 docker-compose.yml 中的端口映射
```

**问题4：防火墙阻止**
```powershell
# 检查 Windows Defender 防火墙
# 设置 -> 更新和安全 -> Windows 安全中心 -> 防火墙和网络保护
# 允许 Docker Desktop 通过防火墙
```

### Linux

#### 要求
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Fedora 34+
- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存

#### 安装步骤（Ubuntu/Debian）

1. **安装 Docker**
   ```bash
   # 更新包索引
   sudo apt-get update
   
   # 安装依赖
   sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
   
   # 添加 Docker GPG 密钥
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   
   # 添加 Docker 仓库
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # 安装 Docker
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
   
   # 将当前用户添加到 docker 组
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **部署应用**
   ```bash
   git clone <repository-url>
   cd physics-question-bank
   ./deploy.sh
   ```

3. **访问应用**
   - 打开浏览器访问 http://localhost
   - 默认管理员账号：admin / admin123

#### 安装步骤（CentOS/RHEL/Fedora）

1. **安装 Docker**
   ```bash
   # CentOS/RHEL
   sudo yum install -y yum-utils
   sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
   
   # Fedora
   sudo dnf -y install dnf-plugins-core
   sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
   sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
   
   # 启动 Docker
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # 将当前用户添加到 docker 组
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **部署应用**
   ```bash
   git clone <repository-url>
   cd physics-question-bank
   ./deploy.sh
   ```

#### 常见问题

**问题1：Docker 服务未启动**
```bash
# 检查 Docker 状态
sudo systemctl status docker

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**问题2：权限不足**
```bash
# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 验证
docker ps
```

**问题3：端口被占用**
```bash
# 检查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5000

# 停止占用服务或修改端口
sudo systemctl stop apache2  # 如果安装了 Apache
sudo systemctl stop nginx    # 如果安装了 Nginx
```

## 开发环境搭建

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接

# 初始化数据库
python -c "
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
"

# 启动开发服务器
python run.py
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户浏览器                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (前端服务)                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  静态文件 (Vue 3 构建产物)                              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask 后端 API                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  题库管理    │  │  试卷生成    │  │  用户/班级管理       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  XeLaTeX (PDF 生成)                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 数据库                          │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
physics-question-bank/
├── frontend/                 # 前端代码
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 公共组件
│   │   ├── api/             # API 接口
│   │   └── stores/          # Pinia 状态管理
│   ├── public/              # 静态资源
│   └── package.json         # 依赖配置
├── backend/                  # 后端代码
│   ├── app/
│   │   ├── routes/          # API 路由
│   │   ├── models/          # 数据库模型
│   │   ├── utils/           # 工具函数
│   │   └── static/          # 静态文件
│   ├── requirements.txt     # Python 依赖
│   └── run.py               # 启动入口
├── Dockerfile               # Docker 构建文件
├── docker-compose.yml       # Docker Compose 配置
├── nginx.conf               # Nginx 配置
├── deploy.sh                # macOS/Linux 部署脚本
├── deploy.ps1               # Windows 部署脚本
└── README.md                # 项目说明
```

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理（包括数据卷）
docker-compose down -v

# 进入容器
docker-compose exec backend bash
docker-compose exec db psql -U postgres -d physics_db

# 备份数据库
docker-compose exec db pg_dump -U postgres physics_db > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U postgres -d physics_db < backup.sql
```

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 教师 | teacher | teacher123 |
| 学生 | student | student123 |

> ⚠️ 生产环境请务必修改默认密码！

## 许可证

MIT License

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 联系方式

如有问题或建议，请提交 Issue 或联系维护者。
