import socket
from shared import send_msg, recv_msg

HOST = '0.0.0.0'
PORT = 9999

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print("[*] Server listening on port 9999...")

conn, addr = server_socket.accept()
print(f"[+] Connection from {addr}")


data = recv_msg(conn)
print(f"[RECEIVED]: {data.decode()}")

send_msg(conn, b"Hello from server! (encrypted)")
print("[SENT]: encrypted response")

conn.close()
server_socket.close()