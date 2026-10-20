#!/usr/bin/env python3
"""One-time setup: virtualenv + the right PyTorch build + everything else.

    python setup.py                 auto-detect GPU
    python setup.py --cpu           force the small CPU-only PyTorch
    python setup.py --cuda 126      force a CUDA build (126 = most GPUs, 128 = RTX 50-series)
    python setup.py --rocm          AMD GPU on Linux
    python setup.py --models        also pre-download the model weights (~150 MB)
    python setup.py --dry-run       only print what would be done

You normally don't need to run this by hand: `python run.py` does it on first launch.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
MARKER = VENV / ".setup-complete"

# Edit these if PyTorch publishes newer index names.
TORCH_INDEX = {
    "cpu": "https://download.pytorch.org/whl/cpu",
    "cu126": "https://download.pytorch.org/whl/cu126",
    "cu128": "https://download.pytorch.org/whl/cu128",
    "rocm": "https://download.pytorch.org/whl/rocm6.4",
}
FONT_URL = ("https://github.com/notofonts/notofonts.github.io/raw/main/"
            "fonts/NotoSans/hinted/ttf/NotoSans-Bold.ttf")


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(cmd, **popen_kwargs):
    print("  $", " ".join(str(part) for part in cmd))
    subprocess.check_call([str(part) for part in cmd], **popen_kwargs)


def detect_flavor() -> tuple[str, str]:
    """-> (flavor, human reason). flavor is one of: default (macOS), cpu, cu126, cu128, rocm"""
    if sys.platform == "darwin":
        return "default", "macOS: the standard wheel includes Apple-GPU (MPS) support"
    if shutil.which("nvidia-smi"):
        cap = ""
        try:
            cap = subprocess.run(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=15).stdout.split("\n")[0].strip()
        except Exception:  # noqa: BLE001
            pass
        try:
            if cap and float(cap) >= 12.0:
                return "cu128", f"NVIDIA GPU (compute {cap}, Blackwell) -> CUDA 12.8 build"
        except ValueError:
            pass
        return "cu126", f"NVIDIA GPU detected{f' (compute {cap})' if cap else ''} -> CUDA 12.6 build"
    if sys.platform.startswith("linux") and (shutil.which("rocminfo") or Path("/opt/rocm").exists()):
        return "rocm", "AMD ROCm detected -> ROCm build"
    why = "No supported GPU found"
    if sys.platform == "win32":
        why += " (AMD/Intel GPUs on Windows aren't supported by PyTorch; CPU mode will be used)"
    return "cpu", why + " -> CPU-only build"


def torch_ok(python_path: Path) -> bool:
    result = subprocess.run([str(python_path), "-c", "import torch"], capture_output=True)
    return result.returncode == 0


def main() -> int:
    arg_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode_group = arg_parser.add_mutually_exclusive_group()
    mode_group.add_argument("--cpu", action="store_true")
    mode_group.add_argument("--cuda", choices=["126", "128"])
    mode_group.add_argument("--rocm", action="store_true")
    arg_parser.add_argument("--torch-index", help="custom PyTorch wheel index URL")
    arg_parser.add_argument("--models", action="store_true", help="download model weights now")
    arg_parser.add_argument("--force", action="store_true", help="reinstall PyTorch even if present")
    arg_parser.add_argument("--dry-run", action="store_true")
    args = arg_parser.parse_args()

    if sys.version_info < (3, 10):
        print(f"Python 3.10+ is required (you have {sys.version.split()[0]}).")
        return 1
    if sys.version_info >= (3, 14):
        print("Note: very new Python versions may not have PyTorch wheels yet. If install fails, use Python 3.11-3.13.")

    if args.cpu:
        flavor, why = "cpu", "forced CPU"
    elif args.cuda:
        flavor, why = f"cu{args.cuda}", "forced CUDA"
    elif args.rocm:
        flavor, why = "rocm", "forced ROCm"
    else:
        flavor, why = detect_flavor()
    print(f"\n[1/5] PyTorch flavour: {flavor}  ({why})")
    index = args.torch_index or TORCH_INDEX.get(flavor)
    if args.dry_run:
        print(f"      would install torch from {index or 'PyPI'} into {VENV}")
        return 0

    print(f"\n[2/5] Virtual environment: {VENV}")
    if not venv_python().exists():
        try:
            run([sys.executable, "-m", "venv", VENV])
        except subprocess.CalledProcessError:
            print("Could not create a virtualenv. On Debian/Ubuntu: sudo apt install python3-venv")
            return 1
    python_path = venv_python()
    run([python_path, "-m", "pip", "install", "-q", "--upgrade", "pip"])

    print("\n[3/5] Installing PyTorch (large download, one time)")
    if args.force or not torch_ok(python_path):
        cmd = [python_path, "-m", "pip", "install", "torch"]
        if index:
            cmd += ["--index-url", index]
        try:
            run(cmd)
        except subprocess.CalledProcessError:
            print("\nPyTorch install failed. Try: python setup.py --cpu   (or --cuda 126 / --rocm)")
            return 1
    else:
        print("  already installed")

    print("\n[4/5] Installing the other Python packages")
    run([python_path, "-m", "pip", "install", "-r", ROOT / "requirements.txt"])

    print("\n[5/5] Extras")
    font = ROOT / "models" / "fonts" / "NotoSans-Bold.ttf"
    if not font.exists():
        try:
            font.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(FONT_URL, headers={"User-Agent": "upscaler-setup"})
            with urllib.request.urlopen(req, timeout=30) as result:
                data = result.read()
            if len(data) < 50_000:
                raise OSError("unexpected response")
            font.write_bytes(data)
            print("  watermark font downloaded (Noto Sans Bold, SIL OFL)")
        except Exception as error:  # noqa: BLE001
            print(f"  watermark font not downloaded ({error}); a system font will be used instead")
    if not (ROOT / "backend" / "static" / "index.html").exists():
        build_frontend()
    if args.models:
        run([python_path, "-c",
             "from backend.core.models import registry\n"
             "for file_name in registry.BUILTIN:\n"
             "    print('  ', file_name, flush=True)\n"
             "    registry.ensure_weights(file_name, lambda fraction: print(f'\\r    {int(fraction*100)}%', end='', flush=True))\n"
             "    print()\n"], cwd=ROOT)

    result = subprocess.run([str(python_path), "-c",
                        "from backend.core import device; d=device.describe(); "
                        "print(f\"  detected: {d['backend']} - {d['name']}\")"], cwd=ROOT)
    MARKER.write_text("ok\n")
    print("\nDone. Start the app with:  python run.py")
    return 0 if result.returncode == 0 else 1


def build_frontend() -> bool:
    npm = shutil.which("npm")
    if not npm:
        print("  frontend isn't built and Node.js isn't installed. Install Node 18+ and run:\n"
              "      cd frontend && npm install && npm run build")
        return False
    try:
        run([npm, "install"], cwd=ROOT / "frontend")
        run([npm, "run", "build"], cwd=ROOT / "frontend")
        return True
    except subprocess.CalledProcessError:
        print("  frontend build failed (see above)")
        return False


if __name__ == "__main__":
    sys.exit(main())
