# routes/moderation.py

from utils.db import fetch_all, execute_query
from utils.email import send_email
from handlers.html import html_template
import logging

def notify_admin_for_approval(email, role, reason):
    # Récupérer les admins
    admins = fetch_all(config['sql']['select_admins_for_moderation'], ())
    if not admins:
        print("Aucun admin trouvé")
        return

    for admin in admins:
        send_email(
            to_email=admin['email'],
            subject='[Liberta] Modération d’inscription',
            body=f"Email: {email}\nRôle: {role}\nMotif: {reason}\nApprouver: https://mailadmin.liberta.email/moderate/pending\nRejeter: https://mailadmin.liberta.email/moderate/deny?email={email}"
        )

# -- Confirmation d'inscription --
def confirm_registration_handler(environ, start_response):
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    hash_param = params.get('hash', [''])[0]

    if not hash_param:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Hash manquant"]

    # Vérifier la demande
    registration = fetch_all(config['sql']['select_admin_registration_by_hash_unconfirmed'], (hash_param,))
    if not registration:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [b"Confirmation invalide ou déjà traitée"]

    reg = registration[0]

    # Marquer comme confirmée
    execute_query(config['sql']['confirm_admin_registration'], (reg['id'],))

    # Envoyer au registrant
    send_email(
        to_email=reg['email'],
        subject='[Liberta] Confirmez votre inscription',
        body=f"Confirmez ici : https://mailadmin.liberta.email/register/confirm?hash={hash_param}"
    )
    
    # Envoyer aux admins
    notify_admin_for_approval(reg['email'], reg['role'], reg['reason'])

    # Réponse utilisateur
    content = "<p>Votre inscription a été confirmée ! Elle est maintenant en attente de validation par un admin.</p>"
    body = html_template("Inscription confirmée", content)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]

# -- Confirmation de l'insription en modération --
def approve_registration_handler(environ, start_response):
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/html")])
        return [b"POST only"]

    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Accès interdit"]

    # 1. Lire les données
    content_length = int(environ.get('CONTENT_LENGTH', 0))
    post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
    data = parse_qs(post_data)

    # 2. Extraire email
    email = data.get('email', [''])[0].strip()
    csrf_token = data.get('csrf_token', [''])[0]

    # 3. Valider CSRF
    if not session.validate_csrf_token(csrf_token):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Jeton CSRF invalide"]

    # 4. Récupérer l'inscription
    reg = fetch_all(config['sql']['select_admin_registration_by_email_unconfirmed'], (email,))
    if not reg:
        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [b"Utilisateur non trouvé"]
    reg = reg[0]

    # 5. Insérer dans admin_users
    try:
        execute_query(config['sql']['insert_user_from_registration'], (email, reg['password_hash'], reg['role']))
    except Exception as e:
        logging.error(f"Erreur insertion utilisateur: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [b"Échec de l'approbation"]

    # 6. Supprimer de admin_registrations
    execute_query(config['sql']['delete_registration_by_email'], (email,))

    # 7. Redirect
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

# --- Rejeter une inscription ---
def deny_registration_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Accès interdit"]

    # Récupérer l'email depuis l'URL
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    email = params.get('email', [''])[0].strip()

    if not email:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Email manquant"]

    # Supprimer la demande d'inscription
    execute_query(config['sql']['delete_registration_by_email'], (email,))

    # Rediriger vers la file d'attente
    start_response("302 Found", [("Location", "/moderate/pending")])
    return []

# -- Affichage des demandes en attente --
def moderation_queue_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    # Vérifier rôle
    if session.data.get('role') not in ['admin', 'super_admin']:
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Accès interdit"]

    # Récupérer les inscriptions en attente
    pending = fetch_all(config['sql']['select_pending_registrations'], ())

    rows = ""
    for p in pending:
        approve = f'<a href="/moderate/approve?email={p["email"]}"><button>Approuver</button></a>'
        deny = f'<a href="/moderate/deny?email={p["email"]}"><button>Rejeter</button></a>'
        rows += f"<tr><td>{p['email']}</td><td>{p['role']}</td><td>{p['reason']}</td><td>{approve} {deny}</td></tr>"

    table = f"""
    <table border="1">
        <thead><tr><th>Email</th><th>Rôle</th><th>Motif</th><th>Actions</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """

    body = html_template("Modération des inscriptions", table)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]
