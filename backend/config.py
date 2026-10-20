"""paths and environment variables, the only place that reads them.

LIGHTBENCH_DATA     where jobs, results and thumbnails are stored  (default: ./data)
LIGHTBENCH_MODELS   where model weights are stored                 (default: ./models)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("LIGHTBENCH_DATA", ROOT / "data"))
JOBS_DIR = DATA_DIR / "jobs"
MODELS_DIR = Path(os.environ.get("LIGHTBENCH_MODELS", ROOT / "models"))
FONT_DIR = ROOT / "models" / "fonts"   # filled by setup.py (Noto Sans, SIL OFL)
STATIC_DIR = Path(__file__).resolve().parent / "static"
