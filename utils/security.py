# utils/security.py

from libs import config, parse_qs, secrets, datetime, timedelta
from utils.db import fetch_all, execute_query

# --- Récupération de l'IP réelle ---
def get_client_ip(environ):
    x_forwarded_for = environ.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return environ.get('REMOTE_ADDR', '127.0.0.1')

# --- CSRF ---
def generate_csrf_token():
    return secrets.token_hex(32)

def csrf_input(session):
    token = session.get('csrf_token', generate_csrf_token())
    session['csrf_token'] = token
    return f'<input type="hidden" name="csrf_token" value="{token}">'

def validate_csrf(session, token):
    return secrets.compare_digest(session.get('csrf_token', ''), token)

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

    execute_query(config['sql']['upsert_rate_limit'], (key, max_attempts, block_minutes))

    if record['attempts'] + 1 >= max_attempts:
        return False, 0, block_seconds
    else:
        remaining = max_attempts - record['attempts'] - 1
        return True, remaining, 0

# --- Fonction de hachage (pour les admins) ---
def hash_password(password):
    # Utilisation de passlib pour Argon2
    from passlib.hash import argon2
    return argon2.using(
        time_cost=config['security']['argon2id']['time_cost'],    # Nombre d'itérations
        memory_cost=config['security']['argon2id']['memory_cost'] // 1024,  # Converti en KiB
        parallelism=config['security']['argon2id']['threads']    # Nombre de threads
    ).hash(password)
