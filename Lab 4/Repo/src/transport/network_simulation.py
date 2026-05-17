import random


def simulate_loss(drop_probability: float) -> bool:
    """Returns True if the packet should be dropped based on the probability."""
    return random.random() < drop_probability


def corrupt_packet(packet_bytes: bytes) -> bytes:
    """Flips a bit in the packet byte string to simulate corruption and trigger false checksums."""
    if not packet_bytes:
        return packet_bytes

    byte_list = bytearray(packet_bytes)
    target_byte_index = random.randint(0, len(byte_list) - 1)

    # Flip the lowest bit of the selected byte
    byte_list[target_byte_index] ^= 1

    return bytes(byte_list)
