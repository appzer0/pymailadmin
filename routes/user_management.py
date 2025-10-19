# routes/user_management.py

from libs import config
from utils.db import fetch_all, execute_query
from handlers.html import html_template
import time
import logging
from libs import argon2
from libs import parse_qs

# --- Gestion des éditions d'aliases ---
def edit_alias_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        alias_id = params.get('id', [''])[0]

        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID invalide"]

        alias = fetch_all(config['sql']['select_alias_by_id'], (int(alias_id),))
        if not alias:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Alias non trouvé"]

        # Générer le formulaire d'édition
        form = f"""
        <form method="POST">
            <input type="hidden" name="alias_id" value="{alias_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="source">Source :</label><br>
            <input type="text" id="source" name="source" value="{alias[0]['source']}" required><br><br>
            <label for="destination">Destination :</label><br>
            <input type="email" id="destination" name="destination" value="{alias[0]['destination']}" required><br><br>
            <button type="submit">Modifier</button>
            <a href="/home"><button type="button">Annuler</button></a>
        </form>
        """
        body = html_template("Modifier un alias", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    # Gérer la requête POST (soumettre le formulaire)
    elif environ['REQUEST_METHOD'] == 'POST':
        # Lire les données POST
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Contenu de requête manquant"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        
        data = parse_qs(post_data)
        alias_id = data.get('alias_id', [''])[0]
        new_source = data.get('source', [''])[0].strip()
        new_destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Jeton CSRF invalide"]
        
        # Validation des entrées
        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID d'alias invalide"]
        if not new_source or not new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Champs requis manquants"]
        if '@' not in new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Adresse de destination invalide"]

        # Mettre à jour l'alias dans la base de données
        try:
            execute_query(config['sql']['update_alias'], (new_source, new_destination, int(alias_id)))
            start_response("302 Found", [("Location", "/home")])
            return []
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Erreur lors de la mise à jour de l'alias: {e}")
            return [b"Erreur lors de la mise à jour de l'alias"]

# --- Gestion des ajouts d'aliases ---
def add_alias_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    if environ['REQUEST_METHOD'] == 'GET':
        # Extraire la destination depuis l'URL
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        destination = params.get('destination', [''])[0]

        if not destination or '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Destination invalide"]

        # Générer le formulaire d'ajout
        form = f"""
        <form method="POST">
            <label for="source">Source :</label><br>
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <input type="text" id="source" name="source" required><br><br>
            <label for="destination">Destination :</label><br>
            <input type="email" id="destination" name="destination" value="{destination}" readonly required><br><br>
            <button type="submit">Ajouter l'alias</button>
            <a href="/home"><button type="button">Annuler</button></a>
        </form>
        """
        body = html_template("Ajouter un alias", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        # Lire et parser les données
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        source = data.get('source', [''])[0].strip()
        destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]

        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Jeton CSRF invalide"]

        # Validation
        if not source or not destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Champs requis manquants"]
        if '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Destination invalide"]

        # Vérifier si l'alias existe déjà
        existing = fetch_all(config['sql']['select_alias_by_source'], (source,))
        if existing:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            return [b"Un alias avec cette source existe déjà"]

        # Récupérer le domain_id pour la destination
        user = fetch_all(config['sql']['select_user_by_email'], (destination,))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Boîte mail de destination inconnue"]
        domain_id = user[0]['domain_id']

        # Insérer le nouvel alias
        try:
            execute_query(config['sql']['insert_alias'], (domain_id, source, destination))
            start_response("302 Found", [("Location", "/home")])
            return []
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Erreur lors de l'ajout de l'alias: {e}")
            return [b"Erreur lors de l'ajout de l'alias"]

# --- Gestion de l'édition d'une boîte mail ---
def edit_user_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        user_id = params.get('id', [''])[0]

        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID utilisateur invalide"]

        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Utilisateur non trouvé"]
  
        form = f"""
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="email">Adresse email :</label><br>
            <input type="email" id="email" name="email" value="{user[0]['email']}" required><br><br>
            <label for="password">Mot de passe (laisser vide pour ne pas changer) :</label><br>
            <input type="password" id="password" name="password"><br><br>
            <button type="submit">Modifier l'utilisateur</button>
            <a href="/home"><button type="button">Annuler</button></a>
        </form>
        """
        body = html_template("Modifier un utilisateur", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Contenu manquant"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        new_password = data.get('password', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Jeton CSRF invalide"]
        
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID invalide"]
        
        # Récupérer user_id ET vérifier ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Accès refusé : vous n'êtes pas propriétaire de cette boîte"]
        
        # Récupérer l’email original
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Utilisateur non trouvé"]
        
        email = user[0]['email']
    
        try:
            if new_password:
                # Hachage Argon2ID
                password_hash = argon2.using(
                    time_cost=config['security']['argon2id']['time_cost'],
                    memory_cost=config['security']['argon2id']['memory_cost'] // 1024,
                    parallelism=config['security']['argon2id']['threads']
                ).hash(new_password)

                crypt_value = config['security']['argon2id']['prefix_for_dovecot'] + password_hash
                execute_query(config['sql']['update_user_password'], (crypt_value, int(user_id)))

                # Désactiver l'utilisateur
                email = user[0]['email']
                execute_query(config['sql']['disable_user'], (email,))

                # Générer token
                import hashlib
                token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()

                # Marquer comme rekey pending
                execute_query(config['sql']['insert_rekey_pending'], (email, token, token))
            
            # Déplacé hors du `if`, mais dans le `try`
            start_response("302 Found", [("Location", "/home")])
            return []

        except Exception as e:
            logging.error(f"Erreur lors de la modification: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [b"Erreur lors de la modification"]

# --- Gestion de la suppression d'une boîte mail ---
def delete_user_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        user_id = params.get('id', [''])[0]

        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID invalide"]

        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Utilisateur non trouvé"]
        
        form = f"""
        <p><strong>ATTENTION : SUPPRESSION IMMINENTE DE LA BOITE MAIL {user[0]['email']}</strong></p>
        <p>Nous n'avons pas accès à vos mails, ils sont chiffrés. Nous ne pourrons pas vous les remettre en clair, ils resteront chiffrés. Assurez-vous de disposer de vos mails en clair si vous désirez les conserver localement. Par exemple, dans un client mail comme Thunderbird, synchronisez vos mails puis quittez ensuite le client mail. Puis supprimez cette boite.</p>
        <p><strong>Toutes les données de vos mails stockés sur nos serveurs seront définitivement perdus !</strong></p>
        <p>Êtes-vous bien sûr⋅e de vouloir supprimer la boite <strong>{user[0]['email']}</strong> ?</p>
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <button type="submit">OUI, supprimer et renoncer à la récupération des mails</button>
            <a href="/home"><button type="button">NON, Annuler</button></a>
        </form>
        """
        body = html_template("Confirmer la suppression", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Contenu manquant"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
    
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Jeton CSRF invalide"]
    
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID invalide"]
    
        # Récupérer user_id ET vérifier ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
    
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Accès refusé : vous n'êtes pas propriétaire de cette boîte"]

        # Récupérer l'email
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Utilisateur non trouvé"]
        
        email = user[0]['email']

        # Vérifier qu'il n'y a pas de rekey en cours
        rekey_active = fetch_all(config['sql']['select_rekey_pending'], (email,))
        
        if rekey_active:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            body = html_template("Suppression bloquée", "<p>Impossible de supprimer la boîte : un rechiffrement est en cours. Veuillez réessayer plus tard.</p>")
            return [body.encode()]

        try:
            # Désactiver l'utilisateur
            execute_query(config['sql']['disable_user'], (email,))
            
            # Générer un token unique
            import hashlib
            import time
            token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()

            # Marquer pour suppression
            execute_query(config['sql']['insert_deletion_pending'], (email, token, token))
                        
            # Rediriection avec message de confirmation
            start_response("302 Found", [("Location", "/home")])
            return []
        
        except Exception as e:
            logging.error(f"Erreur lors de la mise en attente de suppression: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [b"Erreur lors de la suppression"]
        
