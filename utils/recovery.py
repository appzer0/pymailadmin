# utils/recovery.py

import random
import string
import os
import base64
import hashlib
from argon2 import PasswordHasher, exceptions
from Crypto.Cipher import AES

def generate_recovery_key():
    """
    Generate recovery key : eight 5-letters words + 5 digits,
    space-separated and sorted alphabetically
    """
    parts = []
    
    for _ in range(8):
        letters = ''.join(random.choices(string.ascii_lowercase, k=5))
        # We need 5 digits so we zfill(5)
        digits = str(random.randint(1, 99999)).zfill(5)
        parts.append(letters + digits)
    
    # Sort alphabetically
    parts.sort()
    return ' '.join(parts)

# Create hashing object
ph = PasswordHasher()

def encrypt_recovery(new_password: str, recovery_key: str) -> str:
    """
    Ecnrypt the password with the recovery key in an undecryptable way
    """
    # Concat password and recovery key for hashing
    combined = new_password + recovery_key
    return ph.hash(combined)

def verify_recovery(recovery_key: str, admin_password: str, stored_hash: str) -> bool:
    """
    Verify with the supplied, unstored recovery key
    """
    try:
        combined = admin_password + recovery_key
        ph.verify(stored_hash, combined)
        return True
    
    except exceptions.VerifyMismatchError:
        return False
    
    except Exception:
        return False

def derive_key_from_recovery_password(recovery_password: str) -> bytes:
    """
    Derive a key from the user's "recovery key" as the password
    """
    return hashlib.sha256(recovery_password.encode()).digest()

def encrypt_aes_gcm(key: bytes, plaintext: str) -> str:
    iv = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())
    combined = iv + tag + ciphertext
    return base64.b64encode(combined).decode()

def decrypt_aes_gcm(key: bytes, encoded: str) -> str:
    data = base64.b64decode(encoded.encode())
    iv, tag, ciphertext = data[:12], data[12:28], data[28:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode()

def generate_and_store_master_key(mb_password: str, recovery_password: str):
    master_key = os.urandom(32)
    enc_mb_password = encrypt_aes_gcm(master_key, mb_password)
    rec_key = derive_key_from_recovery_password(recovery_password)
    enc_master_key = encrypt_aes_gcm(rec_key, base64.b64encode(master_key).decode())
    return enc_master_key, enc_mb_password

def recover_mb_password(enc_master_key: str, enc_mb_password: str, recovery_password: str) -> str:
    rec_key = derive_key_from_recovery_password(recovery_password)
    master_key_b64 = decrypt_aes_gcm(rec_key, enc_master_key)
    master_key = base64.b64decode(master_key_b64.encode())
    mb_password = decrypt_aes_gcm(master_key, enc_mb_password)
    return mb_password
