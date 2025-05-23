# --- Builder Stage ---
FROM node:22-alpine AS builder

# Copy application files
COPY . /app

# Enable pnpm
RUN corepack enable pnpm

# Install and build frontend
WORKDIR /app/frontend
RUN pnpm install
RUN pnpm install dayjs # 漏了一个依赖
RUN pnpm build

# --- Python Dependencies Stage ---
FROM alpine AS python-deps

# Install Python, build dependencies and pre-compiled packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    g++ \
    musl-dev \
    python3-dev \
    linux-headers \
    make \
    py3-numpy \
    py3-scipy \
    py3-pandas \
    py3-cryptography \
    py3-lxml \
    py3-pillow

# Copy requirements file
COPY backend/requirements.txt /requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /requirements.txt --break-system-packages

# --- Final Stage ---
FROM alpine

# Environment variables
ENV HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    WS_PORT=8765 \
    FRONTEND_PORT=3000 \
    TZ=Asia/Shanghai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python and required packages (no build tools)
RUN apk add --no-cache python3 py3-pip caddy bash

# Copy necessary files from builder stage
COPY --from=builder /app /app

# Copy Python packages from python-deps stage
COPY --from=python-deps /usr/lib/python3.11/site-packages /usr/lib/python3.11/site-packages

# 显式复制启动脚本并设置权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 80

# Startup command
ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
