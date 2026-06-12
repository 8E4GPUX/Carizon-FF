@echo off
chcp 65001 >nul
echo ========================================
echo    CARIZON 数据切分工具 - 自动打包脚本
echo ========================================
echo.

:: 检查Python环境
echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python环境检查通过

:: 检查PyInstaller
echo [2/6] 检查PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  PyInstaller未安装，正在安装...
    pip install pyinstaller>=5.13.0
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)
echo ✅ PyInstaller检查通过

:: 安装依赖
echo [3/6] 安装项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 依赖安装完成

:: 清理旧的构建文件
echo [4/6] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
echo ✅ 清理完成

:: 执行打包
echo [5/6] 开始打包...
pyinstaller --clean pack_v3.2.1.spec
if errorlevel 1 (
    echo ❌ 打包失败
    pause
    exit /b 1
)
echo ✅ 打包完成

:: 检查输出文件
echo [6/6] 检查输出文件...
if exist "dist\CARIZON数据切分工具.exe" (
    echo ✅ 可执行文件生成成功
    echo.
    echo 📁 输出位置: dist\CARIZON数据切分工具.exe
    echo 📊 文件大小: 
    dir "dist\CARIZON数据切分工具.exe" | findstr "CARIZON数据切分工具.exe"
    echo.
    echo 🎉 打包完成！可以运行 dist\CARIZON数据切分工具.exe
) else (
    echo ❌ 可执行文件生成失败
    pause
    exit /b 1
)

echo.
echo 按任意键退出...
pause >nul
