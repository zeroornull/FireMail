@echo off
echo 正在启动花火邮箱助手后端服务（已启用注册功能）...
cd %~dp0\backend
set ALLOW_REGISTER=true
echo 环境变量设置: ALLOW_REGISTER=%ALLOW_REGISTER%
python app.py
pause 