#ownSSH

A ground-up implementation of the core mechanics behind Secure Shell (SSH), built using only raw sockets and low-level cryptographic primitives. No paramiko. No asyncssh. No shortcuts.

This project was built in phases, each one solving a specific problem that the previous phase left open.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Phase 1 — Raw Sockets](#phase-1--raw-sockets)
- [Phase 2 — Symmetric Encryption](#phase-2--symmetric-encryption)
- [Phase 3 — Asymmetric Key Exchange](#phase-3--asymmetric-key-exchange)
- [How to Run](#how-to-run)

---

## Project Structure

```
ownssh/
├── phase1/
│   ├── server.py
│   └── client.py
├── phase2/
│   ├── server.py
│   ├── client.py
│   └── shared.py
├── phase3/
│   ├── server.py
│   ├── client.py
│   └── shared.py
├── screenshots/
│   ├── phase1_wireshark_plaintext.png
│   └── phase2_wireshark_encrypted.png
└── README.md
```

---

## Requirements

**Language:** Python 3.8+

**Standard library used:** `socket`, `os`, `struct`, `json`, `subprocess`

**One external dependency:**

```bash
pip install cryptography
```

No other third-party libraries are used. No high-level SSH libraries. No TLS wrappers.

---

## Phase 1 — Raw Sockets

### What this phase does

A server and a client exchange messages over a raw TCP connection. No encryption, no authentication, no frills. The sole purpose of this phase is to establish that two machines can talk to each other over the network — and to demonstrate exactly why that is a problem.

### The problem it reveals

Anyone on the same network running a packet capture tool can read every byte of every message in plain text. This is not a theoretical vulnerability. You can see it yourself with Wireshark or tcpdump by filtering on `tcp.port == 9999` during the exchange.

### How it works

```
client.py                          server.py
─────────────────────────────────────────────────────

socket(AF_INET, SOCK_STREAM)       socket(AF_INET, SOCK_STREAM)
                                   bind(0.0.0.0:9999)
                                   listen()
connect(127.0.0.1:9999)  ───────►  accept() → conn, addr
send(b"Hello from Alice!")──────►  recv(4096)
                                   print(message)
recv(4096)              ◄───────   send(b"Message received")
print(reply)
close()                            close()
```

### Key concepts

**`socket.AF_INET`** — specifies IPv4 addressing.

**`socket.SOCK_STREAM`** — specifies TCP: ordered, reliable, stream-based delivery.

**`bind('0.0.0.0', 9999)`** — claims port 9999 on all network interfaces of the machine.

**`listen(1)`** — tells the OS to queue incoming connection attempts.

**`accept()`** — blocks until a client connects. Returns a new socket dedicated to that client and the client's address.

**`connect(host, port)`** — triggers the TCP three-way handshake (SYN, SYN-ACK, ACK). Returns after the connection is established.

**`SO_REUSEADDR`** — allows the server to rebind immediately after a crash, bypassing the OS TIME_WAIT delay.

### What Wireshark shows

The full message text is visible in the packet payload. Readable by anyone. This is the problem that every subsequent phase works to eliminate.

---

## Phase 2 — Symmetric Encryption (AES-GCM)

### What this phase does

Every message is encrypted before it leaves the sender and decrypted after it arrives at the receiver. A shared 32-byte key is hardcoded on both sides. The socket code from Phase 1 is almost entirely unchanged — encryption is a layer placed on top.

### The algorithm: AES-GCM

AES-GCM (Advanced Encryption Standard in Galois/Counter Mode) was chosen specifically because it provides two guarantees in a single operation:

- **Confidentiality** — the ciphertext reveals nothing about the plaintext without the key.
- **Authenticity** — a 16-byte authentication tag is produced during encryption and verified during decryption. If a single bit of the ciphertext is modified in transit, decryption throws an exception instead of returning corrupted data.

This second property (the auth tag) is what separates GCM from older modes like CBC, which only encrypt without verifying integrity.

### The nonce

Every encryption call generates 16 fresh random bytes from `os.urandom()` called the nonce (number used once). The nonce is prepended to the ciphertext and sent in plaintext — it is not secret. Its only requirement is uniqueness. Reusing a nonce with the same key catastrophically breaks GCM security, which is why it is generated from the OS's cryptographically secure random source every time.

### The length-prefix problem

TCP is a stream protocol, not a message protocol. When the receiver calls `recv()`, there is no built-in boundary telling it where one message ends and the next begins. Phase 1 avoided this only because messages were short and the connection closed immediately.

Phase 2 solves this properly: every send prepends a 4-byte big-endian unsigned integer representing the byte length of the payload. The receiver reads 4 bytes first, unpacks the integer, then reads exactly that many bytes.

```
Wire format:
[ 0x00 0x00 0x00 0x32 | 16 bytes nonce | N bytes ciphertext+tag ]
  ↑ 4-byte length       ↑ sent plaintext  ↑ unreadable
```

### shared.py

Four helper functions live here and are imported by both server and client:

- `encrypt(plaintext, key)` — generates nonce, runs AES-GCM, returns `nonce + ciphertext+tag`
- `decrypt(data, key)` — splits nonce from ciphertext, runs AES-GCM decryption, verifies tag
- `send_msg(sock, plaintext, key)` — encrypts, prepends length, calls `sendall()`
- `recv_msg(sock, key)` — reads length, reads payload, decrypts, returns plaintext

### The remaining weakness

The key is hardcoded in source code. Anyone who reads the code has the key. There is no way to establish the key securely over the network without already having a secure channel — a circular problem. Phase 3 breaks that circle.

### What Wireshark shows

The message payload is now random-looking bytes. The 4-byte length prefix is visible. The nonce is visible. Neither reveals anything about the message content.

---

## Phase 3 — Asymmetric Encryption and Key Exchange (RSA-OAEP)

### What this phase does

The hardcoded key is eliminated. Instead, the server holds an RSA-2048 keypair. The client generates a fresh random session key on every connection, encrypts it with the server's public key, and sends it over. The server decrypts it with its private key. Both sides now share a secret that never traveled the wire in readable form.

### Why this works

RSA is built on a mathematical one-way trap: multiplying two large primes together is trivial, but factoring the result back into its primes is computationally infeasible at 2048-bit key sizes. The public key contains the product. The private key contains the factors. Encrypting with the public key is easy for anyone. Decrypting requires the factors — only the server has those.

### The padding: RSA-OAEP

Raw RSA encryption is deterministic. The same plaintext encrypted with the same key always produces the same ciphertext, which opens the door to chosen-ciphertext and pattern-matching attacks. OAEP (Optimal Asymmetric Encryption Padding) introduces structured randomness. Every encryption of the same input produces a different output. This is the mandatory modern standard.

OAEP configuration used:

```
padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
)
```

MGF1 is the mask generation function — it uses SHA256 to generate pseudorandom bytes that scramble the padded message before RSA exponentiation. Both the MGF and the main OAEP hash use SHA256 here, which is the universal standard configuration.

### Key serialization

RSA key objects live in memory as Python objects. To send a public key over a socket it must be serialized to bytes. PEM format is used (Privacy Enhanced Mail — the format with `-----BEGIN PUBLIC KEY-----` headers). PEM base64-encodes the binary key data and wraps it in standard headers that allow any compliant library to parse it.

On the receiving end, `serialization.load_pem_public_key()` parses the PEM bytes back into a usable key object.

### The handshake sequence

```
Phase 3 wire exchange (in order):

1.  TCP three-way handshake
2.  Server → Client    [4 bytes length] [PEM public key — plaintext, harmless]
3.  Client → Server    [4 bytes length] [256 bytes RSA-OAEP encrypted session key]
4.  Client → Server    [4 bytes] [AES-GCM encrypted message]
5.  Server → Client    [4 bytes] [AES-GCM encrypted response]
```

Steps 4 and 5 are identical to Phase 2. The only difference is the session key was negotiated dynamically rather than hardcoded.

### What Wireshark shows

The public key is visible in plaintext — this is expected and harmless. The RSA ciphertext in step 3 is 256 bytes of noise. The session key never appears on the wire in any usable form. All subsequent AES-GCM traffic is indistinguishable from Phase 2.

---

## How to Run

### Phase 1

```bash
# Terminal 1
cd phase1
python3 server.py

# Terminal 2
cd phase1
python3 client.py
```

### Phase 2

```bash
# Terminal 1
cd phase2
python3 server.py

# Terminal 2
cd phase2
python3 client.py
```

### Phase 3

```bash
# Terminal 1
cd phase3
python3 server.py

# Terminal 2
cd phase3
python3 client.py
```

Always start the server before the client. If running across two machines, replace `127.0.0.1` in client.py with the server's LAN IP address.

To find the server's LAN IP:

```bash
# Linux
ip a

# Windows
ipconfig
```

---

## Notes

- Port 9999 is used across all phases. Make sure nothing else is occupying it.
- `SO_REUSEADDR` is set on all server sockets so you can restart the server immediately without waiting for the OS TIME_WAIT period to expire.
- The AES-256 session key in Phase 3 is 32 bytes generated by `os.urandom()` — the operating system's cryptographically secure random number generator, not Python's `random` module.
- RSA key generation takes a fraction of a second on modern hardware. This is expected behavior, not a hang.

---

*Phase 4 and Phase 5 documentation are not in this README. Sorry about that. Actually, sorry for making you read all the way down here just to find out there is nothing here. That is on me. Go build the thing.*
