# routes/user_management.py

from libs import config
from utils.db import fetch_all, execute_query
from handlers.html import html_template
import time
import logging
from libs import argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from libs import parse_qs

# --- Aliases management ---
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
            return [b"Aliases not found"]

        # Generate form
        form = f"""
        <form method="POST">
            <input type="hidden" name="alias_id" value="{alias_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="source">Source:</label><br>
            <input type="text" id="source" name="source" value="{alias[0]['source']}" required><br><br>
            <label for="destination">Destination:</label><br>
            <input type="email" id="destination" name="destination" value="{alias[0]['destination']}" required><br><br>
            <button type="submit">Modify</button>
            <a href="/home"><button type="button">Cancel</button></a>
        </form>
        """
        body = html_template("Modify an alias", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    # Submit management
    elif environ['REQUEST_METHOD'] == 'POST':
        # Read POST data
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Missing request content"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        
        data = parse_qs(post_data)
        alias_id = data.get('alias_id', [''])[0]
        new_source = data.get('source', [''])[0].strip()
        new_destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]
        
        # Validate entries
        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Invalid alias ID"]
        if not new_source or not new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Missing mandatory fields"]
        if '@' not in new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Invalida destination address"]

        # Update aliases in database
        try:
            execute_query(config['sql']['update_alias'], (new_source, new_destination, int(alias_id)))
            start_response("302 Found", [("Location", "/home")])
            return []
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Error when  updating alias: {e}")
            return [b"Error when  updating alias"]

# --- Aliases creations ---
def add_alias_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    if environ['REQUEST_METHOD'] == 'GET':
        # Extract destination from URL
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        destination = params.get('destination', [''])[0]

        if not destination or '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Invalid destination"]

        # Generate form
        form = f"""
        <form method="POST">
            <label for="source">Source:</label><br>
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <input type="text" id="source" name="source" required><br><br>
            <label for="destination">Destination:</label><br>
            <input type="email" id="destination" name="destination" value="{destination}" readonly required><br><br>
            <button type="submit">Create Alias</button>
            <a href="/home"><button type="button">Cancel</button></a>
        </form>
        """
        body = html_template("Add an Alias", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        # Parse data
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        source = data.get('source', [''])[0].strip()
        destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]

        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]

        # Validation
        if not source or not destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Missing mandatory fields"]
        if '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"invalid destination"]

        # Vérifiy existing alias
        existing = fetch_all(config['sql']['select_alias_by_source'], (source,))
        if existing:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            return [b"An alias with this source already exists."]

        # Fetch domain_id
        user = fetch_all(config['sql']['select_user_by_email'], (destination,))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Destination mailbox unknown"]
        domain_id = user[0]['domain_id']

        # insert new alias
        try:
            execute_query(config['sql']['insert_alias'], (domain_id, source, destination))
            start_response("302 Found", [("Location", "/home")])
            return []
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Erreur when adding alias: {e}")
            return [b"Erreur when adding alias"]

# --- Mailbox edits ---
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
            return [b"Invalid user ID"]

        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"User not found"]
  
        form = f"""
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="email">Email address:</label><br>
            <input type="email" id="email" name="email" value="{user[0]['email']}" required><br><br>
            <label for="password">Password (leave empty to keep current password):</label><br>
            <input type="password" id="password" name="password"><br><br>
            <button type="submit">Modify mailbox</button>
            <a href="/home"><button type="button">Cancel</button></a>
        </form>
        """
        body = html_template("Modify a Mailbox", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Missing content"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        new_password = data.get('password', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]
        
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Invalid ID"]
        
        # Get user_id and check ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Forbidden access: you are not the owner of this mailbox?!"]
        
        # Fetch original email
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"User not found"]
        
        email = user[0]['email']
    
        try:
            if new_password:
                alg = config['mailbox_hash']['algorithm']
                prefix = config['mailbox_hash']['prefix']

                if alg == 'argon2id':
                    password_hash = argon2.using(
                        type='ID',
                        time_cost=config['mailbox_hash']['argon2_time_cost'],
                        memory_cost=config['mailbox_hash']['argon2_memory_cost'],
                        parallelism=config['mailbox_hash']['argon2_parallelism']
                    ).hash(new_password)
                elif alg == 'argon2i':
                    password_hash = argon2.using(
                        type='I',
                        time_cost=config['mailbox_hash']['argon2_time_cost'],
                        memory_cost=config['mailbox_hash']['argon2_memory_cost'],
                        parallelism=config['mailbox_hash']['argon2_parallelism']
                    ).hash(new_password)
                elif alg == 'bcrypt':
                    password_hash = bcrypt.using(rounds=config['mailbox_hash']['bcrypt_rounds']).hash(new_password)
                elif alg == 'sha512-crypt':
                    password_hash = sha512_crypt.hash(new_password)
                elif alg == 'sha256-crypt':
                    password_hash = sha256_crypt.hash(new_password)
                elif alg == 'pbkdf2':
                    password_hash = pbkdf2_sha256.using(rounds=config['mailbox_hash']['pbkdf2_rounds']).hash(new_password)
                else:
                    # Fallback
                    raise ValueError("Unsupported hash algorithm for Dovecot mailbox passwords.")

                crypt_value = prefix + password_hash
                execute_query(config['sql']['update_user_password'], (crypt_value, int(user_id)))

                # Disable user
                email = user[0]['email']
                execute_query(config['sql']['disable_user'], (email,))

                # Generate token
                import hashlib
                token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()

                # Mark as rekey pending
                execute_query(config['sql']['insert_rekey_pending'], (email, token, token))
            
            start_response("302 Found", [("Location", "/home")])
            return []

        except Exception as e:
            logging.error(f"Error when modifying: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [b"Error when modifying"]

# --- Mailbox deletion ---
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
            return [b"Invalid ID"]

        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"User not found"]
        
        form = f"""
        <p><strong>ATTENTION: MAILBOX INCOMING DELETION FOR {user[0]['email']}</strong></p>
        <p>We cannot access your mails as they are fully encrypted. We won't be able to give them as plain text. Make sure you obtained your mails as plain text if you plan to keep them locally. By example, in a mail client like Thundrbird, synchronize your mails on your computer then quit Thunderbird or switch it offline. Then only delete your mailbox.</p>
        <p><strong>All stored data related to your mails will be definitely lost!</strong></p>
        <p>Are you really sure you want to <strong>delete the mailbox for {user[0]['email']}</strong>?</p>
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <button type="submit">YES, definitely delete mailbox and data NOW</button>
            <a href="/home"><button type="button">NO, cancel now</button></a>
        </form>
        """
        body = html_template("Confirmm deletion", form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Missing content"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
    
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]
    
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"ID invalide"]
    
        # Fetch user_id and check ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
    
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Forbidden access: you are not the owner of this mailbox?!"]

        # Fetch email
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"User not found"]
        
        email = user[0]['email']

        # Check whether there is no pending rekey
        rekey_active = fetch_all(config['sql']['select_rekey_pending'], (email,))
        
        if rekey_active:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            body = html_template("Deletion blocked", "<p>Cannot delete mailbox : a reenryption is already running. Try again later.</p>")
            return [body.encode()]

        try:
            # Disable user
            execute_query(config['sql']['disable_user'], (email,))
            
            # Generate token
            import hashlib
            import time
            token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()

            # Mark deletion as pending
            execute_query(config['sql']['insert_deletion_pending'], (email, token, token))
                        
            # Rediriect to confirmation message
            start_response("302 Found", [("Location", "/home")])
            return []
        
        except Exception as e:
            logging.error(f"Error when creating pending deletion: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [b"Error when creating pending deletion"]
        
