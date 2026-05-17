import logging

from src.transport.rudp_socket import RUDPSocket
from .http_message import HTTPRequest, HTTPResponse

logger = logging.getLogger(__name__)


def _recv_http_response(rudp: RUDPSocket) -> bytes:
    """Accumulate chunks from the RUDP socket until a complete HTTP response
    is received (headers done + body matching Content-Length)."""
    buf = b""
    while True:
        try:
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
        except TimeoutError:
            break

    return buf


class HTTPClient:
    """A minimal HTTP/1.0 client built on top of RUDP (reliable UDP).

    Supports GET and POST methods as required by the lab spec.
    """

    def __init__(self, drop_prob=0.0, corrupt_prob=0.0):
        self.drop_prob = drop_prob
        self.corrupt_prob = corrupt_prob

    def get(self, host: str, port: int, path: str = "/") -> HTTPResponse:
        return self._send_request("GET", host, port, path)

    def post(self, host: str, port: int, path: str = "/",
             body: bytes = b"", content_type: str = "text/plain") -> HTTPResponse:
        extra_headers = {"Content-Type": content_type}
        return self._send_request("POST", host, port, path,
                                  headers=extra_headers, body=body)

    def _send_request(self, method, host, port, path,
                      headers=None, body=b"") -> HTTPResponse:
        rudp = RUDPSocket(drop_prob=self.drop_prob, corrupt_prob=self.corrupt_prob)

        try:
            rudp.connect((host, port))

            req_headers = {
                "Host": f"{host}:{port}",
                "Connection": "close",
            }
            if headers:
                req_headers.update(headers)

            if body:
                if isinstance(body, str):
                    body = body.encode()
                req_headers["Content-Length"] = str(len(body))

            request = HTTPRequest(method, path, headers=req_headers, body=body)
            logger.info("%s %s:%s%s", method, host, port, path)
            rudp.send(request.build())

            raw_response = _recv_http_response(rudp)
            response = HTTPResponse.parse(raw_response)
            logger.info("-> %s %s", response.status_code, response.status_text)

            rudp.close()
            return response

        except Exception:
            try:
                rudp.close()
            except Exception:
                pass
            raise


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    client = HTTPClient()

    if len(sys.argv) > 1 and sys.argv[1] == "post":
        data = sys.argv[2] if len(sys.argv) > 2 else "Hello, Server!"
        resp = client.post("127.0.0.1", 8080, "/echo", body=data.encode())
    else:
        req_path = sys.argv[1] if len(sys.argv) > 1 else "/"
        resp = client.get("127.0.0.1", 8080, req_path)

    print(f"Status: {resp.status_code} {resp.status_text}")
    print(f"Headers: {resp.headers}")
    print(f"Body:\n{resp.body.decode(errors='replace')}")
