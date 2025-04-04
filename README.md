# 🔥 FireMail - 花火邮箱助手

🌟 一款专为Microsoft邮箱设计的批量收件工具，提供简单高效的邮件管理解决方案。

[![GitHub](https://img.shields.io/github/license/fengyuanluo/FireMail)](https://github.com/fengyuanluo/FireMail)

## 📋 项目功能

- 📥 **批量导入邮箱**：支持"邮箱----密码----客户端ID----RefreshToken"的批量导入格式
- 📊 **邮箱管理**：批量操作多个邮箱账户
- 📬 **自动收信**：对导入的邮箱进行自动收信操作
- 👥 **多用户系统**：支持用户注册、登录，权限分级管理
- 🔐 **安全管理**：数据存储在本地SQLite数据库，确保安全性

## ✨ 项目特点

- 🚀 **批量管理**：支持多选、全选邮箱，进行批量删除、收信操作
- 🔄 **WebSocket实时通信**：及时反馈处理进度和结果
- 🧵 **多线程处理**：提高邮件收取效率，支持并行处理多个邮箱
- 🎨 **简洁界面**：简约现代的用户界面，操作简单直观
- 💻 **跨平台支持**：支持Windows和Linux平台
- 🔧 **Docker支持**：可打包为Docker容器快速部署

## 🛠️ 技术栈

- **后端**：Python 3.13, Flask, SQLite, WebSocket
- **前端**：Vue 3, Vite, Element Plus
- **其他**：OAuth 2.0, IMAP, Docker

## 🚀 部署教程

### 🐳 Docker部署

```bash
# 拉取镜像
docker pull luofengyuan/huohuo-email-assistant:latest

# 运行容器
docker run -d \
  --name firemail \
  -p 80:80 \
  -v ./data:/app/backend/data \
  --restart unless-stopped \
  luofengyuan/huohuo-email-assistant:latest
```

### 🐙 Docker-Compose部署

1. 创建`docker-compose.yml`文件：

```yaml
version: '3'

services:
  huohuo-email-assistant:
    image: luofengyuan/huohuo-email-assistant:latest
    container_name: firemail
    restart: unless-stopped
    ports:
      - "80:80"  # 只暴露一个端口，通过Nginx进行反向代理
    volumes:
      - ./backend/data:/app/backend/data
    environment:
      - TZ=Asia/Shanghai
      - HOST=0.0.0.0
      - FLASK_PORT=5000  # 后端服务器端口
      - WS_PORT=8765     # WebSocket服务器端口
      - JWT_SECRET_KEY=your_secret_key_here  # 建议修改为随机字符串
```

2. 启动服务：

```bash
docker-compose up -d
```

### 📦 源代码部署

1. 克隆仓库：
```bash
git clone https://github.com/fengyuanluo/FireMail.git
cd FireMail
```

2. 安装后端依赖：
```bash
pip install -r requirements.txt
```

3. 安装前端依赖并构建：
```bash
cd frontend
npm install
npm run build
```

4. 启动后端服务：
```bash
cd ../backend
python app.py
```

5. 在浏览器中访问 `http://localhost:3000`

## 📝 使用说明

1. **导入邮箱**：在"批量导入"页面，按照"邮箱----密码----客户端ID----RefreshToken"格式导入邮箱
2. **管理邮箱**：在"邮箱管理"页面查看所有导入的邮箱，进行单个或批量操作
3. **收取邮件**：点击"收信"按钮开始收取邮件，实时查看进度
4. **查看邮件**：点击邮箱可以查看已收取的所有邮件内容

## 👤 用户认证

- 🔐 系统默认开启注册功能
- 👑 第一个注册的用户自动成为管理员
- 🔒 管理员可以开启或关闭注册功能
- 👥 管理员可以手动添加、删除用户和重置用户密码

## 🔮 未来开发计划

- 📧 **支持更多邮箱类型**：
  - Gmail
  - Yahoo
  - 163邮箱
  - QQ邮箱
  - 其他主流邮箱服务

- 🏗️ **优化Docker镜像**：
  - 使用Alpine Linux作为基础镜像，大幅减小镜像体积
  - 进一步优化构建流程，提高镜像构建效率

- 🔍 **更多功能**：
  - 邮件内容搜索
  - 邮件分类与标签
  - 自动回复功能

## 📄 开源协议

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 许可证进行开源。

## ⚠️ 免责声明

1. 本工具仅用于方便用户管理自己的邮箱账户，请勿用于非法用途。
2. 使用本工具过程中产生的任何数据安全问题、账户安全问题或违反相关服务条款的行为，均由用户自行承担责任。
3. 开发者不对使用本工具过程中可能出现的任何损失或风险负责。
4. 本工具与Microsoft等邮箱服务提供商没有任何官方关联，使用时请遵守相关服务条款。
5. 邮箱账号和密码等敏感信息仅存储在本地SQLite数据库中，请确保服务器安全，防止数据泄露。

## 🔗 相关链接

- 项目地址：[https://github.com/fengyuanluo/FireMail](https://github.com/fengyuanluo/FireMail)
- 问题反馈：请在项目的Issues页面提交

---

💖 如果您喜欢这个项目，请给它一个Star！ 