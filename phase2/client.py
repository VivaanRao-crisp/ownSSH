import socket
from shared import send_msg, recv_msg    # ← only new import

HOST = '127.0.0.1'
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"[+] Connected to {HOST}:{PORT}")

# ↓ only these two lines changed from Phase 1
send_msg(client_socket, b"Hello! Dr. Ganguly cannot read this anymore.")
print("[SENT]: encrypted message")

reply = recv_msg(client_socket)
print(f"[RECEIVED]: {reply.decode()}")

client_socket.close()