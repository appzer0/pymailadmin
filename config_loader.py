# config_loader.py

from dotenv import load_dotenv
import os
from config_data import config

load_dotenv()

# Dynamic configuration loader
dynamic_config = {
    'SECRET_KEY': os.getenv('SECRET_KEY'),

    'mail': {
        'smtp_host': os.getenv('MAIL_SMTP_HOST'),
        'smtp_port': int(os.getenv('MAIL_SMTP_PORT', 587)),
        'smtp_username': os.getenv('MAIL_SMTP_USERNAME'),
        'smtp_password': os.getenv('MAIL_SMTP_PASSWORD'),
        'smtp_protocol': os.getenv('MAIL_SMTP_PROTOCOL', 'ssl'),
        'smtp_auth': True,
        'smtp_debug': 1,
        'mailgun_api_url': os.getenv('MAILGUN_API_URL', 'https://api.mailgun.net/v3'),
        'mailgun_api_key': os.getenv('MAILGUN_API_KEY', ''),
        'mailgun_domain': os.getenv('MAILGUN_DOMAIN', ''),
        'from_email': os.getenv('MAIL_FROM_EMAIL'),
        'from_name': os.getenv('MAIL_FROM_NAME'),
        'smtp_options': {
            'ssl': {
                'verify_peer': True,
                'verify_peer_name': True,
                'allow_self_signed': False
            }
        },
        'smtp_timeout': 30,
    },

    'db': {
        'host': os.getenv('DB_HOST'),
        'dbname': os.getenv('DB_NAME'),
        'username': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'charset': os.getenv('DB_CHARSET', 'utf8mb4')
    },

    'paths': {
        'static_dir': os.getenv('STATIC_DIR', '/var/www/pymailadmin/static')
    },
    'css': {
        'main_css': os.getenv('CSS_MAIN', 'main.css')
    },

    # Dovecot SQL requests — from .env
    'sql_dovecot': {
        'insert_user': os.getenv('SQL_INSERT_USER'),
        'select_user_by_email': os.getenv('SQL_SELECT_USER_BY_EMAIL'),
        'update_user_password': os.getenv('SQL_UPDATE_USER_PASSWORD'),
        'update_user_email': os.getenv('SQL_UPDATE_USER_EMAIL'),
        'delete_user': os.getenv('SQL_DELETE_USER'),
        'select_users_by_domain': os.getenv('SQL_SELECT_USERS_BY_DOMAIN'),
        'select_user_by_id': os.getenv('SQL_SELECT_USER_BY_ID'),
        'disable_user': os.getenv('SQL_DISABLE_USER'),
        'reactivate_user_after_rekey_timeout': os.getenv('SQL_REACTIVATE_USER_AFTER_REKEY_TIMEOUT'),
        'insert_alias': os.getenv('SQL_INSERT_ALIAS'),
        'select_alias_by_id': os.getenv('SQL_SELECT_ALIAS_BY_ID'),
        'select_alias_by_domain': os.getenv('SQL_SELECT_ALIAS_BY_DOMAIN'),
        'select_alias_by_mailbox': os.getenv('SQL_SELECT_ALIAS_BY_MAILBOX'),
        'select_alias_by_source': os.getenv('SQL_SELECT_ALIAS_BY_SOURCE'),
        'update_alias': os.getenv('SQL_UPDATE_ALIAS'),
        'delete_alias': os.getenv('SQL_DELETE_ALIAS'),
        'select_domain_by_name': os.getenv('SQL_SELECT_DOMAIN_BY_NAME'),
        'select_all_domains': os.getenv('SQL_SELECT_ALL_DOMAINS'),
        'select_user_by_id_in': os.getenv('SQL_SELECT_USER_BY_ID_IN'),
    }
}

def load_config():
    required_env = [
        'SECRET_KEY', 'MAIL_SMTP_HOST', 'MAIL_FROM_EMAIL',
        'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'SQL_INSERT_USER', 'SQL_SELECT_USER_BY_EMAIL', 'SQL_UPDATE_USER_PASSWORD'
    ]

    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Error: Missing variables in .env : {', '.join(missing)}")
    
    full_config = {**config, **dynamic_config}
    full_config['security']['paths'] = dynamic_config['paths']
    full_config['security']['css'] = dynamic_config['css']
    return full_config
