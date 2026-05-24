import socket #access network

HOST = '0.0.0.0'
PORT = 9999

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creates actual socket object
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #quality of life fix, prevent 60s wait if server crash
server_socket.bind((HOST, PORT)) #claim port for program
server_socket.listen(1) #start accepting connections and put them on queue, 1 is the backlog (max length of queue)

print(f"[*] Server listening on port {PORT}...")

conn, addr = server_socket.accept() #take the connection, program freezes here until client connects, unpacks into two variables, addr and conn(brand new socket object)
print(f"[+] Connection established from {addr}") #addr would be like ('ipv4 addr', random port)

data = conn.recv(4096) #receive upto 4kb, recv() returns a raw byte, not a string yet
print(f"[RECEIVED]: {data.decode('utf-8')}") #UTF-8 is the standard text encoding — every English letter/number/symbol maps to one byte. Special characters (Hindi, emoji, etc.) use 2–4 bytes each.

response = b"Hello from the server! Message received." #b is bytes literal,makes it bytes and not string, send() accepts only bytes
conn.send(response) #for commercial code, use sendall, which retries as send may not send all bytes on a busy system
print(f"[SENT]: {response.decode('utf-8')}")

conn.close() #sends a FIN packet,
server_socket.close()
print("[-] Connection closed.")