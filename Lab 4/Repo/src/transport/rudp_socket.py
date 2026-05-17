import socket
import time
import random
from .packet import Packet, SYN, ACK, FIN, SYNACK
from .network_simulation import simulate_loss, corrupt_packet


class RUDPSocket:
    def __init__(self, drop_prob=0.0, corrupt_prob=0.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target_addr = None
        self.seq_num = random.randint(1, 1000)
        self.expected_seq = 0
        self.drop_prob = drop_prob
        self.corrupt_prob = corrupt_prob

    def bind(self, address: tuple):
        self.sock.bind(address)

    def _send_raw(self, raw_bytes: bytes):
        if simulate_loss(self.drop_prob):
            return
        if simulate_loss(self.corrupt_prob):
            raw_bytes = corrupt_packet(raw_bytes)
        self.sock.sendto(raw_bytes, self.target_addr)

    def _reliable_send(self, packet: Packet, expected_flags=ACK, is_synack=False):
        packet_bytes = packet.pack()
        expected_ack_num = packet.seq_num + max(len(packet.data), 1)

        for _ in range(50):
            self._send_raw(packet_bytes)

            deadline = time.time() + 0.05
            while time.time() < deadline:
                try:
                    self.sock.settimeout(max(0.001, deadline - time.time()))
                    raw_ack, _ = self.sock.recvfrom(2048)
                    ack_pkt = Packet.unpack(raw_ack)

                    if ack_pkt.flags == expected_flags:
                        if expected_flags == ACK and ack_pkt.ack_num != expected_ack_num:
                            pass
                        else:
                            if expected_flags == SYNACK:
                                self.expected_seq = ack_pkt.seq_num + 1
                                ack_final = Packet(self.seq_num + 1, self.expected_seq, ACK)
                                self._send_raw(ack_final.pack())
                            self.sock.settimeout(None)
                            return

                    if is_synack and (ack_pkt.flags == 0 or ack_pkt.flags == FIN):
                        self.sock.settimeout(None)
                        return

                    if ack_pkt.flags == SYN:
                        synack_pkt = Packet(self.seq_num, ack_pkt.seq_num + 1, SYNACK)
                        self._send_raw(synack_pkt.pack())

                    elif ack_pkt.flags == SYNACK:
                        ack_final = Packet(self.seq_num, ack_pkt.seq_num + 1, ACK)
                        self._send_raw(ack_final.pack())

                    elif ack_pkt.flags == FIN:
                        ack_num = ack_pkt.seq_num + max(len(ack_pkt.data), 1)
                        re_ack = Packet(self.seq_num, ack_num, ACK)
                        self._send_raw(re_ack.pack())
                        if expected_flags == ACK and not is_synack:
                            self.sock.settimeout(None)
                            return

                    elif ack_pkt.flags == 0:
                        ack_num = ack_pkt.seq_num + max(len(ack_pkt.data), 1)
                        re_ack = Packet(self.seq_num, ack_num, ACK)
                        self._send_raw(re_ack.pack())

                except socket.timeout:
                    break
                except Exception:
                    time.sleep(0.005)

        raise ConnectionError(f"Maximum retransmission limit exceeded for seq {packet.seq_num}")

    def connect(self, address: tuple):
        self.target_addr = address
        syn_pkt = Packet(self.seq_num, 0, SYN)
        self._reliable_send(syn_pkt, expected_flags=SYNACK)
        self.seq_num += 1

    def accept(self):
        self.sock.settimeout(10.0)
        while True:
            try:
                raw_data, addr = self.sock.recvfrom(2048)
                pkt = Packet.unpack(raw_data)

                if pkt.flags == SYN:
                    self.target_addr = addr
                    self.expected_seq = pkt.seq_num + 1

                    synack_pkt = Packet(self.seq_num, self.expected_seq, SYNACK)
                    self._reliable_send(synack_pkt, expected_flags=ACK, is_synack=True)
                    self.seq_num += 1
                    return addr
            except socket.timeout:
                raise TimeoutError("Accept timed out.")
            except Exception:
                continue

    def send(self, data: bytes):
        if not data:
            return
        chunk_size = 1024
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            pkt = Packet(self.seq_num, 0, 0, chunk)
            self._reliable_send(pkt, expected_flags=ACK)
            self.seq_num += len(chunk)

    def recv(self, bufsize: int) -> bytes:
        self.sock.settimeout(10.0)
        while True:
            try:
                raw_data, addr = self.sock.recvfrom(bufsize + Packet.HEADER_SIZE)
                if addr != self.target_addr:
                    continue

                pkt = Packet.unpack(raw_data)

                if pkt.flags == SYN:
                    synack_pkt = Packet(self.seq_num - 1, pkt.seq_num + 1, SYNACK)
                    self._send_raw(synack_pkt.pack())
                    continue

                if pkt.flags == SYNACK:
                    ack_final = Packet(self.seq_num, pkt.seq_num + 1, ACK)
                    self._send_raw(ack_final.pack())
                    continue

                if not pkt.data and pkt.flags == ACK:
                    continue

                ack_num = pkt.seq_num + max(len(pkt.data), 1)
                ack_pkt = Packet(self.seq_num, ack_num, ACK)

                if pkt.seq_num == self.expected_seq:
                    # Target acquired. Burst ACKs to neutralize immediate packet drop.
                    for _ in range(3):
                        self._send_raw(ack_pkt.pack())
                    self.expected_seq = ack_num
                    if pkt.flags == FIN:
                        return b""
                    return pkt.data
                else:
                    self._send_raw(ack_pkt.pack())

            except socket.timeout:
                raise TimeoutError("Receive sequence timed out.")
            except Exception:
                continue

    def close(self):
        fin_pkt = Packet(self.seq_num, 0, FIN)
        try:
            self._reliable_send(fin_pkt, expected_flags=ACK)
        except ConnectionError:
            pass

        deadline = time.time() + 0.1
        while time.time() < deadline:
            try:
                self.sock.settimeout(max(0.001, deadline - time.time()))
                raw_data, addr = self.sock.recvfrom(2048)
                if addr != self.target_addr:
                    continue
                pkt = Packet.unpack(raw_data)
                if pkt.flags == 0 or pkt.flags == FIN:
                    ack_num = pkt.seq_num + max(len(pkt.data), 1)
                    ack_pkt = Packet(self.seq_num, ack_num, ACK)
                    self._send_raw(ack_pkt.pack())
            except Exception:
                pass

        self.sock.close()