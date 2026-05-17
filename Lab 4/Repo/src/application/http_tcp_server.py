import logging
import socket

from .http_message import HTTPRequest, HTTPResponse
from .http_server import HTTPServer

logger = logging.getLogger(__name__)


def _recv_http_request_from_tcp(conn: socket.socket) -> bytes:
    """Read a complete HTTP/1.0 request from a TCP connection."""
    conn.settimeout(5.0)
    buf = b""

    while True:
        chunk = conn.recv(2048)
        if not chunk:
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


class TCPHTTPServer(HTTPServer):
    """Browser-compatible HTTP server over TCP for the lab bonus."""

    def start(self):
        self.running = True
        logger.info("TCP HTTP Server listening on %s:%s", self.host, self.port)
        logger.info("Serving files from %s", self.webroot)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(5)
            server_sock.settimeout(1.0)

            while self.running:
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue

                with conn:
                    self._handle_tcp_connection(conn, addr)

    def serve_once(self):
        """Handle one TCP browser/client request then return."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(1)
            conn, addr = server_sock.accept()
            with conn:
                return self._handle_tcp_connection(conn, addr)

    def _handle_tcp_connection(self, conn: socket.socket, addr):
        logger.info("TCP connection from %s", addr)
        raw = _recv_http_request_from_tcp(conn)
        request = HTTPRequest.parse(raw)
        logger.info("%s %s", request.method, request.path)

        if request.method == "GET":
            response = self._handle_get(request)
        elif request.method == "POST":
            response = self._handle_post(request)
        else:
            response = HTTPResponse(400, body=b"Bad Request")

        conn.sendall(response.build())
        logger.info("-> %s %s", response.status_code, response.status_text)
        return request, response


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    server = TCPHTTPServer(host="127.0.0.1", port=8081)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped.")
