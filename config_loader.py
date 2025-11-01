# config_loader.py

from dotenv import load_dotenv
import os
from config_data import config

load_dotenv()

# Guess prefix for dovecot
def determine_prefix(algorithm):
    algo = algorithm.lower()
    if algo == 'argon2id':
        return '{ARGON2ID}'
    if algo == 'argon2i':
        return '{ARGON2I}'
    if algo == 'bcrypt':
        return '{BCRYPT}'
    if algo == 'sha512-crypt':
        return '{SHA512-CRYPT}'
    if algo == 'sha256-crypt':
        return '{SHA256-CRYPT}'
    if algo == 'pbkdf2':
        return '{PBKDF2}'
    return '{ARGON2ID}'

# Load database schema variables
def load_db_schema():
    """Load database table and field names from .env"""
    return {
        # Domains table
        'table_domains': os.getenv('DB_TABLE_DOMAINS', 'domain'),
        'field_domain_id': os.getenv('DB_FIELD_DOMAIN_ID', 'id'),
        'field_domain_name': os.getenv('DB_FIELD_DOMAIN_NAME', 'domain'),
        
        # Users table
        'table_users': os.getenv('DB_TABLE_USERS', 'users'),
        'field_user_id': os.getenv('DB_FIELD_USER_ID', 'id'),
        'field_user_domain_id': os.getenv('DB_FIELD_USER_DOMAIN_ID', 'domain_id'),
        'field_user_email': os.getenv('DB_FIELD_USER_EMAIL', 'email'),
        'field_user_password': os.getenv('DB_FIELD_USER_PASSWORD', 'crypt'),
        'field_user_quota': os.getenv('DB_FIELD_USER_QUOTA', 'quota'),
        'field_user_active': os.getenv('DB_FIELD_USER_ACTIVE', 'active'),
        
        # Aliases table
        'table_aliases': os.getenv('DB_TABLE_ALIASES', 'alias'),
        'field_alias_id': os.getenv('DB_FIELD_ALIAS_ID', 'id'),
        'field_alias_domain_id': os.getenv('DB_FIELD_ALIAS_DOMAIN_ID', 'domain_id'),
        'field_alias_source': os.getenv('DB_FIELD_ALIAS_SOURCE', 'source'),
        'field_alias_destination': os.getenv('DB_FIELD_ALIAS_DESTINATION', 'destination'),
    }

def generate_sql_queries(schema):
    """Generate SQL queries based on schema configuration"""
    
    # Domains queries
    sql_domains = {
        'select_domain_by_name': f"SELECT * FROM {schema['table_domains']} WHERE {schema['field_domain_name']} = %s",
        'select_domain_by_id': f"SELECT * FROM {schema['table_domains']} WHERE {schema['field_domain_id']} = %s",
        'select_all_domains': f"SELECT {schema['field_domain_id']}, {schema['field_domain_name']} FROM {schema['table_domains']}",
    }
    
    # Users queries
    sql_users = {
        'insert_user': f"INSERT INTO {schema['table_users']} ({schema['field_user_domain_id']}, {schema['field_user_email']}, {schema['field_user_password']}, {schema['field_user_quota']}, {schema['field_user_active']}) VALUES (%s, %s, %s, %s, %s)",
        'select_user_by_id_in': f"SELECT * FROM {schema['table_users']} WHERE {schema['field_user_id']} IN ({{user_ids}})",
        'select_users_by_domain': f"SELECT * FROM {schema['table_users']} WHERE {schema['field_user_domain_id']} = %s",
        'select_user_by_id': f"SELECT * FROM {schema['table_users']} WHERE {schema['field_user_id']} = %s",
        'select_user_by_email': f"SELECT * FROM {schema['table_users']} WHERE {schema['field_user_email']} = %s",
        'update_user_password': f"UPDATE {schema['table_users']} SET {schema['field_user_password']} = %s WHERE {schema['field_user_id']} = %s",
        'update_user_email': f"UPDATE {schema['table_users']} SET {schema['field_user_email']} = %s WHERE {schema['field_user_id']} = %s",
        'disable_user': f"UPDATE {schema['table_users']} SET {schema['field_user_active']} = 0 WHERE {schema['field_user_email']} = %s",
        'delete_user': f"DELETE FROM {schema['table_users']} WHERE {schema['field_user_id']} = %s",
        
        # Hybrid query with pymailadmin_ownerships
        'count_active_mailboxes_by_owner': f"""
            SELECT COUNT(*) as count 
            FROM pymailadmin_ownerships o
            INNER JOIN {schema['table_users']} u ON o.user_id = u.{schema['field_user_id']}
            LEFT JOIN pymailadmin_deletion_pending dp ON u.{schema['field_user_email']} = dp.email
            WHERE o.admin_user_id = %s AND dp.email IS NULL
        """,
        
        # Reactivate after rekey timeout
        'reactivate_user_after_rekey_timeout': f"""
            UPDATE {schema['table_users']} 
            INNER JOIN (
                SELECT email FROM pymailadmin_rekey_pending 
                WHERE created_at < NOW() - INTERVAL %s MINUTE
            ) AS expired ON {schema['table_users']}.{schema['field_user_email']} = expired.email 
            SET {schema['table_users']}.{schema['field_user_active']} = 1
        """,
    }
    
    # Aliases queries
    sql_aliases = {
        'insert_alias': f"INSERT INTO {schema['table_aliases']} ({schema['field_alias_domain_id']}, {schema['field_alias_source']}, {schema['field_alias_destination']}) VALUES (%s, %s, %s)",
        'select_alias_by_id': f"SELECT * FROM {schema['table_aliases']} WHERE {schema['field_alias_id']} = %s",
        'select_alias_by_domain': f"SELECT * FROM {schema['table_aliases']} WHERE {schema['field_alias_domain_id']} = %s",
        'select_alias_by_mailbox': f"SELECT * FROM {schema['table_aliases']} WHERE {schema['field_alias_domain_id']} = %s AND {schema['field_alias_destination']} = %s",
        'select_alias_by_source': f"SELECT * FROM {schema['table_aliases']} WHERE {schema['field_alias_source']} = %s",
        'count_aliases_by_mailbox': f"SELECT COUNT(*) as count FROM {schema['table_aliases']} WHERE {schema['field_alias_destination']} = %s",
        'update_alias': f"UPDATE {schema['table_aliases']} SET {schema['field_alias_source']} = %s, {schema['field_alias_destination']} = %s WHERE {schema['field_alias_id']} = %s",
        'delete_alias': f"DELETE FROM {schema['table_aliases']} WHERE {schema['field_alias_id']} = %s",
    }
    
    # Merge all queries
    return {**sql_domains, **sql_users, **sql_aliases}

# Dynamic configuration loader
dynamic_config = {
    'SECRET_KEY': os.getenv('SECRET_KEY'),
    'PRETTY_NAME': os.getenv('PRETTY_NAME', 'pymailadmin'),
    'PYMAILADMIN_URL': os.getenv('PYMAILADMIN_URL', 'https://mailadmin.liberta.email'),
    
    'limits': {
        'max_mailboxes_per_user': int(os.getenv('MAX_MAILBOXES_PER_USER', 3)),
        'max_aliases_per_mailbox': int(os.getenv('MAX_ALIASES_PER_MAILBOX', 100))
    },
    
    'security': {
        'argon2id': {
            'time_cost': int(os.getenv('ADMIN_HASH_TIME_COST', 3)),
            'memory_cost': int(os.getenv('ADMIN_HASH_MEMORY_COST', 65536)),
            'threads': int(os.getenv('ADMIN_HASH_PARALLELISM', 2))
        },
        'rate_limit': {
            'login': {
                'max_attempts': int(os.getenv('LOGIN_MAX_ATTEMPTS', 5)),
                'window_minutes': int(os.getenv('LOGIN_WINDOW_MINUTES', 15)),
                'block_minutes': int(os.getenv('LOGIN_BLOCK_MINUTES', 30))
            },
            'register': {
                'max_attempts_per_ip': int(os.getenv('REGISTER_MAX_ATTEMPTS_PER_IP', 3)),
                'window_minutes': int(os.getenv('REGISTER_WINDOW_MINUTES', 60)),
                'block_minutes': int(os.getenv('REGISTER_BLOCK_MINUTES', 60))
            }
        }
    },
    
    'mailbox_hash': {
        'algorithm': os.getenv('DOVECOT_HASH', 'argon2id').lower(),
        'prefix': os.getenv('DOVECOT_HASH_PREFIX') or determine_prefix(os.getenv('DOVECOT_HASH', 'argon2id')),
        'argon2_time_cost': int(os.getenv('DOVECOT_ARGON2_TIME_COST', 3)),
        'argon2_memory_cost': int(os.getenv('DOVECOT_ARGON2_MEMORY_COST', 65536)),
        'argon2_parallelism': int(os.getenv('DOVECOT_ARGON2_PARALLELISM', 2)),
        'bcrypt_rounds': int(os.getenv('DOVECOT_BCRYPT_ROUNDS', 12)),
        'pbkdf2_rounds': int(os.getenv('DOVECOT_PBKDF2_ROUNDS', 480000)),
    },
    
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

    # Dovecot SQL requests — AUTO-GENERATED from schema
    'sql_dovecot': None  # Will be populated by load_config()
}

def load_config():
    """Load complete configuration with auto-generated SQL queries"""
    
    required_env = [
        'SECRET_KEY', 'MAIL_SMTP_HOST', 'MAIL_FROM_EMAIL',
        'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'
    ]

    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Error: Missing variables in .env : {', '.join(missing)}")
    
    # Load database schema configuration
    schema = load_db_schema()
    
    # Generate SQL queries based on schema
    sql_queries = generate_sql_queries(schema)
    
    # Inject generated queries into dynamic_config
    dynamic_config['sql_dovecot'] = sql_queries
    
    # Merge configurations
    full_config = {**config, **dynamic_config}
    
    return full_config
