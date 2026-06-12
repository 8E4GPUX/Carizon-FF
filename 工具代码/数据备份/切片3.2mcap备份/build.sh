#!/bin/bash

echo "========================================"
echo "   CARIZON 数据切分工具 - 自动打包脚本"
echo "========================================"
echo

# 检查Python环境
echo "[1/6] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3环境，请先安装Python 3.8+"
    exit 1
fi
echo "✅ Python环境检查通过"

# 检查PyInstaller
echo "[2/6] 检查PyInstaller..."
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "⚠️  PyInstaller未安装，正在安装..."
    pip3 install pyinstaller>=5.13.0
    if [ $? -ne 0 ]; then
        echo "❌ PyInstaller安装失败"
        exit 1
    fi
fi
echo "✅ PyInstaller检查通过"

# 安装依赖
echo "[3/6] 安装项目依赖..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi
echo "✅ 依赖安装完成"

# 清理旧的构建文件
echo "[4/6] 清理旧的构建文件..."
rm -rf build dist __pycache__
echo "✅ 清理完成"

# 执行打包
echo "[5/6] 开始打包..."
pyinstaller --clean pack_v3.2.1.spec
if [ $? -ne 0 ]; then
    echo "❌ 打包失败"
    exit 1
fi
echo "✅ 打包完成"

# 检查输出文件
echo "[6/6] 检查输出文件..."
if [ -f "dist/CARIZON数据切分工具" ]; then
    echo "✅ 可执行文件生成成功"
    echo
    echo "📁 输出位置: dist/CARIZON数据切分工具"
    echo "📊 文件大小: $(du -h 'dist/CARIZON数据切分工具' | cut -f1)"
    echo
    echo "🎉 打包完成！可以运行 dist/CARIZON数据切分工具"
else
    echo "❌ 可执行文件生成失败"
    exit 1
fi

echo
echo "按任意键退出..."
read -n 1
