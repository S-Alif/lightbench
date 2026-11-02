import asyncio
import json
import unittest
from unittest import mock

from backend import config
from backend.api import auth
from backend.main import app


def call(method, path, *, client="192.168.0.20", cookie=None, body=None):
    """send one request straight into the app and return (status, parsed json, set-cookie header)"""
    headers = [(b"content-type", b"application/json")]
    if cookie:
        headers.append((b"cookie", f"{auth.COOKIE}={cookie}".encode()))
    scope = {"type": "http", "method": method, "path": path, "raw_path": path.encode(), "query_string": b"",
             "headers": headers, "client": (client, 5000), "server": ("testserver", 80), "scheme": "http"}
    payload = json.dumps(body).encode() if body is not None else b""
    sent = []

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    start = next(message for message in sent if message["type"] == "http.response.start")
    data = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    cookie_header = next((value.decode() for name, value in start["headers"] if name == b"set-cookie"), None)
    return start["status"], (json.loads(data) if data else None), cookie_header


class PasswordTests(unittest.TestCase):
    def setUp(self):
        self.patches = [mock.patch.object(config, "PASSWORD", "abcd-2345"), mock.patch("asyncio.sleep", new=mock.AsyncMock())]
        for patch in self.patches:
            patch.start()
        auth._sessions.clear()
        auth._failures.clear()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def test_other_devices_are_refused_until_login(self):
        self.assertEqual(call("GET", "/api/jobs")[0], 401)

    def test_this_computer_needs_no_password(self):
        self.assertEqual(call("GET", "/api/auth/status", client="127.0.0.1")[1]["authenticated"], True)
        self.assertNotEqual(call("GET", "/api/jobs", client="127.0.0.1")[0], 401)

    def test_wrong_password_is_rejected(self):
        status, _, cookie = call("POST", "/api/auth/login", body={"password": "nope"})
        self.assertEqual(status, 401)
        self.assertIsNone(cookie)

    def test_right_password_gives_a_working_cookie(self):
        status, _, cookie_header = call("POST", "/api/auth/login", body={"password": "abcd-2345"})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", cookie_header)
        token = cookie_header.split(";")[0].split("=", 1)[1]
        self.assertNotEqual(call("GET", "/api/jobs", cookie=token)[0], 401)
        self.assertEqual(call("GET", "/api/auth/status", cookie=token)[1]["authenticated"], True)

    def test_logout_ends_the_session(self):
        _, _, cookie_header = call("POST", "/api/auth/login", body={"password": "abcd-2345"})
        token = cookie_header.split(";")[0].split("=", 1)[1]
        call("POST", "/api/auth/logout", cookie=token)
        self.assertEqual(call("GET", "/api/jobs", cookie=token)[0], 401)

    def test_too_many_wrong_passwords_lock_the_address(self):
        for _ in range(auth.MAX_FAILURES):
            call("POST", "/api/auth/login", body={"password": "nope"})
        self.assertEqual(call("POST", "/api/auth/login", body={"password": "abcd-2345"})[0], 429)
        # another device is not affected
        self.assertEqual(call("POST", "/api/auth/login", client="192.168.0.99", body={"password": "abcd-2345"})[0], 200)

    def test_page_and_login_endpoints_stay_open(self):
        self.assertEqual(call("GET", "/api/auth/status")[0], 200)
        self.assertEqual(call("GET", "/api/auth/status")[1]["required"], True)

    def test_no_password_means_nothing_is_guarded(self):
        with mock.patch.object(config, "PASSWORD", None):
            self.assertNotEqual(call("GET", "/api/jobs")[0], 401)
            self.assertEqual(call("GET", "/api/auth/status")[1]["required"], False)


if __name__ == "__main__":
    unittest.main()
