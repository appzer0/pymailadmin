# utils/alias_limits.py

from utils.db import fetch_all
from libs import config

def get_max_aliases():
    """
    Get the maximum number of aliases per mailbox from config.
    Falls back to 100 if not configured.
    """
    return config.get('limits', {}).get('max_aliases_per_mailbox', 100)

def get_alias_count(destination_email):
    """
    Count aliases for a given mailbox (destination).
    """
    result = fetch_all(
        config['sql_dovecot']['count_aliases_by_mailbox'], 
        (destination_email,)
    )
    return result[0]['count'] if result else 0

def can_create_alias(destination_email):
    """
    Check if an alias can be created for this mailbox.
    Returns (bool, current_count, max_count)
    """
    max_aliases = get_max_aliases()
    count = get_alias_count(destination_email)
    return (count < max_aliases, count, max_aliases)
