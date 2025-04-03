FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装Node.js、git和基础依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 构建前端
WORKDIR /app/frontend
RUN npm ci && \
    npm run build && \
    npm install -g serve && \
    rm -rf node_modules

# 回到主工作目录
WORKDIR /app

# 添加启动脚本并设置权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 指定默认环境变量
ENV HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    WS_PORT=8765 \
    JWT_SECRET_KEY=huohuo_email_secret_key \
    ALLOW_REGISTER=false

# 暴露端口
EXPOSE 5000 8765 3000

# 启动命令
ENTRYPOINT ["/app/docker-entrypoint.sh"] 