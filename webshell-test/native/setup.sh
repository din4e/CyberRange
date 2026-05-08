#!/usr/bin/env bash
# WebShell 测试环境 - Linux 原生安装脚本
# 下载并配置 PHP + Tomcat(JDK 8/11/17) 运行环境
# 用法: ./setup.sh [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DL_DIR="$SCRIPT_DIR/downloads"
RT_DIR="$SCRIPT_DIR/runtime"
WS_DIR="$(cd "$SCRIPT_DIR/../webshell" && pwd)"
HTML_DIR="$(cd "$SCRIPT_DIR/../html" && pwd)"
JSP_DIR="$(cd "$SCRIPT_DIR/../tomcat-webapps/ROOT" && pwd)"
FORCE="${1:-}"

declare -A PORTS=( [php]=20010 [jdk8]=20011 [jdk9]=20012 [jdk11]=20013 [jdk17]=20014 )

# -- 颜色输出 --
info()  { echo -e "\e[36m  $*\e[0m"; }
ok()    { echo -e "\e[32m  $*\e[0m"; }
skip()  { echo -e "\e[90m  $*\e[0m"; }
warn()  { echo -e "\e[33m  $*\e[0m"; }

# -- 下载 (带重试) --
fetch() {
    local url="$1" file="$2" path="$DL_DIR/$file"
    if [[ -f "$path" && "$FORCE" != "--force" ]]; then
        skip "[skip] $file already downloaded"
        return 0
    fi
    rm -f "$path"
    local tries=0
    while (( tries < 3 )); do
        ((tries++))
        info "download $file (attempt $tries) ..."
        if curl -fSL -o "$path" "$url"; then
            ok "$file downloaded"
            return 0
        fi
        warn "download failed, retrying in 3s ..."
        sleep 3
    done
    echo "ERROR: Failed to download $file after 3 attempts" >&2
    return 1
}

# -- 解压 --
unpack() {
    local zip="$1" label="$2" dest="$RT_DIR/$label"
    if [[ -d "$dest" && "$FORCE" != "--force" ]]; then
        skip "[skip] $label already extracted"
        return 0
    fi
    rm -rf "$dest"
    mkdir -p "$dest"
    info "extract $label ..."
    tar -xzf "$zip" -C "$dest" 2>/dev/null || unzip -q "$zip" -d "$dest"
    ok "$label extracted"
}

# -- 查找解压后的根目录 --
find_dir() {
    local dest="$RT_DIR/$1"
    local dirs=("$dest"/*/)
    if (( ${#dirs[@]} == 1 )); then
        echo "${dirs[0]%/}"
    else
        echo "$dest"
    fi
}

# -- 创建 Tomcat 实例 --
make_tomcat() {
    local tc_src="$1" jdk_dir="$2" label="$3" port="$4"
    local inst="$RT_DIR/tomcat-$label"

    if [[ -d "$inst" && "$FORCE" != "--force" ]]; then
        skip "[skip] tomcat-$label"
        return 0
    fi
    rm -rf "$inst"
    info "setup tomcat-$label (port $port) ..."
    cp -r "$tc_src" "$inst"

    # 修改端口
    sed -i "s/port=\"8005\"/port=\"$((port+10))\"/" "$inst/conf/server.xml"
    sed -i "s/port=\"8080\"/port=\"$port\"/" "$inst/conf/server.xml"
    sed -i "s/port=\"8009\"/port=\"$((port+20))\"/" "$inst/conf/server.xml"

    # setenv.sh → 指定 JAVA_HOME
    cat > "$inst/bin/setenv.sh" <<EOF
#!/bin/sh
export JAVA_HOME="$jdk_dir"
EOF
    chmod +x "$inst/bin/setenv.sh"

    # 清理默认 webapps
    rm -rf "$inst/webapps/docs" "$inst/webapps/examples" "$inst/webapps/manager" "$inst/webapps/host-manager"

    # 部署 index.jsp
    rm -rf "$inst/webapps/ROOT"/*
    cp "$JSP_DIR/index.jsp" "$inst/webapps/ROOT/" 2>/dev/null || true

    # 部署 webshell
    mkdir -p "$inst/webapps/ROOT/webshell"
    cp -r "$WS_DIR"/* "$inst/webapps/ROOT/webshell/"

    # 设置执行权限
    chmod +x "$inst/bin/"*.sh

    ok "tomcat-$label configured (port $port)"
}

# ======================== 主流程 ========================

echo ""
echo "=== WebShell Test Environment - Linux Native Setup ==="
echo ""

mkdir -p "$DL_DIR" "$RT_DIR"

# -- 下载 --
echo "[1/3] Downloading ..."
fetch "https://www.php.net/distributions/php-8.2.31.tar.gz" "php.tar.gz"
fetch "https://api.adoptium.net/v3/binary/latest/8/ga/linux/x64/jdk/hotspot/normal/eclipse?project=jdk" "jdk8.tar.gz"
fetch "https://api.adoptium.net/v3/binary/latest/11/ga/linux/x64/jdk/hotspot/normal/eclipse?project=jdk" "jdk11.tar.gz"
fetch "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse?project=jdk" "jdk17.tar.gz"
fetch "https://archive.apache.org/dist/tomcat/tomcat-9/v9.0.117/bin/apache-tomcat-9.0.117.tar.gz" "tomcat.tar.gz"

# JDK 9 可选
if [[ -f "$DL_DIR/jdk9.tar.gz" ]]; then
    echo "  JDK 9 found"
else
    warn "JDK 9 可选: 手动下载 Oracle JDK 9 tar.gz → downloads/jdk9.tar.gz"
fi

# -- 解压 --
echo ""
echo "[2/3] Extracting ..."
unpack "$DL_DIR/php.tar.gz" "php"
unpack "$DL_DIR/jdk8.tar.gz" "jdk8"
unpack "$DL_DIR/jdk11.tar.gz" "jdk11"
unpack "$DL_DIR/jdk17.tar.gz" "jdk17"
unpack "$DL_DIR/tomcat.tar.gz" "tomcat-src"
[[ -f "$DL_DIR/jdk9.tar.gz" ]] && unpack "$DL_DIR/jdk9.tar.gz" "jdk9"

PHP_DIR=$(find_dir php)
JDK8_DIR=$(find_dir jdk8)
JDK11_DIR=$(find_dir jdk11)
JDK17_DIR=$(find_dir jdk17)
TC_SRC=$(find_dir tomcat-src)
[[ -f "$DL_DIR/jdk9.tar.gz" ]] && JDK9_DIR=$(find_dir jdk9)

# -- 配置 --
echo ""
echo "[3/3] Configuring ..."

# PHP: 编译或使用系统 PHP
if ! command -v php &>/dev/null; then
    warn "PHP not found in PATH. Install via: sudo apt install php"
    warn "Or compile from source in: $PHP_DIR"
fi

# Tomcat 实例
make_tomcat "$TC_SRC" "$JDK8_DIR" "jdk8" "${PORTS[jdk8]}"
make_tomcat "$TC_SRC" "$JDK11_DIR" "jdk11" "${PORTS[jdk11]}"
make_tomcat "$TC_SRC" "$JDK17_DIR" "jdk17" "${PORTS[jdk17]}"
[[ -f "$DL_DIR/jdk9.tar.gz" ]] && make_tomcat "$TC_SRC" "$JDK9_DIR" "jdk9" "${PORTS[jdk9]}"

echo ""
ok "=== Setup Complete ==="
echo "Run: ./start.sh"
echo ""
