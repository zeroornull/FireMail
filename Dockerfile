FROM python:3.12-slim

# 设置工作目录和环境变量
WORKDIR /app
ENV HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    WS_PORT=8765 \
    FRONTEND_PORT=3000 \
    TZ=Asia/Shanghai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JWT_SECRET_KEY=huohuo_email_secret_key

# 安装Node.js、Nginx和基础依赖（合并层）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    nginx \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm serve \
    # 创建数据目录
    && mkdir -p /app/backend/data \
    && chown -R www-data:www-data /app/backend/data

# 先复制依赖相关文件并安装依赖
COPY requirements.txt /app/
COPY frontend/package.json frontend/package-lock.json /app/frontend/
RUN pip install --no-cache-dir -r requirements.txt \
    && cd /app/frontend \
    && npm ci

# 复制前端源代码并构建
WORKDIR /app/frontend
COPY frontend/src /app/frontend/src/
COPY frontend/index.html frontend/vite.config.js /app/frontend/
RUN npm run build && rm -rf node_modules

# 复制后端文件和启动脚本
WORKDIR /app
COPY backend /app/backend/
COPY docker-entrypoint.sh /app/
COPY nginx.conf /etc/nginx/nginx.conf
RUN chmod +x /app/docker-entrypoint.sh \
    && chown -R www-data:www-data /app/frontend/dist

# 暴露端口
EXPOSE 80

# 启动命令
ENTRYPOINT ["/app/docker-entrypoint.sh"]