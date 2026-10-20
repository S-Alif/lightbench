#!/usr/bin/env python3
"""Start Lightbench:  python run.py

    --lan          listen on your network too (open it from your phone)
    --port 8000    pick a port (the next free one is used if it's taken)
    --no-browser   don't open a browser tab

First launch runs setup.py automatically (creates .venv, installs PyTorch etc.).
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def free_port(host: str, start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket() as probe_socket:
            if probe_socket.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("No free port found")


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe_socket:
            probe_socket.connect(("10.255.255.255", 1))
            return probe_socket.getsockname()[0]
    except OSError:
        return "your-computer-ip"


def main() -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--host", default="127.0.0.1")
    arg_parser.add_argument("--lan", action="store_true", help="shortcut for --host 0.0.0.0")
    arg_parser.add_argument("--port", type=int, default=8000)
    arg_parser.add_argument("--no-browser", action="store_true")
    args = arg_parser.parse_args()
    host = "0.0.0.0" if args.lan else args.host

    # Dev/Docker escape hatch: use the interpreter you launched with.
    if os.environ.get("LIGHTBENCH_USE_CURRENT_PYTHON"):
        python_path = Path(sys.executable)
    else:
        python_path = VENV_PY
        if not python_path.exists() or not (VENV / ".setup-complete").exists():
            print("First run: setting things up (this takes a few minutes)...\n")
            if subprocess.call([sys.executable, str(ROOT / "setup.py")]) != 0:
                return 1
    if not (ROOT / "backend" / "static" / "index.html").exists():
        sys.path.insert(0, str(ROOT))
        import setup as _setup  # noqa: PLC0415
        _setup.build_frontend()

    port = free_port(host, args.port)
    local = f"http://127.0.0.1:{port}"
    print(f"\n  Lightbench running at {local}")
    if host == "0.0.0.0":
        print(f"  On your network:    http://{lan_ip()}:{port}")
        print("  (no password: only use --lan on a network you trust)")
    print("  Press Ctrl+C to stop.\n")

    if not args.no_browser:
        def open_when_ready() -> None:
            for _ in range(60):
                try:
                    urllib.request.urlopen(f"{local}/api/system", timeout=1).close()
                    webbrowser.open(local)
                    return
                except Exception:  # noqa: BLE001
                    time.sleep(0.5)
        threading.Thread(target=open_when_ready, daemon=True).start()

    try:
        return subprocess.call(
            [str(python_path), "-m", "uvicorn", "backend.main:app", "--host", host, "--port", str(port),
             "--log-level", "warning"], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
