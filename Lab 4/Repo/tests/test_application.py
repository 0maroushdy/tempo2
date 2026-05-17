import unittest
import threading
import time
import os
import socket

from src.application.http_message import HTTPRequest, HTTPResponse
from src.application.http_server import HTTPServer
from src.application.http_client import HTTPClient
from src.application.http_tcp_server import TCPHTTPServer


WEBROOT = os.path.join(os.path.dirname(__file__), "..", "www")


class TestHTTPMessage(unittest.TestCase):
    """Unit tests for HTTP request/response parsing and building."""

    def test_build_and_parse_get_request(self):
        req = HTTPRequest("GET", "/index.html",
                          headers={"Host": "localhost:8080", "Connection": "close"})
        raw = req.build()

        parsed = HTTPRequest.parse(raw)
        self.assertEqual(parsed.method, "GET")
        self.assertEqual(parsed.path, "/index.html")
        self.assertEqual(parsed.version, "HTTP/1.0")
        self.assertEqual(parsed.headers["Host"], "localhost:8080")
        self.assertEqual(parsed.body, b"")

    def test_build_and_parse_post_request(self):
        body = b"username=alice&password=secret"
        req = HTTPRequest("POST", "/login",
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          body=body)
        raw = req.build()

        parsed = HTTPRequest.parse(raw)
        self.assertEqual(parsed.method, "POST")
        self.assertEqual(parsed.path, "/login")
        self.assertEqual(parsed.body, body)
        self.assertEqual(parsed.headers["Content-Length"], str(len(body)))

    def test_build_and_parse_200_response(self):
        resp = HTTPResponse(200,
                            headers={"Content-Type": "text/html"},
                            body=b"<h1>OK</h1>")
        raw = resp.build()

        parsed = HTTPResponse.parse(raw)
        self.assertEqual(parsed.status_code, 200)
        self.assertEqual(parsed.body, b"<h1>OK</h1>")
        self.assertEqual(parsed.headers["Content-Length"], str(len(b"<h1>OK</h1>")))

    def test_build_and_parse_404_response(self):
        resp = HTTPResponse(404, body=b"Not Found")
        raw = resp.build()

        parsed = HTTPResponse.parse(raw)
        self.assertEqual(parsed.status_code, 404)
        self.assertEqual(parsed.body, b"Not Found")


class TestHTTPEndToEnd(unittest.TestCase):
    """Integration tests: full HTTP request-response over RUDP."""

    def _run_server_once(self, server, errors):
        try:
            server.serve_once()
        except Exception as e:
            errors.append(e)

    def test_get_existing_file(self):
        """GET /index.html should return 200 OK with the file contents."""
        port = 9100
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient()
        resp = client.get("127.0.0.1", port, "/index.html")

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"RUDP HTTP", resp.body)
        self.assertEqual(resp.headers.get("Content-Type"), "text/html")

        t.join(timeout=10)
        self.assertFalse(t.is_alive())
        self.assertEqual(errors, [])

    def test_get_root_serves_index(self):
        """GET / should default to /index.html."""
        port = 9101
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient()
        resp = client.get("127.0.0.1", port, "/")

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"RUDP HTTP", resp.body)

        t.join(timeout=10)
        self.assertFalse(t.is_alive())

    def test_get_not_found(self):
        """GET for a missing file should return 404 Not Found."""
        port = 9102
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient()
        resp = client.get("127.0.0.1", port, "/does_not_exist.html")

        self.assertEqual(resp.status_code, 404)

        t.join(timeout=10)
        self.assertFalse(t.is_alive())

    def test_post_echo(self):
        """POST with a body should echo the body back (default handler)."""
        port = 9103
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient()
        payload = b"hello from the client"
        resp = client.post("127.0.0.1", port, "/echo", body=payload)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, payload)

        t.join(timeout=10)
        self.assertFalse(t.is_alive())

    def test_get_with_simulated_loss(self):
        """GET should succeed even with packet loss and corruption."""
        port = 9104
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT,
                            drop_prob=0.2, corrupt_prob=0.1)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient(drop_prob=0.2, corrupt_prob=0.1)
        resp = client.get("127.0.0.1", port, "/index.html")

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"RUDP HTTP", resp.body)

        t.join(timeout=15)
        self.assertFalse(t.is_alive())

    def test_post_with_simulated_loss(self):
        """POST should succeed even with packet loss and corruption."""
        port = 9105
        server = HTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT,
                            drop_prob=0.2, corrupt_prob=0.1)
        errors = []

        t = threading.Thread(target=self._run_server_once, args=(server, errors), daemon=True)
        t.start()
        time.sleep(0.1)

        client = HTTPClient(drop_prob=0.2, corrupt_prob=0.1)
        payload = b"data with simulated loss"
        resp = client.post("127.0.0.1", port, "/echo", body=payload)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, payload)

        t.join(timeout=15)
        self.assertFalse(t.is_alive())


class TestTCPBonus(unittest.TestCase):
    """Bonus integration: browser-style HTTP over standard TCP."""

    def test_tcp_browser_style_get(self):
        port = 9200
        server = TCPHTTPServer(host="127.0.0.1", port=port, webroot=WEBROOT)
        errors = []

        def run_server_once():
            try:
                server.serve_once()
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=run_server_once, daemon=True)
        t.start()
        time.sleep(0.1)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.sendall(
                b"GET / HTTP/1.0\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            response = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response += chunk

        self.assertIn(b"HTTP/1.0 200 OK", response)
        self.assertIn(b"Hello from the RUDP HTTP/1.0 Server!", response)
        t.join(timeout=5)
        self.assertFalse(t.is_alive())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
