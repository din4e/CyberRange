<#
.SYNOPSIS
    WebShell 测试环境 - 停止所有服务
#>
$Base = $PSScriptRoot
$RT = Join-Path $Base "runtime"
$pidFile = Join-Path $RT ".pids.json"

Write-Host "`n=== Stopping WebShell Test Services ===`n" -f Yellow

# 方式1: 通过保存的 PID 停止
if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    foreach ($prop in $pids.PSObject.Properties) {
        $name = $prop.Name
        $id = $prop.Value
        Write-Host "  Stopping $name (PID $id) ..." -f Cyan -NoNewline
        try {
            $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($proc) {
                # Tomcat 启动的 java 子进程也需要停止
                Get-CimInstance Win32_Process -Filter "ParentProcessId=$id" | ForEach-Object {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                }
                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            }
            Write-Host " OK" -f Green
        } catch {
            Write-Host " not running" -f DarkGray
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 方式2: 兜底 - 通过端口查找进程
$Ports = @{ php = 20010; jdk11 = 20013; jdk8 = 20011; jdk9 = 20012 }
foreach ($entry in $Ports.GetEnumerator()) {
    $port = $entry.Value
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $procIds = $conn.OwningProcess | Select-Object -Unique
        foreach ($p in $procIds) {
            Write-Host "  Port $($port) → PID $p, killing ..." -f DarkYellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "`nAll services stopped.`n" -f Green
