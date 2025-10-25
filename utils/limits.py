# utils/limits.py

from utils.db import fetch_all
from libs import config

def get_max_mailboxes():
    return config.get('limits', {}).get('max_mailboxes_per_user', 3)

def get_mailbox_count(admin_user_id):
    result = fetch_all(
        config['sql_dovecot']['count_active_mailboxes_by_owner'], 
        (admin_user_id,)
    )
    return result[0]['count'] if result else 0

def can_create_mailbox(admin_user_id):
    max_mailboxes = get_max_mailboxes()
    count = get_mailbox_count(admin_user_id)
    return (count < max_mailboxes, count, max_mailboxes)
