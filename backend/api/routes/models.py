"""GET /api/models, the built-in and custom weights found in the models folder."""
from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from ...config import MODELS_DIR
from ...core.models import registry


def _models_listing() -> dict:
    try:
        from ...core.models import loader
        spec_fn = loader.spec
    except ImportError:
        spec_fn = None
    return {"dir": str(MODELS_DIR.resolve()), "models": registry.list_models(spec_fn)}


async def list_models(request):
    # inspecting a custom .pth reads the whole file, so keep it off the event loop
    return JSONResponse(await run_in_threadpool(_models_listing))
