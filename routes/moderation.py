# routes/moderation.py

from utils.db import fetch_all, execute_query
from utils.email import send_email
from handlers.html import html_template
from libs import translations, config, parse_qs
import logging

PYMAILADMIN_URL = config['PYMAILADMIN_URL']
PRETTY_NAME = config['PRETTY_NAME']

def notify_admin_for_approval(email, role, reason):
    admins = fetch_all(config['sql']['select_admins_for_moderation'], ())
    if not admins:
        return
    approve_url = f"{PYMAILADMIN_URL}/moderate/approve?email={email}"
    deny_url = f"{PYMAILADMIN_URL}/moderate/deny?email={email}"
    body_template = translations['email_moderation_body']
    body = body_template.format(email=email, role=role, reason=reason, approve_url=approve_url, deny_url=deny_url)
    subject = f"[{PRETTY_NAME}] {translations['email_moderation_subject']}"
    
    for admin in admins:
        send_email(
            to_email=admin['email'],
            subject=translations['email_moderation_subject'],
            body=body
        )

def confirm_registration_handler(environ, start_response):
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    hash_param = params.get('hash', [''])[0]
    if not hash_param:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [translations['missing_hash'].encode('utf-8')]
    registration = fetch_all(config['sql']['select_admin_registration_by_hash_unconfirmed'], (hash_param,))
    if not registration:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [translations['invalid_hash'].encode('utf-8')]
    reg = registration[0]
    execute_query(config['sql']['confirm_admin_registration'], (reg['id'],))
    
    # Send confirmation link
    confirm_url = f"{PYMAILADMIN_URL}/register/confirm?hash={hash_param}"
    email_body = translations['email_confirm_body'].format(confirm_url=confirm_url)
    subject = f"[{PRETTY_NAME}] {translations['email_confirm_subject']}"
    send_email(reg['email'], subject, email_body)
    
    # Notify admins
    notify_admin_for_approval(reg['email'], reg['role'], reg['reason'])
    
    # Response
    content = f"<p>{translations['pending_confirmation']}</p>"
    body = html_template(translations['pending_title'], content)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]

def approve_registration_handler(environ, start_response):
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/html")])
        return [translations['method_not_allowed'].encode('utf-8')]
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    content_length = int(environ.get('CONTENT_LENGTH', 0))
    post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
    data = parse_qs(post_data)
    email = data.get('email', [''])[0].strip()
    csrf_token = data.get('csrf_token', [''])[0]
    if not session.validate_csrf_token(csrf_token):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['csrf_invalid'].encode('utf-8')]
    reg = fetch_all(config['sql']['select_admin_registration_by_email_unconfirmed'], (email,))
    if not reg:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [translations['user_not_found'].encode('utf-8')]
    reg = reg[0]
    try:
        execute_query(config['sql']['insert_user_from_registration'], (email, reg['password_hash'], reg['role']))
        execute_query(config['sql']['delete_registration_by_email'], (email,))
    except Exception as e:
        logging.error(f"Error approving: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [translations['approval_failed'].encode('utf-8')]
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

def deny_registration_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    email = params.get('email', [''])[0].strip()
    if not email:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [translations['missing_email'].encode('utf-8')]
    execute_query(config['sql']['delete_registration_by_email'], (email,))
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

def moderation_queue_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []
    if session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    pending = fetch_all(config['sql']['select_pending_registrations'], ())
    rows = ""
    for p in pending:
        approve = f'<a href="/moderate/approve?email={p["email"]}"><button>{translations["approve_btn"]}</button></a>'
        deny = f'<a href="/moderate/deny?email={p["email"]}"><button>{translations["deny_btn"]}</button></a>'
        rows += f"<tr><td>{p['email']}</td><td>{p['role']}</td><td>{p['reason']}</td><td>{approve} {deny}</td></tr>"
    table = f"""
    <table border="1">
        <thead><tr>
            <th>{translations['moderation_email_col']}</th>
            <th>{translations['moderation_role_col']}</th>
            <th>{translations['moderation_reason_col']}</th>
            <th>{translations['moderation_actions_col']}</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    body = html_template(translations['moderation_title'], table)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]
