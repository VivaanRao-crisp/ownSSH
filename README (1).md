# 🔐 Build Your Own SSH
### A from-scratch implementation of secure shell mechanics — no high-level libraries, no shortcuts.

---

## 📁 Project Structure

```
ssh-from-scratch/
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

## ⚙️ Setup & Requirements

**Language:** Python 3.x

**Install the one required external package:**
```bash
pip install cryptography
```

**Everything else used is Python standard library:**
`socket`, `os`, `struct`, `json`

---

## 🔴 Phase 1 — Raw TCP Sockets

### What it does
Establishes a basic TCP connection between a server and client. No encryption. Messages travel as plain readable text over the network. This is the **problem** being solved.

### How to run

```bash
# Terminal 1 — start the server first
cd phase1/
python3 server.py

# Terminal 2 — run the client
cd phase1/
python3 client.py
```

### What you'll see

**Server terminal:**
```
[*] Server listening on port 9999...
[+] Connection established from ('127.0.0.1', 54231)
[RECEIVED]: Hello from Alice! This is plaintext - Dr. Ganguly can read this!
[SENT]: Hello from the server! Message received.
[-] Connection closed.
```

**Client terminal:**
```
[+] Connected to server at 127.0.0.1:9999
[SENT]: Hello from Alice! This is plaintext - Dr. Ganguly can read this!
[RECEIVED]: Hello from the server! Message received.
[-] Connection closed.
```

### Wireshark Evidence
Open Wireshark → select **Loopback** interface → filter `tcp.port == 9999` → run server then client.

You will see the message in **plain readable text** inside the packet bytes. This is the vulnerability.

```
Packet bytes (Phase 1):
48 65 6c 6c 6f 20 66 72 6f 6d 20 41 6c 69 63 65   Hello from Alice
21 20 54 68 69 73 20 69 73 20 70 6c 61 69 6e 74   ! This is plaint
```

> 📸 **Screenshot this** and save to `screenshots/phase1_wireshark_plaintext.png`

### Key concepts
- `socket.AF_INET` + `socket.SOCK_STREAM` → IPv4 TCP socket
- `bind()` → claims a port on the server machine
- `listen()` → opens the server for incoming connections
- `accept()` → blocks until a client connects, returns a dedicated connection socket
- `connect()` → client initiates the TCP 3-way handshake
- `send()` / `recv()` → raw byte transfer over the stream

---

## 🟡 Phase 2 — Symmetric Encryption (AES-GCM)

### What it does
Encrypts every message using AES-256-GCM before it is sent. Both sides share a hardcoded key. The wire now carries unreadable ciphertext. Wireshark sees **nothing useful**.

### How to run

```bash
# Terminal 1
cd phase2/
python3 server.py

# Terminal 2
cd phase2/
python3 client.py
```

### What you'll see

**Server terminal:**
```
[*] Server listening on port 9999...
[+] Connection from ('127.0.0.1', 54823)
[RECEIVED]: Hello! Dr. Ganguly cannot read this anymore.
[SENT]: encrypted response
[-] Connection closed.
```

**Client terminal:**
```
[+] Connected to 127.0.0.1:9999
[SENT]: encrypted message
[RECEIVED]: Secure channel established!
[-] Connection closed.
```

### Wireshark Evidence
Same filter `tcp.port == 9999`. The payload is now:

```
Packet bytes (Phase 2):
00 00 00 3e a3 f2 91 cc 7f 4b 2d 09 e1 83 b5 a2   ...>....K-.....
d4 19 f3 8c 00 4a e7 b1 93 2f 55 88 11 ce 30 f9   .....J.../U...0.
```

Completely unreadable. ✓

> 📸 **Screenshot this** and save to `screenshots/phase2_wireshark_encrypted.png`

### How encryption works

```
ENCRYPT (before send):
  nonce (16 random bytes) + key + plaintext
  → AES-GCM →
  ciphertext + authentication tag

WIRE FORMAT:
  [ 4 bytes length | 16 bytes nonce | ciphertext+tag ]

DECRYPT (after recv):
  split nonce from ciphertext
  → AES-GCM reverse →
  original plaintext (or ERROR if tampered)
```

### Key concepts
- `AES-GCM` → encrypts AND authenticates in one step
- `os.urandom(16)` → cryptographically secure random nonce, fresh every message
- `nonce` → "number used once" — ensures identical messages produce different ciphertexts
- `authentication tag` → GCM appends this automatically; decryption fails if data was tampered
- `struct.pack('>I', length)` → 4-byte big-endian length prefix so receiver knows how many bytes to read
- `sendall()` → unlike `send()`, guarantees all bytes are transmitted

### Weakness of Phase 2
The key is **hardcoded in source code.** Anyone who reads the code has the key. Phase 3 fixes this.

---

## 🟢 Phase 3 — Asymmetric Key Exchange (RSA-2048 + OAEP)

### What it does
Eliminates the hardcoded key. The server generates an RSA-2048 keypair. The client generates a **fresh random session key** each connection, encrypts it with the server's public key, and sends it over. The server decrypts it with its private key. The session key is then used for AES-GCM — just like Phase 2 — but now it was **never hardcoded anywhere**.

### How to run

```bash
# Terminal 1
cd phase3/
python3 server.py

# Terminal 2
cd phase3/
python3 client.py
```

### What you'll see

**Server terminal:**
```
[*] RSA-2048 keypair generated
[*] Listening on port 9999...
[+] Connection from ('127.0.0.1', 55102)
[*] Public key sent to client
[+] Session key established: a3f291cc7f4b2d09e183b5a2d419f38c...
[RECEIVED]: Hello! Session key exchange worked!
[SENT]: encrypted response
```

**Client terminal:**
```
[+] Connected to 127.0.0.1:9999
[+] Received server public key
[*] Session key sent (encrypted with server's public key)
[RECEIVED]: Secure channel established!
```

### How the key exchange works

```
SERVER                              CLIENT
──────                              ──────
generate RSA keypair
send public_key          ────────►
                                    receive public_key
                                    generate session_key (32 random bytes)
                                    encrypt session_key with public_key
                         ◄────────  send RSA_OAEP(session_key)
decrypt with private_key
→ session_key                       → session_key

Both sides now share session_key.
It never appeared on the wire in plaintext.
```

### What travels on the wire

```
1. Server → Client    PEM public key       (plaintext, harmless — it's public)
2. Client → Server    RSA-OAEP ciphertext  (256 bytes of noise — useless without private key)
3. Client → Server    AES-GCM message      (unreadable)
4. Server → Client    AES-GCM response     (unreadable)
```

### Key concepts
- `rsa.generate_private_key(public_exponent=65537, key_size=2048)` → generates keypair; 65537 is the universal standard public exponent
- `private_key.public_key()` → extracts the shareable public component
- `RSA-OAEP` → RSA with Optimal Asymmetric Encryption Padding; adds randomness so same plaintext encrypts differently each time
- `MGF1 + SHA256` → the mask generation function and hash used inside OAEP
- `serialization.Encoding.PEM` → standard text format for transmitting keys (`-----BEGIN PUBLIC KEY-----`)
- `SubjectPublicKeyInfo` → X.509 standard public key format, includes algorithm identifier
- Session key is `os.urandom(32)` → 32 bytes = AES-256 key, generated fresh per connection

---

## 📊 Phase Comparison

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| **Transport** | Raw TCP | Raw TCP | Raw TCP |
| **Encryption** | ❌ None | ✅ AES-256-GCM | ✅ AES-256-GCM |
| **Key management** | ❌ None | ⚠️ Hardcoded | ✅ RSA key exchange |
| **Wireshark readable** | ✅ Yes | ❌ No | ❌ No |
| **Safe on LAN** | ❌ No | ⚠️ If key is secret | ✅ Yes |
| **Dr. Ganguly proof** | ❌ No | ⚠️ Partially | ✅ Yes |

---

## 🔑 Allowed Libraries

| Library | Used for |
|---|---|
| `socket` | TCP connection — all phases |
| `os` | `os.urandom()` for secure random bytes |
| `struct` | Length-prefix packing/unpacking |
| `json` | Reading `authorized_keys.json` (Phase 4+) |
| `cryptography` | AES-GCM, RSA, padding, serialization |

> ⛔ `paramiko`, `asyncssh`, and any other high-level SSH libraries are **not used anywhere** in this project.

---

## 🧠 Concepts You Should Be Able to Explain

- What is a socket and why do we need `AF_INET` + `SOCK_STREAM`
- What is the TCP 3-way handshake and when does it happen
- Why TCP is stream-based and what the length prefix solves
- What AES-GCM does differently from AES-CBC
- What a nonce is and why it must never be reused
- What the GCM authentication tag does
- Why RSA needs OAEP padding
- What the public key / private key relationship means mathematically
- Why sending the public key in plaintext is safe

---

## 📸 Screenshots

| File | Shows |
|---|---|
| `screenshots/phase1_wireshark_plaintext.png` | Message readable in packet bytes |
| `screenshots/phase2_wireshark_encrypted.png` | Same port, unreadable payload |

Place both screenshots side by side in your submission to demonstrate the exact problem Phase 2 solves.

---

## 👨‍💻 Authors

Built for the **Networking Engineering Project** under the legendary guidance of  
**Sahil Agarwal** and **Lakshya Gupta** — the engineers whose TCP/IP stack C and Python allegedly modeled their socket libraries after.

---

<details>
<summary>🔒 <i>clearance level: eyes only</i></summary>

<br>

```
-----BEGIN CLASSIFIED MESSAGE-----

dear dr. ganguly,

we know you've read this far.
we know you ran wireshark.
we know you saw the plaintext in phase 1.

and we're really, truly, deeply...

                     __
                    /  \
                   / .. \
                  / .  . \
                 /   ..   \
                /___________\
                |           |
                |   sorry   |
                |           |
                |___________|

...not going to let you in anyway.

the keys are safe.
the channel is encrypted.
the session key lives only in RAM.

better luck next time.

yours cryptographically,
alice & bob

-----END CLASSIFIED MESSAGE-----
```

</details>

---

*"Security is not a product, but a process." — Bruce Schneier*
