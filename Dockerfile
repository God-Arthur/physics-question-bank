# 使用 Python 3.11 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    gcc \
    g++ \
    libpq-dev \
    # LaTeX 相关（最小化安装）
    texlive-latex-base \
    texlive-xetex \
    texlive-lang-chinese \
    fonts-noto-cjk \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# 创建上传目录
RUN mkdir -p app/static/uploads app/static/papers

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "run.py"]
