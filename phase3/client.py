import socket
import os
import struct
from shared import send_msg, recv_msg, deserialize_public_key, rsa_encrypt

HOST = '127.0.0.1'
PORT = 9999

# establish connection
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"[+] Connected to {HOST}:{PORT}")

# get public key
raw_len = client_socket.recv(4)
msg_len = struct.unpack('>I', raw_len)[0]
pem = client_socket.recv(msg_len)
server_public_key = deserialize_public_key(pem)
print("[+] Received server public key")

# generate session key and encpyt then send
session_key = os.urandom(32)
encrypted_session_key = rsa_encrypt(session_key, server_public_key)
length = struct.pack('>I', len(encrypted_session_key))
client_socket.sendall(length + encrypted_session_key)
print(f"[*] Session key sent (encrypted with server's public key)")

# communication using new session key
send_msg(client_socket, b"Hello! Session key exchange worked!", session_key)

reply = recv_msg(client_socket, session_key)
print(f"[RECEIVED]: {reply.decode()}")

client_socket.close()
