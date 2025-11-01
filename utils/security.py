# utils/security.py

from libs import config, parse_qs, secrets, datetime, timedelta
from utils.db import fetch_all, execute_query
import secrets
import hmac
import hashlib
import time

# --- Get real IP ---
def get_client_ip(environ):
    x_forwarded_for = environ.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return environ.get('REMOTE_ADDR', '127.0.0.1')

# --- Rate Limiting ---
def check_rate_limit(key, max_attempts, window_minutes, block_minutes):
    window_seconds = window_minutes * 60
    block_seconds = block_minutes * 60
    now = datetime.now()

    existing = fetch_all(config['sql']['get_rate_limit'], (key,))
    
    if not existing:
        execute_query(config['sql']['upsert_rate_limit'], (key, max_attempts, block_minutes))
        return True, max_attempts - 1, 0

    record = existing[0]
    
    if record['blocked_until'] and record['blocked_until'] > now:
        retry_after = int((record['blocked_until'] - now).total_seconds())
        return False, 0, retry_after
        
    if record['blocked_until'] and record['blocked_until'] <= now:
        # Blocking expired, reset it
        execute_query(config['sql']['reset_rate_limit'], (key,))
    
    # Update rate limits
    execute_query(config['sql']['upsert_rate_limit'], (key, max_attempts, block_minutes))
    
    # Cleanup old expired blockings
    execute_query(config['sql']['delete_expired_rate_limits'])

    if record['attempts'] + 1 >= max_attempts:
        return False, 0, block_seconds
    else:
        remaining = max_attempts - record['attempts'] - 1
        return True, remaining, 0
