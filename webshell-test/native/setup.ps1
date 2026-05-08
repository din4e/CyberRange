<#
.SYNOPSIS
    WebShell 测试环境 - Windows 原生安装脚本
.DESCRIPTION
    下载并配置 PHP + Tomcat(JDK 8/11) 运行环境
    JDK 9 为可选 (非 LTS, 需手动下载 Oracle JDK 9 放入 downloads/jdk9.zip)
.NOTES
    首次运行需联网下载约 500MB, 后续运行自动跳过已下载/已解压的文件
#>
param([switch]$Force)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Base = $PSScriptRoot
$DL = Join-Path $Base "downloads"
$RT = Join-Path $Base "runtime"
$WS = Resolve-Path (Join-Path $Base "..\webshell")

# ── 下载地址 (可按需修改版本) ──────────────────────────────────
$TomcatVer = "9.0.117"
$Urls = @{
    PHP    = "https://windows.php.net/downloads/releases/php-8.2.31-nts-Win32-vs16-x64.zip"
    JDK8   = "https://api.adoptium.net/v3/binary/latest/8/ga/windows/x64/jdk/hotspot/normal/eclipse"
    JDK11  = "https://api.adoptium.net/v3/binary/latest/11/ga/windows/x64/jdk/hotspot/normal/eclipse"
    JDK9   = ""  # JDK 9 已 EOL, 无公开自动下载; 手动下载 Oracle JDK 9 zip 放入 downloads/jdk9.zip
    Tomcat = "https://archive.apache.org/dist/tomcat/tomcat-9/v$TomcatVer/bin/apache-tomcat-$TomcatVer.zip"
}

$Ports = @{ php = 20010; jdk8 = 20011; jdk9 = 20012; jdk11 = 20013 }

# ── 工具函数 ───────────────────────────────────────────────────
function Fetch($Url, $File) {
    $path = Join-Path $DL $File
    if ((Test-Path $path) -and !$Force) { Write-Host "  [skip] $File" -f DarkGray; return $path }
    # 清理上次不完整的下载
    if (Test-Path $path) { Remove-Item $path -Force }
    $tries = 0
    while ($tries -lt 3) {
        $tries++
        try {
            Write-Host "  download $File (attempt $tries) ..." -f Cyan -NoNewline
            Invoke-WebRequest $Url -OutFile $path -UseBasicParsing
            Write-Host " OK" -f Green
            return $path
        } catch {
            Write-Host " FAIL" -f Red
            if ($tries -lt 3) { Write-Host "    retrying in 3s ..." -f DarkYellow; Start-Sleep 3 }
            else { throw "Failed to download $File after 3 attempts: $_" }
        }
    }
}

function Unpack($Zip, $Label) {
    $dest = Join-Path $RT $Label
    if ((Test-Path $dest) -and !$Force) {
        Write-Host "  [skip] $Label" -f DarkGray
        return (Resolve-UnpackDir $dest)
    }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Write-Host "  extract $Label ..." -f Cyan -NoNewline
    Expand-Archive $Zip -DestinationPath $dest -Force
    Write-Host " OK" -f Green
    return (Resolve-UnpackDir $dest)
}

# 判断解压目录: 如果只有一个子目录则返回子目录, 否则返回自身 (如 PHP 平铺解压)
function Resolve-UnpackDir($Dest) {
    $dirs = Get-ChildItem $Dest -Directory
    if ($dirs.Count -eq 1) { return $dirs[0].FullName }
    return $Dest
}

function Make-Tomcat($TomcatSrc, $JdkDir, $Label, $Port) {
    $inst = Join-Path $RT "tomcat-$Label"
    if ((Test-Path $inst) -and !$Force) { Write-Host "  [skip] tomcat-$Label" -f DarkGray; return }

    Write-Host "  setup tomcat-$Label (port $Port) ..." -f Cyan -NoNewline
    Copy-Item -Recurse $TomcatSrc $inst -Force

    # 改端口: Shutdown (8005), HTTP (8080), AJP (8009)
    $xml = Join-Path $inst "conf\server.xml"
    $c = Get-Content $xml -Raw -Encoding UTF8
    $c = $c -replace 'port="8005"', "port=""$($Port + 10)"""
    $c = $c -replace 'port="8080"', "port=""$Port"""
    $c = $c -replace 'port="8009"', "port=""$($Port + 20)"""
    Set-Content $xml $c -Encoding UTF8

    # setenv.bat → 指定 JAVA_HOME
    $se = Join-Path $inst "bin\setenv.bat"
    "@echo off`r`nset `"JAVA_HOME=$JdkDir`"" | Set-Content $se -Encoding ASCII

    # 部署 webshell
    $root = Join-Path $inst "webapps\ROOT"
    Remove-Item (Join-Path $inst "webapps\docs") -Recurse -Force -EA 0
    Remove-Item (Join-Path $inst "webapps\examples") -Recurse -Force -EA 0
    Remove-Item (Join-Path $inst "webapps\manager") -Recurse -Force -EA 0
    Remove-Item (Join-Path $inst "webapps\host-manager") -Recurse -Force -EA 0
    Remove-Item "$root\*" -Recurse -Force -EA 0
    New-Item -ItemType Directory -Force -Path $root | Out-Null

    # 复制 index.jsp 和 webshell 文件
    $srcJsp = Join-Path $Base "..\tomcat-webapps\ROOT\index.jsp"
    if (Test-Path $srcJsp) { Copy-Item $srcJsp $root -Force }
    $wsDest = Join-Path $root "webshell"
    New-Item -ItemType Directory -Force -Path $wsDest | Out-Null
    Copy-Item (Join-Path $WS "*") $wsDest -Recurse -Force

    # 复制 api.jsp 并保护不被删除
    $apiJsp = Join-Path $wsDest "api.jsp"
    if (Test-Path $apiJsp) { attrib +R $apiJsp }

    Write-Host " OK" -f Green
}

# ── 主流程 ─────────────────────────────────────────────────────
Write-Host "`n=== WebShell Test Environment - Windows Native Setup ===`n" -f Yellow
New-Item -ItemType Directory -Force -Path $DL, $RT | Out-Null

Write-Host "[1/3] Downloading ..." -f White
$phpZip  = Fetch $Urls.PHP    "php.zip"
$jdk8Zip = Fetch $Urls.JDK8   "jdk8.zip"
$jdk11Zip= Fetch $Urls.JDK11  "jdk11.zip"
$tcZip   = Fetch $Urls.Tomcat "tomcat.zip"

# JDK 9 可选
$jdk9Zip = Join-Path $DL "jdk9.zip"
$hasJdk9 = Test-Path $jdk9Zip
if (!$hasJdk9) {
    Write-Host "  [info] JDK 9 可选: 手动下载 Oracle JDK 9 zip → downloads/jdk9.zip" -f DarkYellow
}

Write-Host "`n[2/3] Extracting ..." -f White
$phpDir   = Unpack $phpZip   "php"
$jdk8Dir  = Unpack $jdk8Zip  "jdk8"
$jdk11Dir = Unpack $jdk11Zip "jdk11"
$tcSrc    = Unpack $tcZip    "tomcat-src"

if ($hasJdk9) {
    $jdk9Dir = Unpack $jdk9Zip "jdk9"
}

Write-Host "`n[3/3] Configuring ..." -f White

# PHP php.ini
$ini = Join-Path $phpDir "php.ini"
if (!(Test-Path $ini) -or $Force) {
    Copy-Item (Join-Path $phpDir "php.ini-development") $ini -Force
    $c = Get-Content $ini -Raw
    $c = $c -replace ';extension=openssl', 'extension=openssl'
    $c = $c -replace ';extension=mbstring', 'extension=mbstring'
    $c = $c -replace 'upload_max_filesize = 2M', 'upload_max_filesize = 50M'
    Set-Content $ini $c
    Write-Host "  php.ini configured" -f Green
}

# Tomcat 实例
Make-Tomcat $tcSrc $jdk8Dir  "jdk8"  $Ports.jdk8
Make-Tomcat $tcSrc $jdk11Dir "jdk11" $Ports.jdk11
if ($hasJdk9) {
    Make-Tomcat $tcSrc $jdk9Dir "jdk9" $Ports.jdk9
}

Write-Host "`n=== Setup Complete ===" -f Green
Write-Host "Run:  .\start.ps1`n"
