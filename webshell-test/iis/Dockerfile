# IIS + Classic ASP + ASP.NET 4.8
# Requires Docker Desktop in Windows containers mode:
#   Right-click Docker tray icon -> "Switch to Windows containers..."
FROM mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2022

SHELL ["powershell", "-Command"]

# Enable Classic ASP
RUN Add-WindowsFeature Web-ASP; \
    Set-WebConfigurationProperty -Filter /system.webServer/directoryBrowse -PSPath 'IIS:\' -Name enabled -Value true; \
    Remove-Item -Recurse C:\inetpub\wwwroot\*

COPY html/ C:/inetpub/wwwroot/
