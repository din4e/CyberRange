<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP Apache</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 40px 20px;
            line-height: 1.6;
        }
        .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; }
        h1 { font-size: 1.5em; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 20px; }

        .info-box { background: #f5f5f5; padding: 12px 15px; margin: 15px 0; }
        .info-box h3 { font-size: 1em; margin-bottom: 8px; }
        .info-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e0e0e0; }
        .info-item:last-child { border-bottom: none; }
        .info-label { font-weight: 500; }
        .info-value { font-family: monospace; background: #fff; padding: 2px 8px; }

        .status { color: #28a745; font-weight: 600; }
        .tag {
            display: inline-block; padding: 2px 10px; font-size: 0.8em;
            border: 1px solid #333; margin-right: 6px; font-family: monospace;
        }

        .link-list { margin-top: 15px; }
        .link-item {
            border: 1px solid #e0e0e0; padding: 12px 15px; margin: 8px 0;
            display: flex; justify-content: space-between; align-items: center;
            text-decoration: none; color: #333;
        }
        .link-item:hover { background: #f5f5f5; }
        .link-label { font-weight: 500; }
        .link-url { color: #888; font-size: 0.85em; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>PHP Apache</h1>
        <p class="subtitle">WebShell 测试靶场 <span class="status">运行中</span></p>

        <div class="info-box">
            <h3>环境信息</h3>
            <div class="info-item">
                <span class="info-label">服务器</span>
                <span class="info-value"><?php echo apache_get_version(); ?></span>
            </div>
            <div class="info-item">
                <span class="info-label">端口</span>
                <span class="info-value">20000</span>
            </div>
            <div class="info-item">
                <span class="info-label">PHP 版本</span>
                <span class="info-value"><?php echo PHP_VERSION; ?></span>
            </div>
            <div class="info-item">
                <span class="info-label">操作系统</span>
                <span class="info-value"><?php echo PHP_OS; ?></span>
            </div>
            <div class="info-item">
                <span class="info-label">支持类型</span>
                <span><span class="tag">.php</span></span>
            </div>
            <div class="info-item">
                <span class="info-label">服务器时间</span>
                <span class="info-value"><?php echo date('Y-m-d H:i:s'); ?></span>
            </div>
        </div>

        <div class="link-list">
            <a href="/webshell/" class="link-item">
                <span class="link-label">WebShell 目录</span>
                <span class="link-url">/webshell/</span>
            </a>
            <a href="http://localhost:20001/" class="link-item">
                <span class="link-label">Tomcat 环境</span>
                <span class="link-url">:20001</span>
            </a>
            <a href="?phpinfo=1" class="link-item">
                <span class="link-label">PHP 信息</span>
                <span class="link-url">phpinfo()</span>
            </a>
        </div>

        <?php
        if (isset($_GET['phpinfo'])) {
            echo '<div style="margin-top: 20px; background: #fff; padding: 20px;">';
            phpinfo();
            echo '</div>';
        }
        ?>
    </div>
</body>
</html>
