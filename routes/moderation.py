# routes/moderation.py

from utils.db import fetch_all, execute_query
from utils.email import send_email
from handlers.html import html_template
from libs import translations, config, parse_qs
import logging
import secrets

PYMAILADMIN_URL = config['PYMAILADMIN_URL']
PRETTY_NAME = config['PRETTY_NAME']

def notify_admin_for_approval(email, role, reason):
    admins = fetch_all(config['sql']['select_superadmins_for_moderation'], ())
    
    if not admins:
        return
    
    approve_url = f"{PYMAILADMIN_URL}/moderate/approve?email={email}"
    deny_url = f"{PYMAILADMIN_URL}/moderate/deny?email={email}"
    body_template = translations['email_moderation_body']
    body = body_template.format(email=email, reason=reason, approve_url=approve_url, deny_url=deny_url)
    subject = f"[{PRETTY_NAME}] {translations['email_moderation_subject']}"
    
    # Notify each superadmin by mail
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

    try:
        execute_query(config['sql']['confirm_admin_registration'], (reg['id'],))
        content = f"<p>{translations['pending_confirmation']}</p>"
        body = html_template(translations['pending_title'], content)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]
    
    except Exception as e:
        logging.error(f"Erreur confirmation: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [translations['internal_server_error'].encode('utf-8')]

def approve_registration_handler(environ, start_response):
    
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/html")])
        return [translations['method_not_allowed'].encode('utf-8')]

    session = environ.get('session')
    
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]

    content_length = int(environ.get('CONTENT_LENGTH', 0))
    post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
    data = parse_qs(post_data)
    email = data.get('email', [''])[0].strip()
    csrf_token = data.get('csrf_token', [''])[0]
    allowed_domains = data.get('allowed_domains', [])

    if not session.validate_csrf_token(csrf_token):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['csrf_invalid'].encode('utf-8')]

    reg = fetch_all(config['sql']['select_admin_registration_by_email_unconfirmed'], (email,))
    
    if not reg:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [translations['user_not_found'].encode('utf-8')]

    reg = reg[0]
    
    try:
        # Insert new mailbox
        execute_query(config['sql']['insert_user_from_registration'], (email, reg['password_hash'], 'user'))
        
        ### Trigger doveadm here
        
        # Get user ID
        user_row = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
        
        if not user_row:
            raise ValueError("User newly inserted not found")
        
        user_id = user_row[0]['id']
        
        # Insert allowed domains for new user
        for domain_id_str in allowed_domains:
            
            try:
                domain_id = int(domain_id_str)
                execute_query(config['sql']['insert_allowed_domains_for_user'], (user_id, domain_id))
            
            # No domains? OK then
            except ValueError:
                pass
        
        # Then cleanup registration
        execute_query(config['sql']['delete_registration_by_email'], (email,))
    
    except Exception as e:
        logging.error(f"Erreur: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [translations['approval_failed'].encode('utf-8')]
    
    # Send confirmed registration mail
    login_url = f"{PYMAILADMIN_URL}/login"
    email_body = translations['email_confirmed_registration_body'].format(login_url=login_url)
    subject = f"[{PRETTY_NAME}] {translations['email_confirmed_registration_subject']}"
    
    if not send_email(email, subject, email_body):
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [translations['email_sent_failed'].encode('utf-8')]

    start_response("302 Found", [("Location", "/moderate/pending")])
    return [b""]

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
    
    # Don't send any mail, just refuse registration silently and cleanup
    execute_query(config['sql']['delete_registration_by_email'], (email,))
    start_response("302 Found", [("Location", "/moderate/pending")])
    return [b""]

def moderation_queue_handler(environ, start_response):
    session = environ.get('session', None)
    
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]
    
    if session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    
    admin_user_email = session.data.get('email', '')
    admin_role = session.data.get('role', 'user')
    pending = fetch_all(config['sql']['select_pending_registrations'], ())
    rows = ""
    
    for p in pending:
        
        # Build domains list as checkboxes
        domains_checkboxes = ""
        
        for domain in domains:
            domains_checkboxes += f"""
                <label><input type="checkbox" name="allowed_domains" value="{domain["id"]}"> {domain["domain"]}</label><br>
            """
                
        approve = f"""
            <form method="POST" action="/moderate/approve">
                <input type="hidden" name="email" value="{p['email']}">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                <fieldset>
                    <legend>{translations["allowed_domains"]}</legend>
                    {domains_checkboxes}
                </fieldset>
                <button type="submit">{translations["approve_btn"]}</button>
            </form>
        """
        
        deny = f"""
            <form method="POST" action="/moderate/deny">
                <input type="hidden" name="email" value="{p['email']}">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                <button type="submit">{translations["deny_btn"]}</button>
            </form>
        """
        
        rows += f"<tr><td>{p['email']}</td><td>{p['reason']}</td><td>{approve} {deny}</td></tr>"
    
    table = f"""
    <table>
        <thead><tr>
            <th>{translations['moderation_email_col']}</th>
            <th>{translations['moderation_reason_col']}</th>
            <th>{translations['moderation_actions_col']}</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    
    body = html_template(translations['moderation_title'], table, admin_user_email=admin_user_email, admin_role=admin_role)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]
