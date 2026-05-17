import os
import socket
import logging

from src.transport.rudp_socket import RUDPSocket
from .http_message import HTTPRequest, HTTPResponse

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
}


def _recv_http_request(rudp: RUDPSocket) -> bytes:
    """Accumulate chunks from the RUDP socket until a complete HTTP request
    is received (headers done + body matching Content-Length)."""
    buf = b""
    while True:
        chunk = rudp.recv(2048)
        if chunk == b"":
            break
        buf += chunk

        hdr_end = buf.find(b"\r\n\r\n")
        if hdr_end == -1:
            continue

        content_length = 0
        for line in buf[:hdr_end].decode(errors="replace").split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break

        body_start = hdr_end + 4
        if len(buf) >= body_start + content_length:
            break

    return buf


class HTTPServer:
    """A minimal HTTP/1.0 server built on top of RUDP (reliable UDP).

    Supports GET (static file serving) and POST (custom handlers or echo).
    Returns 200 OK or 404 Not Found as required by the lab spec.
    """

    def __init__(self, host="127.0.0.1", port=8080, webroot="www",
                 drop_prob=0.0, corrupt_prob=0.0):
        self.host = host
        self.port = port
        self.webroot = os.path.abspath(webroot)
        self.drop_prob = drop_prob
        self.corrupt_prob = corrupt_prob
        self.post_handlers: dict = {}
        self.running = False

    def register_post_handler(self, path, handler):
        """Register a callable ``handler(request) -> HTTPResponse`` for a
        POST path."""
        self.post_handlers[path] = handler

    # ------------------------------------------------------------------ 
    #  Main server loop                                                    
    # ------------------------------------------------------------------ 

    def start(self):
        self.running = True
        logger.info("HTTP Server listening on %s:%s", self.host, self.port)
        logger.info("Serving files from %s", self.webroot)

        while self.running:
            rudp = RUDPSocket(drop_prob=self.drop_prob, corrupt_prob=self.corrupt_prob)
            rudp.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rudp.bind((self.host, self.port))

            try:
                addr = rudp.accept()
                logger.info("Connection from %s", addr)

                raw = _recv_http_request(rudp)
                request = HTTPRequest.parse(raw)
                logger.info("%s %s", request.method, request.path)

                if request.method == "GET":
                    response = self._handle_get(request)
                elif request.method == "POST":
                    response = self._handle_post(request)
                else:
                    response = HTTPResponse(400, body=b"Bad Request")

                rudp.send(response.build())
                logger.info("-> %s %s", response.status_code, response.status_text)
                rudp.close()

            except Exception as e:
                logger.error("Error handling request: %s", e)
                try:
                    rudp.close()
                except Exception:
                    pass

    def serve_once(self):
        """Handle exactly one request then return. Useful for testing."""
        rudp = RUDPSocket(drop_prob=self.drop_prob, corrupt_prob=self.corrupt_prob)
        rudp.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rudp.bind((self.host, self.port))

        addr = rudp.accept()
        raw = _recv_http_request(rudp)
        request = HTTPRequest.parse(raw)

        if request.method == "GET":
            response = self._handle_get(request)
        elif request.method == "POST":
            response = self._handle_post(request)
        else:
            response = HTTPResponse(400, body=b"Bad Request")

        rudp.send(response.build())
        rudp.close()
        return request, response

    # ------------------------------------------------------------------ 
    #  Request handlers                                                    
    # ------------------------------------------------------------------ 

    def _handle_get(self, request: HTTPRequest) -> HTTPResponse:
        path = request.path
        if path == "/":
            path = "/index.html"

        file_path = os.path.normpath(os.path.join(self.webroot, path.lstrip("/")))

        if not file_path.startswith(self.webroot):
            return HTTPResponse(404, headers={"Connection": "close"},
                                body=b"Not Found")

        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                body = f.read()

            ext = os.path.splitext(file_path)[1].lower()
            content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
            headers = {"Content-Type": content_type, "Connection": "close"}
            return HTTPResponse(200, headers=headers, body=body)

        return HTTPResponse(404, headers={"Connection": "close"},
                            body=b"Not Found")

    def _handle_post(self, request: HTTPRequest) -> HTTPResponse:
        if request.path in self.post_handlers:
            return self.post_handlers[request.path](request)

        headers = {"Content-Type": "text/plain", "Connection": "close"}
        return HTTPResponse(200, headers=headers, body=request.body)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    server = HTTPServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped.")
