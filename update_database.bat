@echo off
echo 正在更新花火邮箱助手数据库结构...
cd %~dp0\backend
python update_db.py
pause 