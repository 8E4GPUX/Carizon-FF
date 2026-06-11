@echo off
chcp 65001 >nul
cd /d "c:\工具开发\Demo\研发包部署\ota_deploy_tool\研发专用"
"C:\Users\8E4GPUX\AppData\Local\Programs\Python\Python311\python.exe" monitor_daemon.py
pause
