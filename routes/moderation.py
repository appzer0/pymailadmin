# routes/moderation.py

from utils.db import fetch_all, execute_query
from utils.email import send_email
from handlers.html import html_template
import logging

def notify_admin_for_approval(email, role, reason):
    # Fetch admins
    admins = fetch_all(config['sql']['select_admins_for_moderation'], ())
    if not admins:
        print("No admin found.")
        return

    for admin in admins:
        send_email(
            to_email=admin['email'],
            subject='[pymailadmin] Register Requests',
            body=f"Email: {email}\nRole: {role}\nReason: {reason}\nAccept: https://mailadmin.liberta.email/moderate/pending\nDecline: https://mailadmin.liberta.email/moderate/deny?email={email}"
        )

# -- Signup confirmation --
def confirm_registration_handler(environ, start_response):
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    hash_param = params.get('hash', [''])[0]

    if not hash_param:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Missing hash"]

    # Check request
    registration = fetch_all(config['sql']['select_admin_registration_by_hash_unconfirmed'], (hash_param,))
    if not registration:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [b"Invalid confirmation or already processed"]

    reg = registration[0]

    # Mark as confirmed
    execute_query(config['sql']['confirm_admin_registration'], (reg['id'],))

    # Send confirmation link to user:
    send_email(
        to_email=reg['email'],
        subject='[pymailadmin] Confirm your registration',
        body=f"Confirm by clicking on: https://mailadmin.liberta.email/register/confirm?hash={hash_param}"
    )
    
    # Send to admins
    notify_admin_for_approval(reg['email'], reg['role'], reg['reason'])

    # Reply to confirmation link:
    content = "<p>Your registration has been confirmed! It is now pending for review and validation by an admin.</p>"
    body = html_template("Registration confirmed, pending for validation", content)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]

# -- Confirm registrations on moderation admin --
def approve_registration_handler(environ, start_response):
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/html")])
        return [b"POST only"]

    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Forbidden access"]

    # 1. Read data
    content_length = int(environ.get('CONTENT_LENGTH', 0))
    post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
    data = parse_qs(post_data)

    # 2. Extract email
    email = data.get('email', [''])[0].strip()
    csrf_token = data.get('csrf_token', [''])[0]

    # 3. Validate CSRF token
    if not session.validate_csrf_token(csrf_token):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Invalid CSRF token"]

    # 4. Fetch registration
    reg = fetch_all(config['sql']['select_admin_registration_by_email_unconfirmed'], (email,))
    if not reg:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [b"User not found."]
    reg = reg[0]

    # 5. Insert in admin_users as simple mailbox user
    try:
        execute_query(config['sql']['insert_user_from_registration'], (email, reg['password_hash'], reg['role']))
    except Exception as e:
        logging.error(f"Eror when inserting new user: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [b"Could not approve registration."]

    # 6.Delete from admin_registrations
    execute_query(config['sql']['delete_registration_by_email'], (email,))

    # 7. Redirect
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

# --- Decline registration ---
def deny_registration_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Forbidden access"]

    # Fetch email from URL
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    email = params.get('email', [''])[0].strip()

    if not email:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Missing email"]

    # Delete registration request
    execute_query(config['sql']['delete_registration_by_email'], (email,))

    # Redirect on pending requests
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

# -- Display pending requests --
def moderation_queue_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    # Vérifier rôle
    if session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Forbidden access"]

    # Récupérer les inscriptions en attente
    pending = fetch_all(config['sql']['select_pending_registrations'], ())

    rows = ""
    for p in pending:
        approve = f'<a href="/moderate/approve?email={p["email"]}"><button>Accept</button></a>'
        deny = f'<a href="/moderate/deny?email={p["email"]}"><button>Decline</button></a>'
        rows += f"<tr><td>{p['email']}</td><td>{p['role']}</td><td>{p['reason']}</td><td>{approve} {deny}</td></tr>"

    table = f"""
    <table border="1">
        <thead><tr><th>Email</th><th>Role</th><th>Reason</th><th>Actions</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """

    body = html_template("Registration moderation", table)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]
