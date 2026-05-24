import socket

HOST = '127.0.0.1'   # loopback IP , so lo0 in wireshark
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"[+] Connected to server at {HOST}:{PORT}") #connects to server

message = b"Dr. Ganguly can read this btw, he thinks he's tuff lol"
client_socket.send(message)
print(f"[SENT]: {message.decode('utf-8')}")

reply = client_socket.recv(4096)
print(f"[RECEIVED]: {reply.decode('utf-8')}")

client_socket.close()
print("[-] Connection closed.")
