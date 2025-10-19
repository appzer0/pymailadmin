# routes/login.py

from passlib.hash import argon2
from utils.security import get_client_ip, check_rate_limit
from utils.db import fetch_all
from handlers.html import html_template

# --- Génération des pages ---
def login_page(session):
    token = session.get_csrf_token()
    content = f"""
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{token}">
        <label for="email">Adresse email :</label><br>
        <input type="email" id="email" name="email" placeholder="votre@email.com" required><br><br>
        <label for="password">Mot de passe :</label><br>
        <input type="password" id="password" name="password" required><br><br>
        <button type="submit">Se connecter</button>
    </form>
    """
    return html_template("Connexion Administrateur", content)


def login_handler(environ, start_response):
    if environ['REQUEST_METHOD'] == 'GET':
        session = environ['session']
        
        if not session.id:
            session.save()  # Force la création d’un nouvel ID
        
        start_response("200 OK", [("Content-Type", "text/html")])
        return [login_page(session).encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        # 1. Lire les données
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)

        # 2. Extraire les champs
        email = data.get('email', [''])[0].strip()
        password = data.get('password', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]

        # 3. Récupérer l'IP réelle
        ip = get_client_ip(environ)

        # 4. Rate limiting
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
            return [b"Limite de tentatives dépassée. Essayez plus tard."]

        # 5. Valider le CSRF token
        session = environ['session']
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Jeton CSRF invalide"]

        # 6. Valider email
        if not email or '@' not in email:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Adresse email invalide"]

        # 7. Vérifier l'utilisateur
        user = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
        if user and argon2.verify(password, user[0]['password_hash']):
            # 8. Connexion réussie
            session.data['logged_in'] = True
            session.data['email'] = email
            session.data['role'] = user[0]['role']
            if not session.id:
                session.save()
            start_response("302 Found", [("Location", "/home")])
            return []
        else:
            start_response("401 Unauthorized", [("Content-Type", "text/html")])
            return [b"Identifiants incorrects"]
