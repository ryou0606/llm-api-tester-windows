"""LLM API Tester - Main entry point."""
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_base_dir() -> Path:
    """Get the base directory - works for both dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    return Path(__file__).parent


def find_free_port(start: int = 12390, end: int = 12490) -> int:
    """Find a free port in the given range."""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                s.close()
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def open_browser(port: int, delay: float = 1.5):
    """Open browser after a short delay."""
    def _open():
        time.sleep(delay)
        webbrowser.open(f"http://localhost:{port}")
    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    base_dir = get_base_dir()

    # Set data directory environment variable for data_store
    import os
    os.environ["LLM_TESTER_DATA_DIR"] = str(base_dir / "data")

    # Ensure data directory exists
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # Ensure static directory exists (for PyInstaller, it's next to exe)
    static_dir = base_dir / "static"
    if not static_dir.exists():
        # Fallback: check if we're in a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            meipass = Path(sys._MEIPASS)
            bundled_static = meipass / "static"
            if bundled_static.exists():
                import shutil
                shutil.copytree(bundled_static, static_dir, dirs_exist_ok=True)

    # Patch server to use correct paths
    os.environ["LLM_TESTER_STATIC_DIR"] = str(static_dir)

    # Find free port
    try:
        port = find_free_port()
    except RuntimeError as e:
        print(f"\n  ❌ 错误: {e}")
        print("  按任意键退出...")
        input()
        return

    print(f"\n  🚀 LLM API Tester 启动中...")
    print(f"  📡 端口: {port}")
    print(f"  🌐 地址: http://localhost:{port}")
    print(f"  ⏹  按 Ctrl+C 停止\n")

    # Open browser
    open_browser(port)

    # Run server - import app directly (string import fails in PyInstaller)
    try:
        import uvicorn
        from app.server import app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\n  👋 已停止")
    except Exception as e:
        print(f"\n  ❌ 启动失败: {e}")
        print("  按任意键退出...")
        input()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  ❌ 致命错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n  按任意键退出...")
        input()
