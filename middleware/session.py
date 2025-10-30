# middleware/session.py

import uuid
import hmac
import hashlib
import json
from datetime import datetime, timedelta
import secrets
from urllib.parse import parse_qs

from libs import config, fetch_all, execute_query

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

    def get_csrf_token(self):
        if 'csrf_token' not in self.data:
            self.data['csrf_token'] = secrets.token_hex(32)
        return self.data['csrf_token']

    def validate_csrf_token(self, token):
        if not token or 'csrf_token' not in self.data:
            return False
        return secrets.compare_digest(self.data['csrf_token'], token)

    def save(self):
        if not self.id:
            self.id = uuid.uuid4().hex
        data_json = json.dumps(self.data, cls=DateTimeEncoder)
        expires_at = datetime.now() + timedelta(hours=24)
        execute_query(config['sql']['insert_session'], (self.id, data_json, expires_at))
        return self.id

def sign_session_id(session_id, secret):
    return session_id + '.' + hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()

def is_valid_session_id(session_id, secret):
    if '.' not in session_id:
        return False
    sid, signature = session_id.rsplit('.', 1)
    expected = hmac.new(secret.encode(), sid.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

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

        session_id = cookies.get('session_id', '')
        session = Session()

        if session_id and is_valid_session_id(session_id, secret):
            unsigned_id = session_id.rsplit('.', 1)[0]
            session.id = unsigned_id
            records = fetch_all(config['sql']['select_session_by_id'], (unsigned_id,))
            if records:
                session.data = json.loads(records[0]['data'])
        else:
            # Generate now session ID if absent or invalid
            session.id = uuid.uuid4().hex
        
        environ['session'] = session

        def custom_start_response(status, headers, exc_info=None):
            if not is_valid_session_id(f"{session.id}.{hmac.new(secret.encode(), session.id.encode(), hashlib.sha256).hexdigest()}", secret):
                session.save()
            signed_sid = sign_session_id(session.id, secret)
            secure_flag = "; Secure" if environ.get('wsgi.url_scheme') == 'https' else ""
            headers.append(('Set-Cookie', f'session_id={signed_sid}; Path=/; HttpOnly;{secure_flag}'))
            return start_response(status, headers, exc_info)

        return app(environ, custom_start_response)

    return middleware
