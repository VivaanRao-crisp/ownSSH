import socket
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from shared import send_msg, recv_msg, serialize_public_key, rsa_decrypt

HOST = '0.0.0.0'
PORT = 9999

# Generate RSA keypair once, before any connection
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()
print("[*] RSA-2048 keypair generated")

# socket setup, indetical to phase2
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print("[*] Listening on port 9999...")

conn, addr = server_socket.accept()
print(f"[+] Connection from {addr}")

# share public key w client
pem = serialize_public_key(public_key)
length = struct.pack('>I', len(pem))
conn.sendall(length + pem)
print("[*] Public key sent to client")

# receive RSA session key and decrypt
raw_len = conn.recv(4)
msg_len = struct.unpack('>I', raw_len)[0]
encrypted_session_key = conn.recv(msg_len)
session_key = rsa_decrypt(encrypted_session_key, private_key)
print(f"[+] Session key established: {session_key.hex()}")

# communicate using session key
data = recv_msg(conn, session_key)
print(f"[RECEIVED]: {data.decode()}")

send_msg(conn, b"Secure channel established!", session_key)

conn.close()
server_socket.close()
