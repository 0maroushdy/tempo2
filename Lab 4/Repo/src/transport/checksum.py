def calculate_checksum(data: bytes) -> int:
    """Calculates the 16-bit one's complement checksum."""
    if len(data) % 2 == 1:
        data += b'\0'

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        checksum += word
        checksum = (checksum & 0xffff) + (checksum >> 16)

    return ~checksum & 0xffff