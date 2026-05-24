import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    # no key hardcoding
    nonce = os.urandom(16)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext

def decrypt(data: bytes, key: bytes) -> bytes:
    nonce = data[:16]
    ciphertext = data[16:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

def send_msg(sock, plaintext: bytes, key: bytes):
    encrypted = encrypt(plaintext, key)
    length = struct.pack('>I', len(encrypted))
    sock.sendall(length + encrypted)

def recv_msg(sock, key: bytes) -> bytes:
    raw_len = sock.recv(4)
    msg_len = struct.unpack('>I', raw_len)[0]
    encrypted = sock.recv(msg_len)
    return decrypt(encrypted, key)

# new RSA functions

def serialize_public_key(public_key) -> bytes:
    # convert RSA public key object into raw bytes to send
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def deserialize_public_key(pem_bytes: bytes):
    # convertinf raw bytes received from socket into RSA public key object
    return serialization.load_pem_public_key(pem_bytes)

def rsa_encrypt(session_key: bytes, public_key) -> bytes:
    # encrypt 32byte session key with server public key
    return public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def rsa_decrypt(encrypted_session_key: bytes, private_key) -> bytes:
    # decrypts with server private key then recovers session key
    return private_key.decrypt(
        encrypted_session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
