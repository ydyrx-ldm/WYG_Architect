#!/usr/bin/env python3
"""
WYG Brain - 外脑 App 一键启动
运行此文件即可启动后端并打开浏览器
启动前自动清除占用端口的旧进程
"""

import os
import sys
import webbrowser
import threading
import time
import subprocess
import signal

HOST = "127.0.0.1"
PORT = 8000

# 将 backend 目录加入 Python 路径
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)


def kill_port(port):
    """杀掉占用指定端口的进程"""
    try:
        if sys.platform == "win32":
            # Windows: 用 netstat 找到占用端口的 PID，然后 taskkill
            result = subprocess.run(
                f'netstat -ano | findstr ":{port} " | findstr "LISTENING"',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    print(f"  发现旧进程 PID={pid} 占用端口 {port}，正在终止...")
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                                   capture_output=True, text=True)
                    print(f"  已终止 PID={pid}")
        else:
            # Linux/Mac: 用 lsof 找到占用端口的 PID
            result = subprocess.run(
                f'lsof -ti:{port}', shell=True, capture_output=True, text=True
            )
            for pid in result.stdout.strip().split('\n'):
                if pid.strip():
                    print(f"  发现旧进程 PID={pid} 占用端口 {port}，正在终止...")
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"  已终止 PID={pid}")
    except Exception as e:
        print(f"  清理端口时出错（可忽略）: {e}")


def open_browser():
    """延迟 2 秒后打开浏览器"""
    time.sleep(2)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    print("=" * 50)
    print("  WYG Brain - 外脑 App")
    print("  启动中...")
    print("=" * 50)

    # 清除旧进程
    print(f"\n[1/3] 检查端口 {PORT}...")
    kill_port(PORT)
    time.sleep(0.5)  # 等待端口释放

    # 后台线程打开浏览器
    print(f"[2/3] 准备打开浏览器...")
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动 uvicorn
    print(f"[3/3] 启动服务 http://{HOST}:{PORT}\n")
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
