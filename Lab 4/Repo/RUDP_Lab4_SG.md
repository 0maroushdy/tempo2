# CC451 – Computer Networks Lab 4: RUDP Study Guide
> Reliable UDP · HTTP/1.0 · Stop-and-Wait · Checksums · Connection Control Flags

---

## Table of Contents
1. [Why RUDP? The UDP vs. TCP Problem](#1-why-rudp-the-udp-vs-tcp-problem)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Core Concept: The Packet](#3-core-concept-the-packet)
4. [Core Concept: Checksum (Error Detection)](#4-core-concept-checksum-error-detection)
5. [Core Concept: Stop-and-Wait (rdt 3.0)](#5-core-concept-stop-and-wait-rdt-30)
6. [Core Concept: Connection Lifecycle (Flags)](#6-core-concept-connection-lifecycle-flags)
7. [Core Concept: Network Simulation](#7-core-concept-network-simulation)
8. [Application Layer: HTTP/1.0](#8-application-layer-http10)
9. [Code Walkthrough by File](#9-code-walkthrough-by-file)
10. [Browser Gateway (Bonus)](#10-browser-gateway-bonus)
11. [Expected TA Questions — Lab Specific](#11-expected-ta-questions--lab-specific)
12. [Expected TA Questions — Lecture Concepts](#12-expected-ta-questions--lecture-concepts)

---

## 1. Why RUDP? The UDP vs. TCP Problem

### UDP: Fast but Unreliable
UDP (`SOCK_DGRAM`) is a **best-effort** transport protocol. It provides:
- No connection setup (connectionless)
- No delivery guarantee (packets can be **lost**)
- No ordering guarantee (packets can arrive **out of order**)
- No duplication protection (packets can be **duplicated**)
- No flow control

### TCP: Reliable but Heavy
TCP adds all the reliability mechanisms, but it's implemented inside the kernel — you can't inspect or modify it easily.

### The Lab Goal
**Simulate TCP-like reliability on top of raw UDP — in user space (Python).**  
This is the exact problem the textbook solves by building `rdt1.0 → rdt2.x → rdt3.0`.

```
Application (HTTP)
      ↓
   RUDPSocket          ← Our custom reliable layer
      ↓
  UDP Socket           ← OS kernel, no guarantees
      ↓
   Network
```

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
│                                                                 │
│   HTTPClient ──────────────────────────────── HTTPServer        │
│       │                                           │             │
│  HTTPRequest / HTTPResponse (http_message.py)     │             │
└───────┼───────────────────────────────────────────┼─────────────┘
        │                                           │
┌───────┼───────────────────────────────────────────┼─────────────┐
│       │          Transport Layer (RUDP)            │             │
│  RUDPSocket.connect()                    RUDPSocket.accept()     │
│  RUDPSocket.send()                       RUDPSocket.recv()       │
│  RUDPSocket.close()                      RUDPSocket.close()      │
│       │                                           │             │
│  Packet.pack() ──────────────────────── Packet.unpack()         │
│  calculate_checksum()                    verify checksum         │
│  simulate_loss() / corrupt_packet()     handle corruption        │
└───────────────────────────────────────────────────────────────┘
        │                                           │
        └─────────── UDP (SOCK_DGRAM) ──────────────┘

BONUS: Browser → TCP → BrowserGateway → RUDP → HTTPServer
```

### File Map
| File | Layer | Purpose |
|------|-------|---------|
| `transport/packet.py` | Transport | Packet structure, pack/unpack, checksum integration |
| `transport/checksum.py` | Transport | 16-bit one's complement checksum |
| `transport/network_simulation.py` | Transport | Simulate loss & bit corruption |
| `transport/rudp_socket.py` | Transport | Main RUDP socket (connect, accept, send, recv, close) |
| `application/http_message.py` | Application | HTTPRequest / HTTPResponse parsing & building |
| `application/http_server.py` | Application | HTTP server over RUDP |
| `application/http_client.py` | Application | HTTP client over RUDP |
| `application/browser_gateway.py` | Bonus | TCP→RUDP bridge for real browsers |

---

## 3. Core Concept: The Packet

### Packet Header Structure
The header is packed using Python's `struct` module with the format `!IIBH`:

| Field | Type | Size | Purpose |
|-------|------|------|---------|
| `seq_num` | `I` (uint32) | 4 bytes | Sequence number |
| `ack_num` | `I` (uint32) | 4 bytes | Acknowledgment number |
| `flags` | `B` (uint8) | 1 byte | Control flags (SYN/ACK/FIN) |
| `checksum` | `H` (uint16) | 2 bytes | 16-bit checksum |
| **Total header** | | **11 bytes** | |
| `data` | bytes | variable | Payload |

The `!` prefix means **network byte order** (big-endian). This is important for interoperability — the textbook always uses big-endian for headers.

### Flags (bitmask, 1 byte)
```python
SYN    = 0b0001   # 1  – Synchronize (start connection)
ACK    = 0b0010   # 2  – Acknowledge
FIN    = 0b0100   # 4  – Finish (close connection)
SYNACK = SYN|ACK  # 3  – SYN + ACK combined (server response to SYN)
```

### Packing & Checksum
```python
def pack(self) -> bytes:
    # Step 1: Pack header with checksum field = 0
    header_without_checksum = struct.pack('!IIBH', seq_num, ack_num, flags, 0)
    # Step 2: Compute checksum over header+data
    self.checksum = calculate_checksum(header_without_checksum + self.data)
    # Step 3: Repack with real checksum
    final_header = struct.pack('!IIBH', seq_num, ack_num, flags, self.checksum)
    return final_header + self.data
```

**Why zero out checksum during calculation?** Because the checksum field is part of the bytes being checksummed. By setting it to zero first, the same formula works both to compute and to verify (the result should be 0xFFFF if you include the received checksum in the calculation — this is the standard UDP/IP trick).

### Unpacking & Verification
```python
@classmethod
def unpack(cls, raw_bytes):
    # Extract header
    seq_num, ack_num, flags, received_checksum = struct.unpack('!IIBH', raw_bytes[:11])
    data = raw_bytes[11:]
    # Recalculate with checksum=0 in its slot
    header_zeroed = struct.pack('!IIBH', seq_num, ack_num, flags, 0)
    calculated = calculate_checksum(header_zeroed + data)
    if received_checksum != calculated:
        raise ValueError("Checksum verification failed. Corrupt packet.")
```
If corrupt → **raise ValueError** → caller discards the packet → sender times out → **retransmits**.

---

## 4. Core Concept: Checksum (Error Detection)

### One's Complement Checksum (Internet Checksum)
The same algorithm used by UDP, TCP, and IP in the real internet:

```python
def calculate_checksum(data: bytes) -> int:
    if len(data) % 2 == 1:
        data += b'\0'          # Pad to even length

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]   # 16-bit word
        checksum += word
        checksum = (checksum & 0xffff) + (checksum >> 16)  # carry wrap

    return ~checksum & 0xffff   # one's complement
```

### Step-by-Step
1. **Treat data as a sequence of 16-bit words**
2. **Sum all words** (can overflow 16 bits — add carries back to the sum)
3. **Take the bitwise NOT** (one's complement)

**Verification:** When the receiver recalculates the checksum over the entire received packet (including the checksum field), the result should be `0x0000` (or equivalently, `0xFFFF` depending on variant). Any deviation → corruption detected.

### Why can't checksum detect all errors?
If two opposite bit flips happen in the same column of a 16-bit word pair, they cancel out → undetected. Checksum provides **error detection**, not correction.

### What's included in the checksum here?
The **entire packet** (header with checksum=0 zeroed out + data). This covers:
- Sequence and ACK numbers
- Flags
- Payload data

---

## 5. Core Concept: Stop-and-Wait (rdt 3.0)

### What is Stop-and-Wait?
**Send one packet → wait for ACK → only then send the next.**  
This is `rdt 3.0` from the textbook — the simplest reliable protocol.

### Why is it called rdt 3.0?
The textbook builds reliability incrementally:
- **rdt 1.0** – Perfect channel (no loss, no corruption)
- **rdt 2.0** – Handles corruption via checksum + ACK/NAK
- **rdt 2.1** – Handles duplicate ACKs with sequence numbers
- **rdt 2.2** – NAK-free (uses ACK with sequence number instead of NAK)
- **rdt 3.0** – Handles **loss** with timeouts + retransmission

### Lab Implementation: `_reliable_send()`
```python
def _reliable_send(self, packet, expected_flags=ACK, is_synack=False):
    packet_bytes = packet.pack()
    expected_ack_num = packet.seq_num + max(len(packet.data), 1)

    for _ in range(50):          # Max 50 retransmission attempts
        self._send_raw(packet_bytes)    # Send (may be dropped/corrupted)

        deadline = time.time() + 0.05  # 50ms timeout
        while time.time() < deadline:
            try:
                self.sock.settimeout(max(0.001, deadline - time.time()))
                raw_ack, _ = self.sock.recvfrom(2048)
                ack_pkt = Packet.unpack(raw_ack)  # May raise ValueError if corrupt

                if ack_pkt.flags == expected_flags:
                    if ack_pkt.ack_num == expected_ack_num:
                        return   # ✅ Got the correct ACK
                    # Wrong ACK number → ignore, keep waiting
            except socket.timeout:
                break            # Timeout → retransmit
            except Exception:
                time.sleep(0.005)  # Corrupt → wait briefly, retry recv

    raise ConnectionError("Maximum retransmission limit exceeded")
```

### Key mechanisms in the code:
| Mechanism | Where | How |
|-----------|-------|-----|
| **Retransmit on timeout** | `_reliable_send` | 50ms timeout, up to 50 retries |
| **Discard corrupt packets** | `Packet.unpack()` | Raises `ValueError`, caught silently |
| **ACK number check** | `_reliable_send` | `ack_num == seq_num + len(data)` |
| **Duplicate detection** | `recv()` | Check `pkt.seq_num == self.expected_seq` |
| **Sequence number** | `RUDPSocket` | Starts random 1–1000, increments by data length |

### What happens when an ACK is lost?
1. Sender doesn't receive ACK within 50ms
2. Sender retransmits the **same packet** with the **same sequence number**
3. Receiver gets duplicate → compares `pkt.seq_num != self.expected_seq` → sends ACK again but **discards the data** (no duplicate delivery to upper layer)

### What is the ACK number?
`ack_num = seq_num + max(len(data), 1)`  
For data packets: ACK num = next expected byte.  
For control packets (no data): `max(0, 1) = 1`, so control packet advances by 1.

---

## 6. Core Concept: Connection Lifecycle (Flags)

### Three-Way Handshake (connect/accept)

```
CLIENT                          SERVER
  |                               |
  |──── SYN (seq=X) ─────────────►|   client.connect()
  |                               |   server sees SYN → saves expected_seq = X+1
  |◄─── SYNACK (seq=Y, ack=X+1) ─|   server._reliable_send(SYNACK)
  |                               |
  |──── ACK (seq=X+1, ack=Y+1) ──►|   client sends final ACK
  |                               |
  |═══════ DATA TRANSFER ══════════|
```

**Code: client side (`connect`)**
```python
def connect(self, address):
    self.target_addr = address
    syn_pkt = Packet(self.seq_num, 0, SYN)
    self._reliable_send(syn_pkt, expected_flags=SYNACK)
    self.seq_num += 1
```

**Code: server side (`accept`)**
```python
def accept(self, timeout=10.0):
    raw_data, addr = self.sock.recvfrom(2048)
    pkt = Packet.unpack(raw_data)
    if pkt.flags == SYN:
        self.target_addr = addr
        self.expected_seq = pkt.seq_num + 1
        synack_pkt = Packet(self.seq_num, self.expected_seq, SYNACK)
        self._reliable_send(synack_pkt, expected_flags=ACK, is_synack=True)
        self.seq_num += 1
        return addr
```

### Data Transfer (send/recv)

```
SENDER                          RECEIVER
  |──── DATA (seq=N, len=L) ────►|
  |                              |  checks seq_num == expected_seq
  |◄─── ACK (ack=N+L) ──────────|  sends ACK 3x (burst to survive drop)
  |                              |  returns data to application
  |──── DATA (seq=N+L, ...) ────►|
```

**Burst ACK trick:** The receiver sends 3 ACKs immediately to reduce the chance that all copies get dropped:
```python
for _ in range(3):
    self._send_raw(ack_pkt.pack())
```

### Connection Teardown (close/FIN)

```
CLOSER                          OTHER SIDE
  |──── FIN (seq=M) ────────────►|
  |◄─── ACK (ack=M+1) ──────────|
  |  (waits 100ms for stray pkts)|
  |  sock.close()                |
```

```python
def close(self):
    fin_pkt = Packet(self.seq_num, 0, FIN)
    try:
        self._reliable_send(fin_pkt, expected_flags=ACK)
    except ConnectionError:
        pass
    # Wait 100ms for any stray packets, then close socket
    deadline = time.time() + 0.1
    # ... drain loop ...
    self.sock.close()
```

Note: This is a **simplified** teardown (not the full TCP 4-way FIN/FIN-ACK). The lab spec doesn't require full TCP-equivalent teardown.

---

## 7. Core Concept: Network Simulation

### Packet Loss Simulation
```python
def simulate_loss(drop_probability: float) -> bool:
    return random.random() < drop_probability
```
Called in `_send_raw()`. If `True`, the packet is silently not sent. The sender will time out and retransmit.

### Packet Corruption Simulation
```python
def corrupt_packet(packet_bytes: bytes) -> bytes:
    byte_list = bytearray(packet_bytes)
    target_byte_index = random.randint(0, len(byte_list) - 1)
    byte_list[target_byte_index] ^= 1   # Flip the LSB of a random byte
    return bytes(byte_list)
```
Flips a single bit in a random byte. When the receiver runs `Packet.unpack()`, the checksum won't match → `ValueError` raised → packet discarded → sender retransmits after timeout.

### `_send_raw()` — Both Applied Together
```python
def _send_raw(self, raw_bytes: bytes):
    if simulate_loss(self.drop_prob):
        return                                  # Drop silently
    if simulate_loss(self.corrupt_prob):
        raw_bytes = corrupt_packet(raw_bytes)   # Corrupt then send
    self.sock.sendto(raw_bytes, self.target_addr)
```

---

## 8. Application Layer: HTTP/1.0

### HTTP/1.0 vs HTTP/1.1
| Feature | HTTP/1.0 | HTTP/1.1 |
|---------|----------|----------|
| Connections | **One request per connection** | Persistent (keep-alive) |
| Mandatory headers | None | `Host` required |
| Chunked encoding | No | Yes |
| Default behavior | Close after response | Keep-alive |

The lab uses **HTTP/1.0** because it's simpler: one connection = one request/response cycle. This maps cleanly to one RUDP connect/send/recv/close cycle.

### HTTP Message Format
```
[Request Line]    GET /index.html HTTP/1.0\r\n
[Headers]         Host: 127.0.0.1:8080\r\n
                  Connection: close\r\n
[Blank Line]      \r\n
[Body]            (empty for GET)
```

```
[Status Line]     HTTP/1.0 200 OK\r\n
[Headers]         Content-Type: text/html\r\n
                  Content-Length: 542\r\n
[Blank Line]      \r\n
[Body]            <html>...</html>
```

### HTTPRequest.build() & parse()
```python
def build(self) -> bytes:
    request_line = f"{self.method} {self.path} {self.version}\r\n"
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items())
    return (request_line + header_lines + "\r\n").encode() + self.body
```

Parse splits on `\r\n\r\n` to separate headers from body, then parses the request line and header key-values.

### Why `\r\n`?
HTTP spec (RFC 7230) requires CRLF (`\r\n = 0x0D 0x0A`) as line delimiter. Using just `\n` is a common source of bugs.

### Content-Length Header
Critical for knowing when a message ends over a stream:
- Sender sets it based on `len(body)`
- Receiver reads until it has `header_end + 4 + Content-Length` bytes

Without it, the receiver doesn't know if data transfer is complete:
```python
hdr_end = buf.find(b"\r\n\r\n")
# ...
body_start = hdr_end + 4
if len(buf) >= body_start + content_length:
    break
```

### HTTP Methods (lab: GET + POST)
**GET:** Retrieve a resource. No body. Server looks up file → 200 OK or 404 Not Found.  
**POST:** Send data to server. Body present. Server echoes back (or custom handler).

### Status Codes (lab: 200 + 404)
| Code | Text | When |
|------|------|------|
| 200 | OK | File found, request succeeded |
| 404 | Not Found | File doesn't exist |
| 400 | Bad Request | Unsupported method |
| 500 | Internal Server Error | Unexpected crash |

---

## 9. Code Walkthrough by File

### `checksum.py` — The Math
```python
# For each 16-bit word in the data:
word = (data[i] << 8) + data[i + 1]
checksum += word
checksum = (checksum & 0xffff) + (checksum >> 16)  # end-around carry
return ~checksum & 0xffff
```
The end-around carry wraps any overflow back into the 16-bit result. Final NOT gives the one's complement.

---

### `packet.py` — The PDU
- `HEADER_FORMAT = '!IIBH'` → `!` = big-endian, `I`=uint32, `I`=uint32, `B`=uint8, `H`=uint16
- `HEADER_SIZE = struct.calcsize('!IIBH')` → 11 bytes
- `pack()` → zero checksum → compute → repack with real checksum
- `unpack()` → extract header → recompute checksum → raise if mismatch

---

### `network_simulation.py` — Chaos Injection
- `simulate_loss(prob)` → probabilistic drop
- `corrupt_packet(bytes)` → random bit flip using XOR

---

### `rudp_socket.py` — The Core Engine

**Initialization:**
```python
self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Raw UDP
self.seq_num = random.randint(1, 1000)   # Random ISN (like TCP)
self.expected_seq = 0
```

**`_send_raw()`** — applies loss/corruption before actual `sendto()`

**`_reliable_send()`** — stop-and-wait loop:
- Send → set 50ms timeout → wait for correct ACK
- If timeout → retransmit (up to 50 times)
- If corrupt ACK → caught silently, loop continues

**`connect()`** — SYN → wait for SYNACK → send final ACK

**`accept()`** — wait for SYN → send SYNACK → wait for final ACK

**`send(data)`** — chunks data into 1024-byte pieces, calls `_reliable_send` for each:
```python
for i in range(0, len(data), 1024):
    chunk = data[i:i+1024]
    pkt = Packet(self.seq_num, 0, 0, chunk)   # flags=0 = pure data
    self._reliable_send(pkt, expected_flags=ACK)
    self.seq_num += len(chunk)
```

**`recv(bufsize)`** — blocks until a packet arrives with the expected seq_num:
```python
if pkt.seq_num == self.expected_seq:
    for _ in range(3): self._send_raw(ack_pkt.pack())  # burst ACK
    self.expected_seq = ack_num
    return pkt.data
else:
    self._send_raw(ack_pkt.pack())   # re-ACK old packet (duplicate)
```

**`close()`** — sends FIN, waits for ACK, drains for 100ms, calls `sock.close()`

---

### `http_server.py` — Request Handling Loop
```python
while self.running:
    rudp = RUDPSocket(...)      # Fresh socket each connection (HTTP/1.0)
    rudp.bind((host, port))
    addr = rudp.accept()        # Wait for SYN
    raw = _recv_http_request(rudp)
    request = HTTPRequest.parse(raw)

    if request.method == "GET":
        response = self._handle_get(request)
    elif request.method == "POST":
        response = self._handle_post(request)

    rudp.send(response.build())
    rudp.close()
```

**`_handle_get()`**: 
- Resolve path to file in `www/` directory
- Path traversal protection: `os.path.normpath` + `startswith(webroot)` check
- Read file → 200 OK with Content-Type, or 404 if missing

**`_handle_post()`**:
- Check registered handlers → otherwise echo body back with 200 OK

---

### `http_client.py` — Request Lifecycle
```python
def request(self, method, host, port, path, headers=None, body=b''):
    rudp = RUDPSocket(...)
    rudp.connect((host, port))         # SYN handshake
    request = HTTPRequest(method, path, headers=..., body=body)
    rudp.send(request.build())         # Send HTTP bytes over RUDP
    raw_response = _recv_http_response(rudp)
    response = HTTPResponse.parse(raw_response)
    rudp.close()                       # FIN teardown
    return response
```

---

## 10. Browser Gateway (Bonus)

### Why is a gateway needed?
Real browsers speak **TCP**. Our server speaks **RUDP over UDP**. They are incompatible at the socket level. The gateway bridges them.

```
Browser (Chrome) ──TCP──► BrowserGateway ──RUDP/UDP──► HTTPServer
                            listens :8080              listens :9090
```

### How it works
1. `BrowserGateway` creates a **TCP server socket** (`SOCK_STREAM`) on port 8080
2. For each browser connection:
   - Read the full HTTP request from TCP
   - Create an `HTTPClient` (RUDP) and forward the request to port 9090
   - Get the response back over RUDP
   - Write the response back to the browser over TCP
3. Each browser request spawns a new `threading.Thread`

```python
def _handle_client(self, conn, addr):
    raw_request = self._recv_http_request_from_tcp(conn)
    request = HTTPRequest.parse(raw_request)
    client = HTTPClient(...)
    response = client.request(request.method, rudp_host, rudp_port, request.path, ...)
    conn.sendall(response.build())
```

### Why threading?
The browser sends multiple requests (HTML + CSS + favicon). Each needs a separate connection. Threads allow concurrent handling. (Though the RUDP server is still sequential — one at a time.)

---

## 11. Expected TA Questions — Lab Specific

### Q: What does RUDP stand for and what does it do?
**A:** Reliable UDP. It's a custom protocol implemented in user space that adds reliability mechanisms (checksums, retransmission, sequence numbers, connection flags) on top of raw UDP sockets, making UDP behave like a simplified TCP.

---

### Q: Explain the packet header. What fields does it contain and why?
**A:** `seq_num` (4B) — identifies position of this packet in the byte stream. `ack_num` (4B) — tells sender the next expected byte. `flags` (1B) — encodes SYN/ACK/FIN as a bitmask. `checksum` (2B) — 16-bit one's complement sum for error detection. Total 11 bytes packed with `struct` in network byte order.

---

### Q: Walk me through the stop-and-wait mechanism in `_reliable_send`.
**A:** Send the packet, set a 50ms timeout, wait for ACK. If ACK arrives with correct `ack_num`, return success. If timeout fires, break inner loop and retransmit. If a corrupt packet arrives (ValueError from `Packet.unpack`), catch silently and keep waiting. Repeat up to 50 times before raising `ConnectionError`.

---

### Q: What happens when a packet is corrupted?
**A:** `Packet.unpack()` recomputes the checksum. If it doesn't match the received checksum field, it raises `ValueError`. The caller catches this and ignores the packet. The sender times out and retransmits. The receiver will get the correct packet eventually.

---

### Q: How does the receiver detect and discard duplicate packets?
**A:** Each `RUDPSocket` tracks `self.expected_seq`. When `recv()` gets a packet whose `seq_num != expected_seq`, it sends an ACK but **does not return the data** to the application. The application never sees duplicates.

---

### Q: Why does the receiver send 3 ACKs for each data packet?
**A:** To increase the probability that at least one ACK gets through, even under simulated loss. Since ACKs have no ACK of their own, a single lost ACK would cause an unnecessary retransmission. Burst-sending 3 copies reduces this risk.

---

### Q: Explain the three-way handshake in your implementation.
**A:** (1) Client sends SYN with its ISN (initial sequence number). (2) Server responds with SYNACK carrying its own ISN and ack_num = client_ISN + 1, confirming it received the SYN. (3) Client sends ACK with ack_num = server_ISN + 1. After this, both sides have synchronized sequence numbers and data transfer begins.

---

### Q: Why are sequence numbers initialized randomly?
**A:** To prevent stale packets from a previous connection (with the same port pair) being mistakenly accepted by a new connection. This mirrors TCP's ISN randomization.

---

### Q: How does the server handle GET vs POST?
**A:** GET: resolves the path to a file in `www/`. If found, reads and returns it with a `Content-Type` header and 200 OK. If not, returns 404. POST: checks registered handlers (e.g., `/echo`). If none match, echoes the request body back with 200 OK.

---

### Q: Why does the server create a new RUDPSocket per connection?
**A:** HTTP/1.0 is connection-per-request. RUDP uses UDP which is connectionless, but our RUDP adds state (seq_num, expected_seq, target_addr). A new socket starts clean state for each new client. It's the equivalent of `accept()` returning a new socket in TCP.

---

### Q: How does `_recv_http_request` know when the full request has arrived?
**A:** It accumulates chunks until it finds `\r\n\r\n` (header terminator). Then it parses `Content-Length` from headers and keeps reading until `body_start + Content-Length` bytes are in the buffer. For GET (no body), `Content-Length` is 0, so it stops immediately after headers.

---

### Q: What is the browser gateway and why is it needed?
**A:** Real browsers use TCP (`SOCK_STREAM`), but our server uses RUDP over UDP. The `BrowserGateway` is a TCP server that receives browser requests, forwards them to the RUDP server using `HTTPClient`, and relays the response back. It's a protocol bridge. Without it, browsers couldn't communicate with our RUDP server.

---

### Q: How does path traversal protection work in the server?
**A:**
```python
file_path = os.path.normpath(os.path.join(self.webroot, path.lstrip("/")))
if not file_path.startswith(self.webroot):
    return HTTPResponse(404, ...)
```
`normpath` resolves `../` sequences. The `startswith` check ensures the resolved path is still inside `www/`. Without this, a request like `GET /../etc/passwd` could escape the web root.

---

## 12. Expected TA Questions — Lecture Concepts

### Q: What is the difference between TCP and UDP? Why use UDP as a base?
**A:** TCP provides reliable, ordered, connection-oriented delivery with flow and congestion control — implemented in kernel. UDP is connectionless, unreliable, but has very low overhead and gives application full control. We use UDP as base because it lets us implement custom reliability in user space — exactly what this lab demonstrates.

---

### Q: What is rdt 3.0 and how does it differ from rdt 2.x?
**A:** 
- `rdt 2.x` handles **bit errors** (corruption) via checksum + ACK/NAK, adding sequence numbers in 2.1 to handle duplicate ACKs.
- `rdt 3.0` additionally handles **packet loss** by adding **timers** (timeouts). If no ACK arrives within the timeout, the sender assumes loss and retransmits. The sequence numbers also prevent old retransmissions from being accepted as new data.

---

### Q: What is the alternating bit protocol?
**A:** A simplified stop-and-wait where sequence numbers alternate between 0 and 1. It's the simplest case of `rdt 2.1` / `rdt 3.0`. Our implementation uses full 32-bit sequence numbers (like TCP), not alternating bit, but the behavior is equivalent.

---

### Q: Define: propagation delay, transmission delay, queuing delay, processing delay.
**A:**
- **Transmission delay** = L/R (packet size / link bandwidth) — time to push all bits onto wire
- **Propagation delay** = d/s (distance / signal speed) — time for bit to travel through medium
- **Queuing delay** — time waiting in router queue (variable)
- **Processing delay** — time router takes to examine header and decide forwarding

RTT (round-trip time) ≈ 2 × propagation delay (dominates in wide-area networks).

---

### Q: What is the purpose of the checksum in UDP and TCP headers?
**A:** Error detection only — not correction. The 16-bit one's complement checksum covers the header and data (and a pseudo-header in TCP/UDP that includes IP addresses). If the receiver computes a different checksum than the received one, the segment is discarded. UDP checksum is optional (field can be zero); TCP checksum is mandatory.

---

### Q: What is Go-Back-N vs Selective Repeat? How does stop-and-wait relate?
**A:**
- **Stop-and-wait** = sliding window of size 1. Send 1, wait, send 1.
- **Go-Back-N (GBN)** = window size N. On error, retransmit from the errored packet onward (all N). Receiver only buffers one packet.
- **Selective Repeat (SR)** = window size N. Only retransmit the specific lost packet. Receiver buffers out-of-order packets.

The lab uses **stop-and-wait** (no window, no concurrent inflight packets).

---

### Q: What is the significance of the SYN, SYNACK, ACK, FIN flags?
**A:**
- **SYN** — Synchronize. Initiates connection and announces initial sequence number.
- **SYNACK** — Server's combined SYN+ACK: acknowledges client SYN and announces server ISN.
- **ACK** — Acknowledgment. Confirms receipt of data or control packets.
- **FIN** — Finish. Signals desire to close connection (one direction).

TCP uses a 4-way FIN for graceful close (FIN→ACK→FIN→ACK). Our implementation uses a simplified 2-way close.

---

### Q: What is a socket? What is the difference between SOCK_STREAM and SOCK_DGRAM?
**A:** A socket is a software abstraction for a network endpoint, identified by (IP, port, protocol). `SOCK_STREAM` = TCP — provides a reliable, ordered byte stream. `SOCK_DGRAM` = UDP — provides unreliable, unordered datagrams. Both are accessed through the same POSIX socket API but have different semantics.

---

### Q: What is multiplexing and demultiplexing at the transport layer?
**A:** **Multiplexing** — multiple applications share the same IP address, differentiated by port numbers. Sockets from multiple processes are multiplexed onto IP datagrams. **Demultiplexing** — the transport layer uses (src IP, src port, dst IP, dst port) to route incoming segments to the correct socket/process. UDP demux uses only (dst IP, dst port); TCP demux uses all 4 fields.

---

### Q: What is the purpose of the `Content-Length` header? What happens without it?
**A:** It tells the receiver how many bytes the body contains. Over a persistent connection or any stream-based protocol, without `Content-Length`, the receiver doesn't know where the body ends and the next message begins. In HTTP/1.0, the connection closes after the response, so the receiver could alternatively read until EOF — but `Content-Length` is still best practice.

---

### Q: Why does HTTP/1.0 create a new connection for every request?
**A:** HTTP/1.0 was designed for simple document retrieval. Each request is independent, so the simplest design is open → request → respond → close. HTTP/1.1 introduced persistent connections (keep-alive) to avoid the TCP connection setup overhead for each resource (especially on pages with many images/scripts).

---

### Q: What is the purpose of the `\r\n\r\n` separator in HTTP?
**A:** It's the blank line that separates HTTP headers from the body (per RFC 7230). `\r\n` = CRLF (Carriage Return + Line Feed). HTTP strictly requires CRLF for header line termination, and a blank CRLF line after all headers signals "headers done, body starts here."

---

### Q: What is the role of the `struct` module and network byte order?
**A:** `struct.pack/unpack` converts Python values to/from raw bytes for binary protocols. Network byte order = **big-endian** (most significant byte first), enforced by the `!` prefix. Without standardizing byte order, a little-endian machine (x86) and big-endian machine would interpret the same bytes differently.

---

### Q: Could this RUDP handle out-of-order packets?
**A:** Currently, the stop-and-wait approach plus `expected_seq` checking means the receiver **discards** any out-of-order packet (seq_num ≠ expected_seq) and re-ACKs the last seen. The application only sees in-order data. If you wanted to handle reordering more efficiently, you'd need Selective Repeat with a receive buffer.

---

*Good luck with the TA discussion! Focus on being able to trace a packet from `client.get()` all the way through to `server._handle_get()` and back.*
