# libs/__init__.py

import os
from dotenv import load_dotenv

load_dotenv()

# Import load_config and static config
from config_loader import load_config
from config_data import config as static_config

# Load merged config
config = None

def get_config():
    global config
    if config is None:
        dynamic_config = load_config()
        config = {**static_config, **dynamic_config}
    return config

# Expose config object
config = get_config()

import time
import secrets
from urllib.parse import parse_qs
from datetime import datetime, timedelta
from config_loader import load_config
from utils.db import execute_query, fetch_all
from email.mime.text import MIMEText
import smtplib
from passlib.hash import argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from i18n import get_translations
translations = get_translations()

__all__ = ['config', 'execute_query', 'fetch_all', 'parse_qs', 'datetime', 'timedelta', 'secrets', 'smtplib', 'argon2', 'translations']
