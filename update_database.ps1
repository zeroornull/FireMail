Write-Host "正在更新花火邮箱助手数据库结构..." -ForegroundColor Green
Set-Location -Path "$PSScriptRoot\backend"
python update_db.py
Write-Host "按任意键继续..." -ForegroundColor Yellow
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null 