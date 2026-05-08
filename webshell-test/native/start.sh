#!/usr/bin/env bash
# WebShell 测试环境 - Linux 启动脚本
# 用法: ./start.sh [php] [jdk8] [jdk9] [jdk11] [jdk17]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RT_DIR="$SCRIPT_DIR/runtime"
WS_DIR="$(cd "$SCRIPT_DIR/../webshell" && pwd)"
HTML_DIR="$(cd "$SCRIPT_DIR/../html" && pwd)"

declare -A PORTS=( [php]=20010 [jdk8]=20011 [jdk9]=20012 [jdk11]=20013 [jdk17]=20014 )
PIDS_FILE="$RT_DIR/.pids"

# 只启动指定服务或全部
SERVICES=("$@")
(( ${#SERVICES[@]} == 0 )) && SERVICES=(php jdk8 jdk9 jdk11 jdk17)

cleanup() { echo ""; }
trap cleanup EXIT

info()  { echo -e "\e[36m  $*\e[0m"; }
ok()    { echo -e "\e[32m  $*\e[0m"; }
warn()  { echo -e "\e[33m  $*\e[0m"; }
dim()   { echo -e "\e[90m  $*\e[0m"; }

echo ""
echo "=== Starting WebShell Test Services (Linux) ==="
echo ""

mkdir -p "$RT_DIR"
echo "" > "$PIDS_FILE"

# -- PHP --
start_php() {
    if ! command -v php &>/dev/null; then
        warn "[php] not found in PATH, skipping"
        return
    fi
    local port=${PORTS[php]}
    local docroot="$RT_DIR/php-docroot"

    # 创建 document root
    if [[ ! -d "$docroot" ]]; then
        mkdir -p "$docroot"
        cp -r "$HTML_DIR"/* "$docroot/"
        mkdir -p "$docroot/webshell"
        cp -r "$WS_DIR"/* "$docroot/webshell/"
    fi

    info "[php] :$port ..."
    php -S "0.0.0.0:$port" -t "$docroot" &>/dev/null &
    local pid=$!
    echo "php:$pid" >> "$PIDS_FILE"
    ok "[php] :$port (PID $pid)"
}

# -- Tomcat --
start_tomcat() {
    local label="$1"
    local tc_dir="$RT_DIR/tomcat-$label"
    local port=${PORTS[$label]}

    if [[ ! -d "$tc_dir" ]]; then
        dim "[$label] not installed"
        return
    fi

    info "[$label] :$port ..."
    export CATALINA_HOME="$tc_dir"
    export CATALINA_BASE="$tc_dir"
    # 读取 setenv.sh 中的 JAVA_HOME
    if [[ -f "$tc_dir/bin/setenv.sh" ]]; then
        source "$tc_dir/bin/setenv.sh"
    fi

    "$tc_dir/bin/catalina.sh" start &>/dev/null
    # 找到 java 进程 PID
    sleep 1
    local pid=$(pgrep -f "catalina.base=$tc_dir" 2>/dev/null || echo "unknown")
    echo "$label:$pid" >> "$PIDS_FILE"
    ok "[$label] :$port (PID $pid)"
}

# 启动服务
for svc in "${SERVICES[@]}"; do
    case "$svc" in
        php)    start_php ;;
        jdk8)   start_tomcat jdk8 ;;
        jdk9)   start_tomcat jdk9 ;;
        jdk11)  start_tomcat jdk11 ;;
        jdk17)  start_tomcat jdk17 ;;
        *)      warn "Unknown service: $svc" ;;
    esac
done

# 等待端口就绪
echo ""
echo -n "Waiting for services ..."
sleep 3

for svc in "${SERVICES[@]}"; do
    port=${PORTS[$svc]}
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
        echo ""
        ok "[$svc] :$port READY"
    else
        echo ""
        warn "[$svc] :$port STARTING..."
    fi
done

# 输出访问地址
echo ""
echo "=== Access URLs (Native) ==="
echo ""
for svc in "${SERVICES[@]}"; do
    port=${PORTS[$svc]}
    case "$svc" in
        php)   echo "  PHP        http://localhost:$port/" ;;
        jdk*)  echo "  Tomcat $svc http://localhost:$port/" ;;
    esac
    echo "  WebShell   http://localhost:$port/webshell/"
done
echo ""
echo "Docker: 20000-20003 | Native: 20010-20014"
echo "Stop: ./stop.sh"
echo ""
