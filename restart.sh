#!/bin/bash
# 重启花火邮箱助手服务

echo "正在重启花火邮箱助手服务..."

# 停止现有容器
docker-compose down

# 重新构建并启动容器
docker-compose up -d

echo "服务已重启，请稍等片刻然后尝试访问"
echo "注册功能应该现在可以正常工作了" 