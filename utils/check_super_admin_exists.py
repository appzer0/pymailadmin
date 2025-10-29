# utils/check_super_admin_exists.py

from libs import translations, parse_qs, config, execute_query, fetch_all
import logging

def check_super_admin_exists():
    try:
        result = fetch_all(config['sql']['count_super_admins'], ())
        return bool(result and result[0]['count'] > 0)
    except Exception as e:
        logging.error(f"Error checking super_admin existence: {e}")
        return False
