import socket
import threading

clients = []

def broadcast(data):
    for c in clients:
        try:
            c.sendall(data)
        except Exception:
            clients.remove(c)
            c.close()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} підключився")
    clients.append(conn)
    buffer = ""
    while True:
        try:
            chunk = conn.recv(8192)
            if not chunk:
                break
            buffer += chunk.decode('utf-8', errors='ignore')
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                broadcast((line + "\n").encode('utf-8'))
        except Exception:
            break
    print(f"[DISCONNECTED] {addr} відключився")
    if conn in clients:
        clients.remove(conn)
    conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # дозволяє перезапуск порту
    server.bind(("localhost", 2525))
    server.listen()
    print("[SERVER STARTED] Чат готовий до підключень")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
