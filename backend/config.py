"""paths and environment variables, the only place that reads them.

LIGHTBENCH_DATA     where jobs, results and thumbnails are stored  (default: ./data)
LIGHTBENCH_MODELS   where model weights are stored                 (default: ./models)
LIGHTBENCH_PASSWORD password asked from other devices on the network (default: none; run.py sets it for --lan)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("LIGHTBENCH_DATA", ROOT / "data"))
JOBS_DIR = DATA_DIR / "jobs"
PASSWORD = os.environ.get("LIGHTBENCH_PASSWORD") or None
MODELS_DIR = Path(os.environ.get("LIGHTBENCH_MODELS", ROOT / "models"))
FONT_DIR = ROOT / "models" / "fonts"   # filled by setup.py (Noto Sans, SIL OFL)
STATIC_DIR = Path(__file__).resolve().parent / "static"
