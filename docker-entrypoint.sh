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
echo "注册功能状态: ${ALLOW_REGISTER}"

# 创建前端环境变量文件
mkdir -p /app/frontend/dist
cat > /app/frontend/dist/env-config.js << EOF
// 环境配置
window.API_URL = '${API_URL:-/api}';
window.WS_URL = '${WS_URL:-/ws}';
console.log('env-config.js已加载，API_URL:', window.API_URL, 'WS_URL:', window.WS_URL);
EOF

echo "已创建环境配置文件，内容如下:"
cat /app/frontend/dist/env-config.js

# 创建Nginx配置文件用于反向代理
mkdir -p /tmp/nginx
cat > /tmp/nginx/serve.json << EOF
{
  "rewrites": [
    { "source": "/api/**", "destination": "http://$HOST:$FLASK_PORT/api/:splat" },
    { "source": "/ws", "destination": "ws://$HOST:$WS_PORT" }
  ],
  "headers": [
    {
      "source": "**",
      "headers": [
        { "key": "Cache-Control", "value": "no-cache, no-store, must-revalidate" },
        { "key": "Pragma", "value": "no-cache" },
        { "key": "Expires", "value": "0" }
      ]
    }
  ]
}
EOF

echo "已创建反向代理配置，内容如下:"
cat /tmp/nginx/serve.json

# 启动前端静态文件服务器
cd /app/frontend
echo "启动前端服务..."
npx serve -s dist -l "$FRONTEND_PORT" --config /tmp/nginx/serve.json &

echo "等待前端服务启动..."
sleep 2

# 启动Python后端应用
cd /app
echo "启动后端服务..."
exec python3 ./backend/app.py --host "$HOST" --port "$FLASK_PORT" --ws-port "$WS_PORT" 