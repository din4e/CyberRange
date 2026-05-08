<#
.SYNOPSIS
    WebShell 测试环境 - 启动所有服务
.EXAMPLE
    .\start.ps1              # 启动全部
    .\start.ps1 -Only php,jdk8  # 只启动 PHP 和 JDK8
#>
param(
    [string[]]$Only  # 指定服务: php, jdk8, jdk9, jdk11
)

$Base = $PSScriptRoot
$RT = Join-Path $Base "runtime"
$WS = Resolve-Path (Join-Path $Base "..\webshell")
$HtmlDir = Resolve-Path (Join-Path $Base "..\html")
$Ports = @{ php = 20010; jdk8 = 20011; jdk9 = 20012; jdk11 = 20013 }
$script:Pids = @{}

function Find-Dir($Name) {
    $d = Join-Path $RT $Name
    if (!(Test-Path $d)) { return $null }
    $dirs = Get-ChildItem $d -Directory
    if ($dirs.Count -eq 1) { return $dirs[0].FullName }
    return $d
}

function Ensure-PhpDocroot {
    $docRoot = Join-Path $RT "php-docroot"
    if (Test-Path $docRoot) { return $docRoot }
    New-Item -ItemType Directory -Force -Path $docRoot | Out-Null
    # 复制 html 内容
    Copy-Item (Join-Path $HtmlDir "*") $docRoot -Recurse -Force
    # 复制 webshell 目录内容
    $wsDest = Join-Path $docRoot "webshell"
    New-Item -ItemType Directory -Force -Path $wsDest | Out-Null
    Copy-Item (Join-Path $WS "*") $wsDest -Recurse -Force
    return $docRoot
}

function Start-Php {
    $phpDir = Find-Dir "php"
    if (!$phpDir) { Write-Host "  [php] not installed, run setup.ps1" -f Red; return }
    $php = Join-Path $phpDir "php.exe"
    if (!(Test-Path $php)) { Write-Host "  [php] php.exe not found" -f Red; return }

    $port = $Ports.php
    $docRoot = Ensure-PhpDocroot
    Write-Host "  [php]  :$port ..." -f Cyan -NoNewline
    $proc = Start-Process -FilePath $php -ArgumentList "-S","0.0.0.0:$port","-t",$docRoot `
        -WindowStyle Hidden -PassThru
    $script:Pids["php"] = $proc.Id
    Write-Host " OK (PID $($proc.Id))" -f Green
}

function Start-TomcatInstance($Label) {
    $tcDir = Join-Path $RT "tomcat-$Label"
    if (!(Test-Path $tcDir)) {
        Write-Host "  [tomcat-$Label] not installed" -f DarkGray
        return
    }
    $port = $Ports[$Label]
    Write-Host "  [$Label] :$port ..." -f Cyan -NoNewline

    $env:CATALINA_HOME = $tcDir
    $env:CATALINA_BASE = $tcDir
    # 读取 setenv.bat 中配置的 JAVA_HOME
    $setenv = Join-Path $tcDir "bin\setenv.bat"
    if (Test-Path $setenv) {
        $content = Get-Content $setenv -Raw
        if ($content -match 'JAVA_HOME=(.+?)"') {
            $env:JAVA_HOME = $Matches[1]
        }
    }

    $proc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c","`"$tcDir\bin\catalina.bat`" run" `
        -WindowStyle Hidden -PassThru
    $script:Pids["tomcat-$Label"] = $proc.Id
    Write-Host " OK (PID $($proc.Id))" -f Green
}

# ── 主流程 ─────────────────────────────────────────────────────
Write-Host "`n=== Starting WebShell Test Services ===`n" -f Yellow

$services = if ($Only) { $Only -split "," | ForEach-Object { $_.Trim() } } else { @("php","jdk8","jdk9","jdk11") }

if ("php" -in $services)   { Start-Php }
if ("jdk8" -in $services)  { Start-TomcatInstance "jdk8" }
if ("jdk9" -in $services)  { Start-TomcatInstance "jdk9" }
if ("jdk11" -in $services) { Start-TomcatInstance "jdk11" }

# 等待端口就绪
Write-Host "`nWaiting for services ..." -f White -NoNewline
Start-Sleep -Seconds 5

foreach ($svc in $services) {
    $port = $Ports[$svc]
    $ready = $false
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
        $tcp.Close(); $ready = $true
    } catch {}
    $tag = if ($svc -eq "php") { "php" } else { $svc }
    if ($ready) { Write-Host "`n  [$tag] :$port READY" -f Green -NoNewline }
    else { Write-Host "`n  [$tag] :$port STARTING..." -f DarkYellow -NoNewline }
}

# 保存 PID
$pidFile = Join-Path $RT ".pids.json"
$script:Pids | ConvertTo-Json | Set-Content $pidFile

# 输出访问地址
Write-Host "`n`n=== Access URLs (Native) ===`n" -f Yellow
if ("php" -in $services) {
    Write-Host "  PHP (Native)    http://localhost:20010/"
    Write-Host "    WebShell      http://localhost:20010/webshell/"
}
if ("jdk8" -in $services) {
    Write-Host "  Tomcat JDK 8    http://localhost:20011/"
    Write-Host "    WebShell      http://localhost:20011/webshell/"
}
if ("jdk9" -in $services) {
    Write-Host "  Tomcat JDK 9    http://localhost:20012/"
    Write-Host "    WebShell      http://localhost:20012/webshell/"
}
if ("jdk11" -in $services) {
    Write-Host "  Tomcat JDK 11   http://localhost:20013/"
    Write-Host "    WebShell      http://localhost:20013/webshell/"
}
Write-Host "`nDocker ports: 20000-20003 | Native ports: 20010-20013"
Write-Host "Run '.\stop.ps1' to stop all services.`n" -f DarkGray
