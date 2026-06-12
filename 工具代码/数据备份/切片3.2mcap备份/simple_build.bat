@echo off
chcp 65001 >nul
echo ========================================
echo    CARIZON 数据切分工具 - 简化打包脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
py --version
if errorlevel 1 (
    echo ❌ 错误：未找到Python环境
    pause
    exit /b 1
)
echo ✅ Python环境检查通过

echo [2/4] 安装依赖...
py -m pip install customtkinter paramiko openpyxl pyinstaller
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 依赖安装完成

echo [3/4] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo ✅ 清理完成

echo [4/4] 开始打包...
echo 正在打包，请稍候...
py -m PyInstaller --onefile --windowed --name "CARIZON数据切分工具" --add-data "Auto_pack.sh;." pack_v3.2.1.py

if exist "dist\CARIZON数据切分工具.exe" (
    echo ✅ 打包成功！
    echo 📁 输出位置: dist\CARIZON数据切分工具.exe
    echo 📊 文件大小: 
    dir "dist\CARIZON数据切分工具.exe" | findstr "CARIZON数据切分工具.exe"
    echo.
    echo 🎉 可以运行 dist\CARIZON数据切分工具.exe
) else (
    echo ❌ 打包失败
)

echo.
echo 按任意键退出...
pause >nul






