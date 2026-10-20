"""Web layer (Starlette). Serves the built React app and a small JSON API."""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Mount, Route

from .api.router import api_routes
from .api.spa import SPAStaticFiles, index_missing
from .config import STATIC_DIR

routes = list(api_routes)

if (STATIC_DIR / "index.html").exists():
    routes.append(Mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True)))
else:
    routes.append(Route("/{path:path}", index_missing))

app = Starlette(routes=routes)
