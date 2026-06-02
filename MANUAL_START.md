# 手动启动指南

由于 WSL 环境限制，请按以下步骤手动启动系统：

## 步骤 1: 安装必要依赖

在 WSL 终端中执行：

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3.12-venv
```

## 步骤 2: 创建虚拟环境并安装依赖

```bash
cd /home/redaunt/physics

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install flask flask-cors flask-jwt-extended sqlalchemy werkzeug reportlab pillow python-dotenv
```

## 步骤 3: 初始化数据库

```bash
cd backend
python init_data.py
cd ..
```

## 步骤 4: 启动后端服务

```bash
cd backend
python app/__init__.py
```

保持这个终端运行，打开新的终端继续...

## 步骤 5: 启动前端服务

```bash
cd /home/redaunt/physics/frontend
npm install
npm run dev
```

## 访问系统

- 前端页面: http://localhost:3000
- 后端API: http://localhost:5000

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 教师 | teacher | teacher123 |
| 学生 | student | student123 |

## 常见问题

### 端口被占用

```bash
# 查找占用 5000 端口的进程
lsof -i :5000

# 结束进程
kill -9 <PID>
```

### 前端端口被占用

Vite 会自动尝试其他端口（如 3001），查看终端输出获取实际端口。
