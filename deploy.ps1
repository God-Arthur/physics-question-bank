# 物理题库系统部署脚本 (Windows PowerShell)

Write-Host "=== 开始构建物理题库系统 ===" -ForegroundColor Green

# 检查 PowerShell 版本
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "错误：需要 PowerShell 5.0 或更高版本" -ForegroundColor Red
    exit 1
}

# 检查 Docker
Write-Host "[检查] 检查 Docker 环境..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "Docker 已安装: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "错误：Docker 未安装或未添加到 PATH" -ForegroundColor Red
    Write-Host "请安装 Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# 检查 Docker 是否运行
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker 未运行"
    }
} catch {
    Write-Host "错误：Docker 服务未启动" -ForegroundColor Red
    Write-Host "请启动 Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# 1. 构建前端
Write-Host "[1/4] 构建前端..." -ForegroundColor Cyan
Set-Location frontend

try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
    
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build 失败" }
} catch {
    Write-Host "错误：前端构建失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Set-Location ..
    exit 1
}

Set-Location ..
Write-Host "前端构建完成" -ForegroundColor Green

# 2. 构建 Docker 镜像
Write-Host "[2/4] 构建 Docker 镜像..." -ForegroundColor Cyan
try {
    docker-compose build
    if ($LASTEXITCODE -ne 0) { throw "docker-compose build 失败" }
} catch {
    Write-Host "错误：Docker 镜像构建失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host "Docker 镜像构建完成" -ForegroundColor Green

# 3. 启动服务
Write-Host "[3/4] 启动服务..." -ForegroundColor Cyan
try {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) { throw "docker-compose up 失败" }
} catch {
    Write-Host "错误：启动服务失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host "服务启动完成" -ForegroundColor Green

# 4. 初始化数据库
Write-Host "[4/4] 初始化数据库..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

try {
    $initScript = @"
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表创建成功')
"@
    
    $initScript | docker-compose exec -T backend python -
    if ($LASTEXITCODE -ne 0) { throw "数据库初始化失败" }
} catch {
    Write-Host "警告：数据库初始化可能失败，请手动检查" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Green
Write-Host "访问地址: http://localhost" -ForegroundColor Cyan
Write-Host "API 地址: http://localhost/api" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Yellow
Write-Host "  查看日志: docker-compose logs -f" -ForegroundColor White
Write-Host "  停止服务: docker-compose down" -ForegroundColor White
Write-Host "  重启服务: docker-compose restart" -ForegroundColor White
Write-Host ""
Write-Host "默认账号:" -ForegroundColor Yellow
Write-Host "  管理员: admin / admin1906" -ForegroundColor White
Write-Host "  教师和学生账号由管理员在系统内创建" -ForegroundColor White
# 物理题库系统部署脚本 (Windows PowerShell)

Write-Host "=== 开始构建物理题库系统 ===" -ForegroundColor Green

# 检查 PowerShell 版本
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "错误：需要 PowerShell 5.0 或更高版本" -ForegroundColor Red
    exit 1
}

# 检查 Docker
Write-Host "[检查] 检查 Docker 环境..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "Docker 已安装: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "错误：Docker 未安装或未添加到 PATH" -ForegroundColor Red
    Write-Host "请安装 Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# 检查 Docker 是否运行
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker 未运行"
    }
} catch {
    Write-Host "错误：Docker 服务未启动" -ForegroundColor Red
    Write-Host "请启动 Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# 1. 构建前端
Write-Host "[1/4] 构建前端..." -ForegroundColor Cyan
Set-Location frontend

try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
    
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build 失败" }
} catch {
    Write-Host "错误：前端构建失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Set-Location ..
    exit 1
}

Set-Location ..
Write-Host "前端构建完成" -ForegroundColor Green

# 2. 构建 Docker 镜像
Write-Host "[2/4] 构建 Docker 镜像..." -ForegroundColor Cyan
try {
    docker-compose build
    if ($LASTEXITCODE -ne 0) { throw "docker-compose build 失败" }
} catch {
    Write-Host "错误：Docker 镜像构建失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host "Docker 镜像构建完成" -ForegroundColor Green

# 3. 启动服务
Write-Host "[3/4] 启动服务..." -ForegroundColor Cyan
try {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) { throw "docker-compose up 失败" }
} catch {
    Write-Host "错误：启动服务失败" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host "服务启动完成" -ForegroundColor Green

# 4. 初始化数据库
Write-Host "[4/4] 初始化数据库..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

try {
    $initScript = @"
from app import create_app
from app.utils.database import db
app = create_app()
with app.app_context():
    db.create_all()
    print('数据库表创建成功')
"@
    
    $initScript | docker-compose exec -T backend python -
    if ($LASTEXITCODE -ne 0) { throw "数据库初始化失败" }
} catch {
    Write-Host "警告：数据库初始化可能失败，请手动检查" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Green
Write-Host "访问地址: http://localhost" -ForegroundColor Cyan
Write-Host "API 地址: http://localhost/api" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Yellow
Write-Host "  查看日志: docker-compose logs -f" -ForegroundColor White
Write-Host "  停止服务: docker-compose down" -ForegroundColor White
Write-Host "  重启服务: docker-compose restart" -ForegroundColor White
Write-Host ""
Write-Host "默认账号:" -ForegroundColor Yellow
Write-Host "  管理员: admin / admin1906" -ForegroundColor White
Write-Host "  教师和学生账号由管理员在系统内创建" -ForegroundColor White
