"""runs one trace at a time so the machine isn't flooded by slider changes."""
from __future__ import annotations

import threading

from ..core.vector import TraceOptions, trace_image

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
_trace_lock = threading.Lock()


def vectorize(image_bytes: bytes, raw_options: dict | None) -> dict:
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Image is too large (limit 40 MB).")
    options = TraceOptions.from_dict(raw_options)
    with _trace_lock:
        return trace_image(image_bytes, options)
