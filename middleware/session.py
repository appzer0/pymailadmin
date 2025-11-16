# middleware/session.py

import uuid
import hmac
import hashlib
import json
from datetime import datetime, timedelta
import secrets
import logging

from libs import config, fetch_all, execute_query, parse_qs

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class Session:
    def __init__(self, session_id=None):
        self.id = session_id
        self.data = {}
        if session_id:
            records = fetch_all(config['sql']['select_session_by_id'], (session_id,))
            if records and records[0]['expires_at'] > datetime.now():
                self.data = json.loads(records[0]['data'])
                logging.info(f"Session loaded: {self.id} - data keys: {list(self.data.keys())}")
            else:
                logging.info(f"No valid session found for id: {session_id}")

    def get_csrf_token(self):
        if 'csrf_token' not in self.data:
            self.data['csrf_token'] = secrets.token_hex(32)
            logging.info(f"New CSRF token generated: {self.data['csrf_token']}")
        else:
            logging.info(f"Existing CSRF token used: {self.data['csrf_token']}")
        return self.data['csrf_token']

    def validate_csrf_token(self, token):
        stored_token = self.data.get('csrf_token', '')
        logging.info(f"Validating CSRF token. Stored: {stored_token}, Received: {token}")
        if not token or 'csrf_token' not in self.data:
            return False
        return secrets.compare_digest(stored_token, token)

    def save(self):
        if not self.id:
            self.id = uuid.uuid4().hex
        data_json = json.dumps(self.data, cls=DateTimeEncoder)
        expires_at = datetime.now() + timedelta(hours=24)
        execute_query(config['sql']['insert_session'], (self.id, data_json, expires_at))
        logging.info(f"Session saved: {self.id}")
        return self.id

def sign_session_id(session_id, secret):
    signature = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}.{signature}"

def is_valid_session_id(signed_session_id, secret):
    if '.' not in signed_session_id:
        return False
    session_id, signature = signed_session_id.rsplit('.', 1)
    expected_signature = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

def SessionMiddleware(app, secret=None):
    if secret is None:
        secret = config.get('SECRET_KEY', 'your-default-secret-key')

    def middleware(environ, start_response):
        cookies = {}
        if 'HTTP_COOKIE' in environ:
            for cookie in environ['HTTP_COOKIE'].split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value

        signed_session_id = cookies.get('session_id')
        session = None
        if signed_session_id and is_valid_session_id(signed_session_id, secret):
            session_id = signed_session_id.rsplit('.', 1)[0]
            session = Session(session_id=session_id)
        if session is None:
            session = Session()

        environ['session'] = session

        def custom_start_response(status, headers, exc_info=None):
            session.save()
            signed_sid = sign_session_id(session.id, secret)
            secure_flag = "; Secure" if environ.get('wsgi.url_scheme') == 'https' else ""
            headers.append(('Set-Cookie', f'session_id={signed_sid}; Path=/; HttpOnly;{secure_flag}'))
            return start_response(status, headers, exc_info)

        try:
            response = app(environ, custom_start_response)
            if response is None:
                logging.error("SessionMiddleware: app returned None")
                return [b"Internal Server Error: app returned None"]
            return response
        except Exception as e:
            logging.error(f"SessionMiddleware unexpected error: {e}", exc_info=True)
            return [b"Internal Server Error"]

    return middleware
