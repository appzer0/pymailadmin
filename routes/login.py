# routes/login.py

from passlib.hash import argon2
from utils.security import get_client_ip, check_rate_limit
from utils.db import fetch_all, execute_query
from handlers.html import html_template
from libs import translations, parse_qs, config
from utils.check_super_admin_exists import check_super_admin_exists
import logging

def login_page(session, error_msg=None):
    """Display standard login page"""
    token = session.get_csrf_token()
    
    error_html = f'<p style="color: red; font-weight: bold;">{error_msg}</p>' if error_msg else ''
    
    content = f"""
    <div>
        {error_html}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{token}">
            
            <label for="email">{translations['email_label']}</label><br>
            <input type="email" id="email" name="email" placeholder="your@email.com" required><br>
            
            <label for="password">{translations['password_label']}</label><br>
            <input type="password" id="password" name="password" required><br>
            
            <button type="submit">
                {translations['btn_login']}
            </button>
        </form>
    </div>
    """
    return html_template(translations['login_title'], content)

def login_handler(environ, start_response):
    session = environ['session']
    
    if session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/home")])
        return [b""]
    
    session.save()

    if environ['REQUEST_METHOD'] == 'GET':
        session.get_csrf_token()
        start_response("200 OK", [("Content-Type", "text/html")])
        return [login_page(session).encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]
        
        email = data.get('email', [''])[0].strip()
        password = data.get('password', [''])[0]
        
        # Rate limiting
        if not session.data.get('logged_in'):
            ip = get_client_ip(environ)
            rl_config = config['security']['rate_limit']['login']
            success, _, retry_after = check_rate_limit(
                f"ip:{ip}",
                rl_config['max_attempts'],
                rl_config['window_minutes'],
                rl_config['block_minutes']
            )
            if not success:
                start_response("429 Too Many Requests", [
                    ("Content-Type", "text/html"),
                    ("Retry-After", str(retry_after))
                ])
                return [translations['too_many_attempts'].encode('utf-8')]

        # CSRF validation
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]

        # Email validation
        if not email or '@' not in email or '.' not in email:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [login_page(session, translations['invalid_email']).encode()]

        # Authenticate user
        user = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
        if user and argon2.verify(password, user[0]['password_hash']):
            session.data['logged_in'] = True
            session.data['email'] = email
            session.data['role'] = user[0]['role']
            session.data['id'] = user[0]['id']
            
            start_response("302 Found", [("Location", "/home")])
            return [b""]
        else:
            start_response("401 Unauthorized", [("Content-Type", "text/html")])
            return [login_page(session, translations['invalid_credentials']).encode()]
