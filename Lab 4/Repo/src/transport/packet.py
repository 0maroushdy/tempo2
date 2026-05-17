import struct
from .checksum import calculate_checksum

# Flags
SYN = 0b0001
ACK = 0b0010
FIN = 0b0100
SYNACK = SYN | ACK


class Packet:
    # Header format: Sequence Number (I, 4 bytes), Acknowledgment Number (I, 4 bytes),
    # Flags (B, 1 byte), Checksum (H, 2 bytes) -> Total 11 bytes header
    HEADER_FORMAT = '!IIBH'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq_num: int, ack_num: int, flags: int, data: bytes = b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.data = data
        self.checksum = 0

    def pack(self) -> bytes:
        """Packs the header and data, calculates and inserts the checksum."""
        header_without_checksum = struct.pack(self.HEADER_FORMAT, self.seq_num, self.ack_num, self.flags, 0)
        packet_data = header_without_checksum + self.data
        self.checksum = calculate_checksum(packet_data)

        # Repack with the calculated checksum
        final_header = struct.pack(self.HEADER_FORMAT, self.seq_num, self.ack_num, self.flags, self.checksum)
        return final_header + self.data

    @classmethod
    def unpack(cls, raw_bytes: bytes) -> 'Packet':
        """Unpacks raw bytes into a Packet object and verifies checksum."""
        header = raw_bytes[:cls.HEADER_SIZE]
        data = raw_bytes[cls.HEADER_SIZE:]
        seq_num, ack_num, flags, received_checksum = struct.unpack(cls.HEADER_FORMAT, header)

        # Verify checksum [cite: 38]
        header_without_checksum = struct.pack(cls.HEADER_FORMAT, seq_num, ack_num, flags, 0)
        calculated_checksum = calculate_checksum(header_without_checksum + data)

        if received_checksum != calculated_checksum:
            raise ValueError("Checksum verification failed. Corrupt packet.")

        pkt = cls(seq_num, ack_num, flags, data)
        pkt.checksum = received_checksum
        return pkt