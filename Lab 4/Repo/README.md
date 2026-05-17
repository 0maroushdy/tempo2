# Networks Lab 4

## Overview

This project implements reliable data transfer over UDP and supports HTTP/1.0 on top of it.

The implementation is divided into:
- **Transport layer (`src/transport`)**: custom reliable UDP (RUDP) with stop-and-wait, retransmission, checksums, packet loss/corruption simulation, handshake flags, and timeouts.
- **Application layer (`src/application`)**: HTTP request/response parsing, HTTP client/server over RUDP, and a TCP HTTP server for browser bonus validation.

---

## Lab Requirements Coverage

### Core Requirements
- Reliable transfer over UDP using stop-and-wait.
- Checksum calculation and verification for packet integrity.
- Packet loss and corruption simulation.
- Retransmission with timeout when ACK is missing.
- Sequence numbers, duplicate handling, and basic connection control flags (SYN, SYNACK, ACK, FIN).
- HTTP/1.0 support on top of transport layer.
- GET and POST methods.
- Required status responses: **200 OK** and **404 Not Found**.

### Bonus Requirement
- Browser-compatible communication using standard TCP HTTP server:
  - `src/application/http_tcp_server.py`
- This is added to demonstrate valid browser-to-server HTTP communication and Wireshark capture.

---

## Project Structure

```text
src/
  transport/
    checksum.py
    network_simulation.py
    packet.py
    rudp_socket.py
  application/
    http_message.py
    http_client.py
    http_server.py
    http_tcp_server.py
tests/
  test_transport.py
  test_application.py
www/
  index.html
  about.html
```

---

## How to Run

### 1) Run HTTP over RUDP (Lab Core)

Terminal 1:
```bash
python -m src.application.http_server
```

Terminal 2:
```bash
python -m src.application.http_client /
python -m src.application.http_client /nonexistent.html
python -m src.application.http_client post "Hello from client"
```

What you should see:
- `GET /` returns `200 OK`
- Missing file returns `404 Not Found`
- POST returns `200 OK` with echoed body

---

### 2) Run Browser Bonus (HTTP over TCP)

Start bonus server:
```bash
python -m src.application.http_tcp_server
```

Open browser:
- `http://127.0.0.1:8081/`
- `http://127.0.0.1:8081/about.html`
- `http://127.0.0.1:8081/nonexistent.html`

---

## Run Tests

Run all tests:
```bash
python -m unittest discover -s tests -v
```

Current result:
- **16 tests passed** (transport + application + TCP bonus test)

---


## Notes

- The core lab implementation remains on custom reliable UDP transport.
- The TCP server is included only to satisfy the browser communication bonus requirement.
