import socket
import threading

HOST = '127.0.0.1'
PORT = 65432


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


def handle_client(conn: socket.socket, addr: tuple):
    print(f"[TCP] New connection from {addr}")
    with conn:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    # Client disconnected
                    break
                message = data.decode('utf-8').strip()
                print(f"[TCP] Received from {addr}: {message}")

                response = process_message(message)
                print(f"[TCP] Sending to {addr}: {response}")
                conn.sendall(response.encode('utf-8'))
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"[TCP] Error with {addr}: {e}")
                break
    print(f"[TCP] Connection closed: {addr}")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[TCP] Server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            # Create a new thread for each client
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
            print(f"[TCP] Active connections: {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\n[TCP] Server shutting down.")
    finally:
        server.close()


if __name__ == '__main__':
    main()
