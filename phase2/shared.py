import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

#hardcoded key in phase2
SHARED_KEY = bytes.fromhex("0123456789abcdef" * 4) #64 char hex string, has 32 bytes. aes has 3 key sizes :16,24,32 bytes. 32 bytes is 256bit, the most secure

def encrypt(plaintext: bytes) -> bytes: #takes input of a bytes obj and return a bytes object
    nonce = os.urandom(16)          # random
    aesgcm = AESGCM(SHARED_KEY)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext       # bundle nonce with ciphertext

def decrypt(data: bytes) -> bytes:
    nonce = data[:16]               # first 16 bytes are nonce
    ciphertext = data[16:]          # rest = ciphertext+tag
    aesgcm = AESGCM(SHARED_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None)

def send_msg(sock, plaintext: bytes):
    encrypted = encrypt(plaintext)
    length = struct.pack('>I', len(encrypted))   # return 4 bytes of data, big-endian,
    sock.sendall(length + encrypted)

def recv_msg(sock) -> bytes:
    raw_len = sock.recv(4)                        # read the 4-byte length
    msg_len = struct.unpack('>I', raw_len)[0]     # convert to integer
    encrypted = sock.recv(msg_len)                # read exactly that many bytes
    return decrypt(encrypted)