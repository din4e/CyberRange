# CyberRange

网络安全靶场环境集合，用于渗透测试学习和 CTF 训练。

## 项目结构

```text
CyberRange/
├── pentest/               # 渗透测试靶场
│   └── cfs/              # CFS 三层内网渗透靶场
└── README.md
```

## 环境要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- Windows 11 / Windows 10 Pro / Linux / macOS

## 快速开始

### CFS 靶场

CFS 是一个三层内网渗透靶场，涵盖 Shiro 反序列化、Tomcat 弱口令、WebLogic 弱口令、JBoss 反序列化等常见漏洞。

```powershell
cd pentest/cfs
.\cfs-manage.ps1 start
```

详细文档：[pentest/cfs/README.md](pentest/cfs/README.md)

## 资源限制

所有靶场已配置资源限制，防止过度占用系统资源：

| 服务     | CPU 限制  | 内存限制 |
| -------- | --------- | -------- |
| Shiro    | 0.5 核    | 512M     |
| Tomcat   | 1.0 核    | 1G       |
| WebLogic | 1.5 核    | 2G       |
| JBoss    | 1.0 核    | 1G       |

## 免责声明

本项目仅供安全研究和教育目的使用。请勿用于非法用途。使用本靶场环境所造成的任何后果由使用者自行承担。

## 许可证

MIT License
