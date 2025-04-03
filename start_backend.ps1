Write-Host "正在启动花火邮箱助手后端服务..." -ForegroundColor Green
Set-Location -Path "$PSScriptRoot\backend"
python app.py 