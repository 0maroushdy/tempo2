class HTTPRequest:
    """Represents an HTTP/1.0 request message."""

    def __init__(self, method, path, version="HTTP/1.0", headers=None, body=b""):
        self.method = method.upper()
        self.path = path
        self.version = version
        self.headers = headers or {}
        self.body = body if isinstance(body, bytes) else body.encode()

    def build(self) -> bytes:
        if self.body and "Content-Length" not in self.headers:
            self.headers["Content-Length"] = str(len(self.body))

        request_line = f"{self.method} {self.path} {self.version}\r\n"
        header_lines = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items())
        return (request_line + header_lines + "\r\n").encode() + self.body

    @classmethod
    def parse(cls, raw: bytes) -> "HTTPRequest":
        text = raw.decode(errors="replace") if isinstance(raw, bytes) else raw

        header_part, _, body_str = text.partition("\r\n\r\n")
        lines = header_part.split("\r\n")

        parts = lines[0].split(" ", 2)
        method = parts[0]
        path = parts[1] if len(parts) > 1 else "/"
        version = parts[2] if len(parts) > 2 else "HTTP/1.0"

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        return cls(method, path, version, headers, body_str.encode())

    def __repr__(self):
        return f"HTTPRequest({self.method} {self.path} {self.version})"


class HTTPResponse:
    """Represents an HTTP/1.0 response message."""

    STATUS_TEXTS = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    }

    def __init__(self, status_code=200, headers=None, body=b"", version="HTTP/1.0"):
        self.version = version
        self.status_code = status_code
        self.status_text = self.STATUS_TEXTS.get(status_code, "Unknown")
        self.headers = headers or {}
        self.body = body if isinstance(body, bytes) else body.encode()

    def build(self) -> bytes:
        if "Content-Length" not in self.headers:
            self.headers["Content-Length"] = str(len(self.body))

        status_line = f"{self.version} {self.status_code} {self.status_text}\r\n"
        header_lines = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items())
        return (status_line + header_lines + "\r\n").encode() + self.body

    @classmethod
    def parse(cls, raw: bytes) -> "HTTPResponse":
        text = raw.decode(errors="replace") if isinstance(raw, bytes) else raw

        header_part, _, body_str = text.partition("\r\n\r\n")
        lines = header_part.split("\r\n")

        parts = lines[0].split(" ", 2)
        version = parts[0] if parts else "HTTP/1.0"
        status_code = int(parts[1]) if len(parts) > 1 else 500

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        resp = cls(status_code, headers, body_str.encode(), version)
        if len(parts) > 2:
            resp.status_text = parts[2]
        return resp

    def __repr__(self):
        return f"HTTPResponse({self.status_code} {self.status_text})"
