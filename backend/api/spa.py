"""static file serving for the built react app."""
from __future__ import annotations

from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles


async def index_missing(request):
    return HTMLResponse(
        "<h2>Frontend not built</h2><p>Run <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code> "
        "(or just <code>python run.py</code>, which does it for you). The API is running at /api.</p>")


class SPAStaticFiles(StaticFiles):
    """Serve static files, falling back to index.html for client-side SPA routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code == 404 and not path.startswith(("api/", "assets/")) and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise
