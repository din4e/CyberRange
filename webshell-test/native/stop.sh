#!/usr/bin/env bash
# WebShell 测试环境 - Linux 停止脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RT_DIR="$SCRIPT_DIR/runtime"
PIDS_FILE="$RT_DIR/.pids"

ok()    { echo -e "\e[32m  $*\e[0m"; }
info()  { echo -e "\e[36m  $*\e[0m"; }

echo ""
echo "=== Stopping WebShell Test Services ==="
echo ""

# 方式1: 通过 PID 文件
if [[ -f "$PIDS_FILE" ]]; then
    while IFS=: read -r label pid; do
        if [[ -n "$pid" && "$pid" != "unknown" ]]; then
            info "Stopping $label (PID $pid) ..."
            kill "$pid" 2>/dev/null || true
            # 等待进程退出
            timeout 5 bash -c "while kill -0 $pid 2>/dev/null; do sleep 0.5; done" 2>/dev/null || true
            ok "$label stopped"
        fi
    done < "$PIDS_FILE"
    rm -f "$PIDS_FILE"
fi

# 方式2: 通过 catalina 脚本停止
for tc in "$RT_DIR"/tomcat-*/; do
    if [[ -d "$tc" && -x "$tc/bin/catalina.sh" ]]; then
        label=$(basename "$tc" | sed 's/tomcat-//')
        info "Stopping tomcat-$label via catalina.sh ..."
        CATALINA_HOME="$tc" CATALINA_BASE="$tc" "$tc/bin/catalina.sh" stop &>/dev/null || true
    fi
done

# 方式3: 兜底 - 通过端口杀进程
for port in 20010 20011 20012 20013 20014; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [[ -n "$pid" ]]; then
        info "Killing PID $pid on port $port ..."
        kill $pid 2>/dev/null || true
    fi
done

echo ""
ok "All services stopped."
echo ""
