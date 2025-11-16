# utils/recovery.py

import random
import string
from argon2 import PasswordHasher, exceptions

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

def encrypt_admin_mailbox(admin_mailbox: str, recovery_key: str) -> str:
    """
    Ecnrypt the mailbox name with the recovery key in an undecryptable way
    """
    # Concat mailbox and recovery key for hashing
    combined = admin_mailbox + recovery_key
    return ph.hash(combined)

def verify_admin_mailbox(recovery_key: str, admin_mailbox: str, stored_hash: str) -> bool:
    """
    Decrypt with the supplied, unstored recovery key
    """
    try:
        combined = admin_mailbox + recovery_key
        ph.verify(stored_hash, combined)
        return True
    
    except exceptions.VerifyMismatchError:
        return False
    
    except Exception:
        return False

