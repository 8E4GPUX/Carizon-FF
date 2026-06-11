"""产品需求监控脚本 - 每3分钟检测一次"""
import subprocess
import time
import os
import sys

GIT_DIR = r"c:\工具开发\Demo\研发包部署\ota_deploy_tool"
BASELINE_FILE = r"c:\Users\8E4GPUX\.qwen\projects\c-------demo\memory\product_last_commit.txt"


def get_latest_commit():
    """获取产品专用目录的最新提交哈希"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--", "产品专用/"],
            cwd=GIT_DIR,
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            return result.stdout.strip().split()[0]
    except Exception:
        pass
    return ""


def get_baseline():
    """读取基线提交哈希"""
    try:
        with open(BASELINE_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return ""


def save_baseline(hash_val):
    """保存基线提交哈希"""
    try:
        with open(BASELINE_FILE, "w") as f:
            f.write(hash_val)
    except Exception:
        pass


def get_new_commits():
    """获取新提交的详细信息"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--", "产品专用/"],
            cwd=GIT_DIR,
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# 设置控制台编码为 UTF-8
if hasattr(sys, 'stdout') and sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 60)
print("[产品需求监控] 已启动")
print("[检测间隔] 3 分钟")
print("[监控目录] 产品专用/")
print("[Git 仓库] %s" % GIT_DIR)
print("=" * 60)

baseline = get_baseline()
print("[基线提交] %s" % baseline)
print()

while True:
    time.sleep(180)  # 3 分钟

    latest = get_latest_commit()
    if not latest:
        print("[%s] [WARN] 无法获取最新提交" % time.strftime('%H:%M:%S'))
        continue

    if latest != baseline:
        print()
        print("=" * 60)
        print("[%s] [NEW] 检测到新提交!" % time.strftime('%H:%M:%S'))
        print("   旧: %s" % baseline)
        print("   新: %s" % latest)
        print("=" * 60)

        # 获取新提交详情
        log = get_new_commits()
        found_new = False
        for line in log.split("\n"):
            if line.strip():
                h = line.split()[0]
                if h == baseline:
                    break
                print("   [COMMIT] %s" % line.strip())
                found_new = True

        if found_new:
            print()
            print("=" * 60)
            print("[ALERT] 发现新需求！请查看以上提交信息。")
            print("[ALERT] 如需我处理新需求，请告知。")
            print("=" * 60)
            print()

        # 更新基线
        baseline = latest
        save_baseline(latest)
    else:
        print("[%s] [OK] 无新提交 (基线: %s)" % (time.strftime('%H:%M:%S'), baseline))
