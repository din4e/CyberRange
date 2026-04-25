# CyberRange - 项目指南

## 项目概述

网络安全靶场管理平台，提供 CLI 和 MCP Server 管理基于 Docker 的靶场环境，支持多实例、多类别，为 AI Agent 自动化渗透测试提供基础设施。

## 技术栈

- **语言**: Python 3.10+
- **依赖管理**: setuptools + pyproject.toml
- **CLI 框架**: Typer + Rich
- **MCP Server**: mcp[cli] (FastMCP)
- **数据模型**: Pydantic v2
- **容器编排**: Docker Compose (subprocess 调用)
- **平台**: Windows 11 / Linux / macOS

## 项目结构

```
CyberRange/
├── cyberrange/                  # Python 管理包
│   ├── cli.py                   # Typer CLI 入口 (start/stop/status/list/stats/serve)
│   ├── mcp_server.py            # FastMCP 工具定义 (7 个工具)
│   ├── __main__.py              # python -m cyberrange 入口
│   ├── core/
│   │   ├── config.py            # 路径常量、端口池配置 (9000-9999)
│   │   ├── models.py            # Pydantic 数据模型
│   │   ├── discovery.py         # 扫描目录发现靶场 (docker-compose.yml)
│   │   ├── docker_client.py     # subprocess 封装 docker compose CLI
│   │   ├── ports.py             # 多实例端口分配
│   │   ├── stats.py             # 运行时间/交互统计 (JSON 持久化)
│   │   └── manager.py           # 核心编排器 (RangeManager)
│   └── data/                    # 运行时数据 (gitignored)
├── pentest/                     # 渗透测试靶场目录
│   └── cfs/                     # CFS 三层内网渗透靶场
│       ├── docker-compose.yml   # 4 服务 + 3 网络
│       ├── .env                 # FLAGS + COMPOSE_PROJECT_NAME
│       └── cfs-manage.ps1       # 旧版 PowerShell 管理脚本
└── pyproject.toml
```

## 开发命令

```bash
# 安装 (可编辑模式)
pip install -e .

# CLI 使用
cyberrange list
cyberrange start pentest/cfs
cyberrange start pentest/cfs -i 2    # 多实例
cyberrange status
cyberrange stats
cyberrange stop pentest/cfs --remove

# MCP Server
cyberrange serve                     # stdio 模式 (Claude Code 集成)
cyberrange serve -t streamable-http   # HTTP 模式

# 也可通过 python -m 运行
python -m cyberrange list
```

## 架构要点

### 靶场发现
- 扫描项目根目录下 `<category>/<name>/docker-compose.yml`
- 跳过 `.git`, `.claude`, `.omc`, `node_modules`, `cyberrange` 等目录
- 通过 `docker compose config --format json` 解析服务/网络元数据

### 多实例隔离
- 实例 1: 使用原始项目名 (如 `cfs`)，保留原始端口和子网
- 实例 N: 使用 `{name}-{N}` (如 `cfs-2`)，自动分配：
  - 端口: 从 9000-9999 池分配 (每实例 20 端口)
  - 子网: /16 → `172.{30+N}.0.0/16`，/24 → 第三段偏移
  - IP: 与子网同步偏移
- 生成完整 compose 文件 (非 override)，避免 Docker 合并问题

### 项目名规则
- `RangeManager._project_name(name, id)`: id==1 返回原始名，否则 `{name}-{id}`
- MCP 工具中 `record_interaction` / `get_stats` 需使用相同规则

### Windows 兼容
- `docker_client.py` 使用 `encoding="utf-8", errors="replace"` 避免 GBK 解码错误
- `docker compose ps --format json` 返回 NDJSON (逐行)，非 JSON 数组
- 端口检测绑定 `0.0.0.0` (非 `127.0.0.1`)，因为 Docker 发布端口用 `0.0.0.0`

## MCP 工具列表

| 工具 | 参数 | 只读 | 用途 |
|------|------|------|------|
| `list_ranges` | - | 是 | 列出所有靶场及运行实例 |
| `start_range` | range_key, instance_id | 否 | 启动靶场实例 |
| `stop_range` | range_key, instance_id, remove, volumes | 否 | 停止/销毁实例 |
| `get_status` | range_key?, instance_id? | 是 | 查询运行状态、服务IP/端口 |
| `get_topology` | range_key, instance_id | 是 | 网络拓扑图+攻击路径 |
| `get_stats` | range_key?, instance_id? | 是 | 启动次数、运行时间统计 |
| `record_interaction` | range_key, instance_id, action, details | 否 | 记录 AI Agent 交互事件 |

## 已知问题

- PowerShell 脚本 `cfs-manage.ps1` 需 UTF-8 BOM，否则 PowerShell 5.1 按 GBK 解析中文导致语法错误
- `docker compose config` 输出包含 `name:` (项目名) 和网络 `name:` (带项目前缀)，生成 compose 文件时必须移除
