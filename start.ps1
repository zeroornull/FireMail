# 启动后端服务器
$backendProcess = Start-Process -FilePath "python" -ArgumentList "app.py" -WorkingDirectory "backend" -PassThru -NoNewWindow

Write-Host "后端服务器已启动，PID: $($backendProcess.Id)"
Write-Host "按Ctrl+C停止服务器..."

try {
    # 保持脚本运行
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    # 当用户按下Ctrl+C时，停止后端进程
    if (-not $backendProcess.HasExited) {
        Write-Host "正在停止后端服务器..."
        Stop-Process -Id $backendProcess.Id -Force
        Write-Host "后端服务器已停止"
    }
} 