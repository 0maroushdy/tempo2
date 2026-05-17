import unittest
import threading
import time
from src.transport.packet import Packet
from src.transport.checksum import calculate_checksum
from src.transport.rudp_socket import RUDPSocket


class TestTransportLayer(unittest.TestCase):

    def test_checksum_determinism(self):
        """Verifies checksum calculates consistently for identical payloads."""
        payload = b"Reliable UDP Data"
        chk1 = calculate_checksum(payload)
        chk2 = calculate_checksum(payload)
        self.assertEqual(chk1, chk2)

    def test_packet_pack_unpack(self):
        """Verifies packet structure serialization and deserialization."""
        original_pkt = Packet(seq_num=100, ack_num=0, flags=1, data=b"Payload")
        raw_bytes = original_pkt.pack()

        unpacked_pkt = Packet.unpack(raw_bytes)
        self.assertEqual(unpacked_pkt.seq_num, 100)
        self.assertEqual(unpacked_pkt.data, b"Payload")

    def test_corrupted_packet_rejection(self):
        """Verifies system drops packets with invalid checksums[cite: 38]."""
        pkt = Packet(seq_num=1, ack_num=0, flags=0, data=b"Valid Data")
        raw_bytes = bytearray(pkt.pack())

        # Invert a byte in the payload to simulate a false checksum
        raw_bytes[-1] ^= 0xFF

        with self.assertRaises(ValueError):
            Packet.unpack(bytes(raw_bytes))

    def test_transmission_with_loss_and_corruption(self):
        server_addr = ('127.0.0.1', 9000)
        test_payload = b"End-to-End Transmission Test"

        server_sock = RUDPSocket(drop_prob=0.3, corrupt_prob=0.3)
        server_sock.bind(server_addr)

        client_sock = RUDPSocket(drop_prob=0.3, corrupt_prob=0.3)

        def server_listen():
            client_addr = server_sock.accept()

            # Receive data payload
            data = server_sock.recv(2048)
            self.assertEqual(data, test_payload)

            # Await EOF (FIN) from client
            fin_signal = server_sock.recv(2048)
            self.assertEqual(fin_signal, b"")

            # Execute standard RUDP TIME_WAIT teardown
            server_sock.close()

        server_thread = threading.Thread(target=server_listen)
        server_thread.start()

        time.sleep(0.1)

        client_sock.connect(server_addr)
        client_sock.send(test_payload)
        client_sock.close()

        server_thread.join(timeout=10.0)
        self.assertFalse(server_thread.is_alive())

    def test_bidirectional_connection(self):
        """Verifies bidirectional connection."""

        def run_server():
            server_socket = RUDPSocket(drop_prob=0.2, corrupt_prob=0.1)
            server_socket.bind(("127.0.0.1", 8000))
            server_socket.accept()

            data = server_socket.recv(bufsize=1024)
            # print(f"Server received: {data}")
            assert b"GET /index.html HTTP/1.0" in data, "Server failed to receive correct GET request"

            server_socket.send(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nOK")
            server_socket.close()

        def run_client():
            client_socket = RUDPSocket(drop_prob=0.2, corrupt_prob=0.1)
            client_socket.connect(("127.0.0.1", 8000))

            request = b"GET /index.html HTTP/1.0\r\nHost: localhost\r\n\r\n"
            client_socket.send(request)

            response = client_socket.recv(bufsize=1024)
            # print(f"Client received: {response}")
            assert b"200 OK" in response, "Client failed to receive HTTP 200 OK response"

            time.sleep(2)
            client_socket.close()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        time.sleep(0.2)
        run_client()

        thread.join(timeout=5)
        assert not thread.is_alive(), "Server thread hung; transmission sequence failed"


if __name__ == '__main__':
    unittest.main()