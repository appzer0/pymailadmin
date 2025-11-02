# routes/register.py

from libs import parse_qs, datetime, timedelta, config, translations
from utils.db import fetch_all, execute_query
from utils.email import send_email
from handlers.html import html_template
from utils.security import get_client_ip, check_rate_limit
import secrets
from passlib.hash import argon2
import logging

PYMAILADMIN_URL = config['PYMAILADMIN_URL']
PRETTY_NAME = config['PRETTY_NAME']

def register_handler(environ, start_response):
    session = environ['session']
    
    if session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/home")])
        return [b""]
    
    if environ['REQUEST_METHOD'] == 'GET':
        session.get_csrf_token()
        
        content = f"""
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label>{translations['email_label']}</label><br>
            <input type="email" name="email" required><br><br>
            <label>{translations['password_label']}</label><br>
            <input type="password" name="password" required><br><br>
            <input type="hidden" name="role" value="user">
            <label>{translations['reason_label']}</label><br>
            <textarea name="reason" required></textarea><br><br>
            <button type="submit">{translations['btn_register']}</button>
        </form>
        """
        
        body = html_template(translations['register_title'], content,admin_user_email=None,admin_role=None)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)

        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]

        email = data.get('email', [''])[0].strip()
        password = data.get('password', [''])[0]
        role = data.get('role', ['user'])[0]
        reason = data.get('reason', [''])[0].strip()

        if not email or '@' not in email:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['email_required'].encode('utf-8')]
        
        if not reason:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['reason_required'].encode('utf-8')]

        ip = get_client_ip(environ)
        rl = config['security']['rate_limit']['register']
        success, _, _ = check_rate_limit(f"ip:{ip}", rl['max_attempts_per_ip'], 60, 60)
        
        if not success:
            start_response("429 Too Many Requests", [("Retry-After", "3600")])
            return [translations['ip_rate_limited'].encode('utf-8')]

        password_hash = argon2.using(
            time_cost=config['security']['argon2id']['time_cost'],
            memory_cost=config['security']['argon2id']['memory_cost'] // 1024,
            parallelism=config['security']['argon2id']['threads']
        ).hash(password)

        confirmation_hash = secrets.token_urlsafe(64)
        expires_at = datetime.now() + timedelta(hours=48)

        try:
            
            execute_query(config['sql']['insert_admin_registration'],(email, password_hash, confirmation_hash, expires_at, reason))
        
        except Exception as e:
            logging.error(f"DB error during registration: {e}", exc_info=True)
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['internal_server_error'].encode('utf-8')]

        confirm_url = f"{PYMAILADMIN_URL}register/confirm?hash={confirmation_hash}"
        email_body_template = translations['email_confirm_body']
        email_body = email_body_template.format(confirm_url=confirm_url)
        subject = f"[{PRETTY_NAME}] {translations['email_confirm_subject']}"

        if not send_email(email, subject, email_body):
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['email_sent_failed'].encode('utf-8')]

        content = f"<p>{translations['registration_saved']}</p>"
        body = html_template(translations['register_title'], content)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]
