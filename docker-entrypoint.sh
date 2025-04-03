#!/bin/bash
set -e

# 创建必要的数据目录
mkdir -p /app/backend/data

# 检查数据权限
chown -R nobody:nogroup /app/backend/data 2>/dev/null || true

# 设置环境变量
export HOST="${HOST:-0.0.0.0}"
export FLASK_PORT="${FLASK_PORT:-5000}"
export WS_PORT="${WS_PORT:-8765}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-huohuo_email_secret_key}"
export ALLOW_REGISTER="${ALLOW_REGISTER:-false}"
export TZ="${TZ:-Asia/Shanghai}"

echo "花火邮箱助手正在启动..."
echo "后端API地址: http://$HOST:$FLASK_PORT"
echo "WebSocket服务地址: ws://$HOST:$WS_PORT"
echo "前端服务地址: http://$HOST:$FRONTEND_PORT"

# 启动前端静态文件服务器
cd /app/frontend
echo "启动前端服务..."
npx serve -s dist -l $FRONTEND_PORT &

# 启动Python后端应用
cd /app
echo "启动后端服务..."
exec python3 ./backend/app.py --host "$HOST" --port "$FLASK_PORT" --ws-port "$WS_PORT" 