# 花火邮箱助手

花火邮箱助手是一款专为Microsoft邮箱设计的批量收件工具，提供简单高效的邮件管理解决方案。

## 功能特点

- **批量导入**：支持"邮箱----密码----客户端ID----RefreshToken"的批量导入格式，一行一个
- **批量管理**：允许多选、全选邮箱，进行批量删除、收信，允许单个邮箱手动收信
- **WebSocket支持**：实时通信，及时反馈处理进度和结果
- **多线程处理**：提高邮件收取效率，支持并行处理多个邮箱
- **简洁界面**：简约现代的用户界面，操作简单直观
- **跨平台支持**：支持Windows和Linux平台，可打包为Docker容器部署

## 技术栈

- **后端**：Python 3.13, Flask, SQLite, WebSocket
- **前端**：Vue 3, Vite, Element Plus
- **其他**：OAuth 2.0, IMAP

## 安装与使用

### 方法一：本地运行

1. 克隆项目
   ```bash
   git clone https://github.com/yourusername/huohuo-email-assistant.git
   cd huohuo-email-assistant
   ```

2. 后端安装与运行
   ```bash
   pip install -r requirements.txt
   python backend/app.py
   ```

3. 前端安装与运行
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. 在浏览器中访问 http://localhost:5173

### 方法二：Docker部署

1. 使用Docker Compose
   ```bash
   docker-compose up -d
   ```

2. 在浏览器中访问 http://localhost:5000

## 使用说明

1. **导入邮箱**：在"批量导入"页面，按照"邮箱----密码----客户端ID----RefreshToken"格式导入邮箱
2. **管理邮箱**：在"邮箱管理"页面查看所有导入的邮箱，进行单个或批量操作
3. **收取邮件**：点击"收信"按钮开始收取邮件，实时查看进度
4. **查看邮件**：点击邮箱可以查看已收取的所有邮件内容

## 获取Microsoft RefreshToken

1. 登录Microsoft Azure门户
2. 注册应用并获取客户端ID
3. 设置API权限和回调URL
4. 使用OAuth流程获取初始RefreshToken

详细说明可参考：[Microsoft OAuth 2.0 授权代码流](https://learn.microsoft.com/zh-cn/azure/active-directory/develop/v2-oauth2-auth-code-flow)

## 注意事项

- 本工具仅用于方便用户管理自己的邮箱账户，请勿用于非法用途
- 邮箱账号和密码等敏感信息仅存储在本地SQLite数据库中，请确保服务器安全
- 由于Microsoft API限制，可能会有请求频率限制，请合理使用

## 许可证

MIT License

## 用户认证功能

项目已添加用户认证功能，包括以下特性：

- 用户注册和登录
- 用户密码管理
- 用户权限控制（管理员和普通用户）
- 访问控制和路由保护

### 默认管理员账户

首次启动后，系统会创建一个默认的管理员账户：

- 用户名：admin
- 密码：admin123

**注意：** 出于安全考虑，建议在首次登录后修改默认管理员密码。

## 运行应用

### 首次运行或更新后

如果您是首次运行，或者从旧版本升级，请先执行以下步骤更新数据库结构：

#### Windows命令提示符（CMD）
```
update_database.bat
```

#### Windows PowerShell
```powershell
.\update_database.ps1
```

#### 手动更新
```bash
cd huohuo-email-assistant/backend
python update_db.py
```

### 方式一：使用批处理脚本

#### Windows命令提示符（CMD）
项目根目录提供了两个批处理脚本，方便在Windows环境下启动应用：

1. 启动后端服务：
   - 双击运行 `start_backend.bat`

2. 启动前端服务：
   - 双击运行 `start_frontend.bat`

#### Windows PowerShell
PowerShell用户可以使用以下脚本：

1. 启动后端服务：
   ```powershell
   .\start_backend.ps1
   ```

2. 启动前端服务：
   ```powershell
   .\start_frontend.ps1
   ```

### 方式二：命令行启动

#### 启动后端

```bash
# 进入后端目录
cd huohuo-email-assistant/backend

# 启动后端服务
python app.py
```

#### 启动前端

```bash
# 进入前端目录
cd huohuo-email-assistant/frontend

# 安装依赖（如果尚未安装）
npm install

# 启动开发服务器
npm run dev
```

## 访问应用

启动前后端服务后，可通过以下地址访问应用：

- 前端界面：http://localhost:5173
- 后端API：http://localhost:5000/api

## 技术细节

### WebSocket认证

WebSocket连接现在需要用户认证才能建立。用户登录后，系统会自动连接WebSocket并进行认证。

### API认证

所有API请求都需要认证令牌（除了登录和注册端点）。认证采用JWT令牌，在HTTP请求头的Authorization字段中传递。 