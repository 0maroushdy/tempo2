import socket
import sys

TCP_HOST = '127.0.0.1'
TCP_PORT = 65432
UDP_HOST = '127.0.0.1'
UDP_PORT = 65433


def tcp_client():
    print(f"[TCP Client] Connecting to {TCP_HOST}:{TCP_PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((TCP_HOST, TCP_PORT))
        print("[TCP Client] Connected! Type 'quit' to exit.\n")

        while True:
            message = input("You: ")
            if message.lower() == 'quit':
                break

            sock.sendall(message.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8')
            print(f"Server: {response}\n")

    print("[TCP Client] Disconnected.")


def udp_client():
    print(f"[UDP Client] Sending to {UDP_HOST}:{UDP_PORT}")
    print("[UDP Client] Ready! Type 'quit' to exit.\n")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            message = input("You: ")
            if message.lower() == 'quit':
                break

            sock.sendto(message.encode('utf-8'), (UDP_HOST, UDP_PORT))
            response, _ = sock.recvfrom(1024)
            print(f"Server: {response.decode('utf-8')}\n")

    print("[UDP Client] Done.")


def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in ('tcp', 'udp'):
        print("Usage: python client.py <tcp|udp>")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == 'tcp':
        tcp_client()
    else:
        udp_client()


if __name__ == '__main__':
    main()
