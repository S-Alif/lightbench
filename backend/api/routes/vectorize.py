"""POST /api/vectorize: image in, svg out. nothing is stored on disk."""
from __future__ import annotations

import json

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from ...core.vector import VectorizerMissing
from ...services import vectorize as vectorize_service
from ..helpers import error_response


async def vectorize(request):
    form = await request.form()
    upload = form.get("file")
    if not hasattr(upload, "read"):
        return error_response("No image uploaded")
    try:
        raw_options = json.loads(form.get("options") or "{}")
        image_bytes = await upload.read()
        result = await run_in_threadpool(vectorize_service.vectorize, image_bytes, raw_options)
    except VectorizerMissing as missing:
        return error_response(str(missing), 501)
    except (ValueError, TypeError) as bad_input:
        return error_response(f"Invalid request: {bad_input}")
    except OSError:
        return error_response("That file could not be read as an image.", 415)
    return JSONResponse(result)
