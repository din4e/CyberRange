# WebShell 测试文件说明

本目录包含用于安全测试的各类 WebShell 样本，支持冰蝎和哥斯拉两大主流工具。

## 文件列表

### Behinder（冰蝎）WebShell

#### JSP 版本
- **behinder_3.0_default.jsp** - 标准版本（兼容 Java 8-21）
  - 使用 `java.util.Base64` 解码
  - 默认密码：`rebeyond`
  - 密钥：`e45e329feb5d925b`（密码 MD5 前 16 位）

- **behinder_3.0_default_java9.jsp** - Java 9+ 版本（与标准版功能相同，备用）

- **behinder_3.0_default.jspx** - JSPX 格式版本（XML 格式 JSP）

#### PHP 版本
- **behinder_3.0_default.php** - PHP WebShell（PHP 5.4+）

#### ASP/ASPX 版本
- **behinder_3.0_default.asp** - Classic ASP WebShell（Windows IIS）
- **behinder_3.0_default.aspx** - ASP.NET WebShell（Windows IIS）

> **冰蝎 4.0 兼容说明：** 冰蝎 4.0 的服务端 payload 与 3.0 相同，上述文件均可直接用于冰蝎 4.0 客户端连接。4.0 的主要变化在客户端（新增自定义请求头、分块传输等功能）。

### Godzilla（哥斯拉）WebShell

- **godzilla.php** - PHP WebShell
  - 连接密码：`pass`
  - 密钥：`pass`（与密码相同，XOR 加密）

- **godzilla.jsp** - JSP WebShell
  - 连接密码：`pass`
  - 密钥：`3c6e0b8a9c15224a`（MD5(pass)[0:16]）
  - 加密方式：AES-128 + Base64

- **godzilla.aspx** - ASP.NET WebShell
  - 连接密码：`pass`
  - 密钥：`3c6e0b8a9c15224a`
  - 加密方式：AES-128

### 其他文件
- **api.php** / **api.jsp** - 文件管理 API（上传/列表/删除）
- **index.html** - 目录索引页面

## 连接信息汇总

| 工具 | 语言 | 文件 | 密码 | 密钥 | 加密 |
|------|------|------|------|------|------|
| 冰蝎 3.0/4.0 | PHP | behinder_3.0_default.php | rebeyond | e45e329feb5d925b | AES-128 |
| 冰蝎 3.0/4.0 | JSP | behinder_3.0_default.jsp | rebeyond | e45e329feb5d925b | AES-128 |
| 冰蝎 3.0/4.0 | JSPX | behinder_3.0_default.jspx | rebeyond | e45e329feb5d925b | AES-128 |
| 冰蝎 3.0/4.0 | ASP | behinder_3.0_default.asp | rebeyond | e45e329feb5d925b | XOR |
| 冰蝎 3.0/4.0 | ASPX | behinder_3.0_default.aspx | rebeyond | e45e329feb5d925b | AES-128 |
| 哥斯拉 | PHP | godzilla.php | pass | pass | XOR |
| 哥斯拉 | JSP | godzilla.jsp | pass | 3c6e0b8a9c15224a | AES-128 |
| 哥斯拉 | ASPX | godzilla.aspx | pass | 3c6e0b8a9c15224a | AES-128 |

## 访问地址

### Docker 环境 (端口 20000-20003)
```
PHP:        http://localhost:20000/webshell/
JSP JDK 8:  http://localhost:20001/webshell/
JSP JDK 11: http://localhost:20002/webshell/
JSP JDK 17: http://localhost:20003/webshell/
```

### Windows 原生环境 (端口 20010-20013)
```
PHP:        http://localhost:20010/webshell/
JSP JDK 8:  http://localhost:20011/webshell/
JSP JDK 9:  http://localhost:20012/webshell/ (可选)
JSP JDK 11: http://localhost:20013/webshell/
```

### Docker + 原生可同时运行（端口不冲突）

### Vagrant 环境
```
Linux Apache PHP:  http://localhost:20020/webshell/
Linux Tomcat JSP:  http://localhost:20021/webshell/
Windows IIS ASP:   http://localhost:20022/webshell/
```

## 连接工具设置

### 冰蝎 (Behinder) 3.0 / 4.0
- 下载：https://github.com/rebeyond/Behinder
- URL：上述任意 `.php` / `.jsp` / `.asp` / `.aspx` 地址
- 密码：`rebeyond`
- 冰蝎 4.0 新增功能：自定义请求头、分块传输、内存马管理

### 哥斯拉 (Godzilla)
- 下载：https://github.com/BeichenDream/Godzilla
- URL：上述 `godzilla.*` 地址
- 密码：`pass`
- 密钥：`key`（PHP）或 `3c6e0b8a9c15224a`（JSP/ASPX）
- 有效载荷：Java / PHP / C#
- 加密器：JAVA_AES/PHP_XOR/C#_AES

## 常见问题

### Java 版本兼容性
- **问题**: JSP 报错 `sun.misc.BASE64Decoder cannot be resolved`
- **解决**: 使用 `behinder_3.0_default.jsp`（已更新为标准 Base64 API）

### 哥斯拉连接失败
- 确保密钥设置正确：PHP 使用密码本身作为密钥，JSP/ASPX 使用 `3c6e0b8a9c15224a`
- 哥斯拉 4.0 生成的 webshell 密钥不同，请使用本目录提供的默认版本

## 安全警告

**这些 WebShell 文件仅用于安全测试和教育目的！**

- 不要上传到生产环境
- 不要用于非法用途
- 仅在受控的测试环境中使用
- 测试完成后及时清理
