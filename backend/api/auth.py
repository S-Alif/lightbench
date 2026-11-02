"""optional password for devices that reach the app over the network.

The computer that runs Lightbench never has to log in. Anyone else must enter the password once,
which gives their browser a random session cookie. Only /api/ is guarded: the web page itself holds
no data, so the login screen can load before anyone has signed in.
"""
from __future__ import annotations

import asyncio
import hmac
import secrets
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from .. import config
from .helpers import is_local_request

COOKIE = "lightbench_session"
SESSION_SECONDS = 30 * 24 * 3600
MAX_FAILURES = 5              # wrong passwords allowed ...
FAILURE_WINDOW = 300          # ... within this many seconds, then the address is locked out for the rest of it

_sessions: dict[str, float] = {}            # token -> expiry time (kept in memory, so a restart signs everyone out)
_failures: dict[str, list[float]] = {}      # client address -> times of recent wrong passwords


def password_matches(given: str) -> bool:
    return bool(config.PASSWORD) and hmac.compare_digest(given.encode(), config.PASSWORD.encode())


def has_valid_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE)
    expiry = _sessions.get(token) if token else None
    if expiry is None:
        return False
    if expiry < time.time():
        _sessions.pop(token, None)
        return False
    return True


def is_trusted(request: Request) -> bool:
    """true when no password is needed or this request already proved it knows it."""
    return not config.PASSWORD or is_local_request(request) or has_valid_session(request)


def seconds_locked(address: str) -> int:
    """how long this address must wait before trying again (0 = not locked)."""
    now = time.time()
    recent = [moment for moment in _failures.get(address, []) if now - moment < FAILURE_WINDOW]
    _failures[address] = recent
    if len(recent) < MAX_FAILURES:
        return 0
    return int(FAILURE_WINDOW - (now - recent[0])) + 1


class PasswordGate:
    """refuses /api/ requests from other devices until they have logged in."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        if scope["type"] == "http" and config.PASSWORD and path.startswith("/api/") and not path.startswith("/api/auth/"):
            if not is_trusted(Request(scope)):
                response = JSONResponse({"error": "Password required"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def auth_status(request):
    return JSONResponse({"required": bool(config.PASSWORD), "authenticated": is_trusted(request),
                         "local": is_local_request(request)})


async def login(request):
    address = request.client.host if request.client else "unknown"
    wait = seconds_locked(address)
    if wait:
        return JSONResponse({"error": f"Too many wrong passwords. Try again in {wait} seconds."}, status_code=429)
    try:
        body = await request.json()
        given = str(body.get("password", "")) if isinstance(body, dict) else ""
    except ValueError:
        given = ""
    if config.PASSWORD and not password_matches(given):
        _failures.setdefault(address, []).append(time.time())
        await asyncio.sleep(0.5)               # makes guessing slower even before the lockout
        return JSONResponse({"error": "Wrong password"}, status_code=401)
    response = JSONResponse({"ok": True})
    if config.PASSWORD:
        token = secrets.token_urlsafe(32)
        _sessions[token] = time.time() + SESSION_SECONDS
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", path="/")
    return response


async def logout(request):
    _sessions.pop(request.cookies.get(COOKIE, ""), None)
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE, path="/")
    return response
