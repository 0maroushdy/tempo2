import socket

HOST = '127.0.0.1'
PORT = 65433


def process_message(message: str) -> str:
    if len(message) == 0:
        return message

    command = message[0]
    data = message[1:]

    if command == 'A':
        # Sort characters in descending order
        return ''.join(sorted(data, reverse=True))
    elif command == 'C':
        # Sort characters in ascending order
        return ''.join(sorted(data))
    elif command == 'D':
        # Convert all letters to uppercase
        return data.upper()
    else:
        # Return the exact same message
        return message


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((HOST, PORT))
    print(f"[UDP] Server listening on {HOST}:{PORT}")

    try:
        while True:
            data, client_addr = server.recvfrom(1024)
            message = data.decode('utf-8').strip()
            print(f"[UDP] Received from {client_addr}: {message}")

            response = process_message(message)
            print(f"[UDP] Sending to {client_addr}: {response}")
            server.sendto(response.encode('utf-8'), client_addr)
    except KeyboardInterrupt:
        print("\n[UDP] Server shutting down.")
    finally:
        server.close()


if __name__ == '__main__':
    main()
