# utils/recovery.py

import random
import string

def generate_recovery_key():
    """
    Generate recovery key : eight 5-letters words + 5 digits,
    space-separated and sorted alphabetically
    """
    parts = []
    
    for _ in range(8):
        letters = ''.join(random.choices(string.ascii_lowercase, k=5))
        digits = str(random.randint(00001, 99999))
        parts.append(letters + digits)
    
    # Sort alphabetically
    parts.sort()
    return ' '.join(parts)

def generate_hint_from_key(key):
    """
    Hint for user to retrieve their recovery key
    Input : "abcde12345 [...] vwxyz12345" → Output : "ab......45"
    """
    first = key[:2]
    last = key[-3:]
    
    return f"{first}......{last[:-1]}"
