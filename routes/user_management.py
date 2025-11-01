# routes/user_management.py

from libs import config
from utils.db import fetch_all, execute_query
from handlers.html import html_template
import time
import logging
from libs import argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from libs import parse_qs
from utils.alias_limits import can_create_alias
from i18n.en_US import translations

# --- Aliases management ---
def edit_alias_handler(environ, start_response):
    session = environ.get('session', None)
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        alias_id = params.get('id', [''])[0]

        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['alias_id_invalid'].encode('utf-8')]

        alias = fetch_all(config['sql_dovecot']['select_alias_by_id'], (int(alias_id),))
        if not alias:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['alias_not_found'].encode('utf-8')]

        # Generate form
        form = f"""
        <form method="POST">
            <input type="hidden" name="alias_id" value="{alias_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="source">{translations['source_label']}</label><br>
            <input type="text" id="source" name="source" value="{alias[0]['source']}" required><br><br>
            <label for="destination">{translations['destination_label']}</label><br>
            <input type="email" id="destination" name="destination" value="{alias[0]['destination']}" required><br><br>
            <button type="submit">{translations['btn_modify']}</button>
            <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
        </form>
        """
        body = html_template(translations['edit_alias_title'], form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    # Submit management
    elif environ['REQUEST_METHOD'] == 'POST':
        # Read POST data
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['bad_request'].encode('utf-8')]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        
        data = parse_qs(post_data)
        alias_id = data.get('alias_id', [''])[0]
        new_source = data.get('source', [''])[0].strip()
        new_destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
        
        # Validate entries
        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['alias_id_invalid'].encode('utf-8')]
        if not new_source or not new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['source_required'].encode('utf-8')]
        if '@' not in new_destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_invalid'].encode('utf-8')]

        # Update aliases in database
        try:
            execute_query(config['sql_dovecot']['update_alias'], (new_source, new_destination, int(alias_id)))
            start_response("302 Found", [("Location", "/home")])
            return [b""]
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Error when updating alias: {e}")
            return [translations['alias_update_failed'].encode('utf-8')]
            
# --- Aliases creations ---
def add_alias_handler(environ, start_response):
    session = environ.get('session', None)
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]

    if environ['REQUEST_METHOD'] == 'GET':
        # Extract destination from URL
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        destination = params.get('destination', [''])[0]

        if not destination or '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_invalid'].encode('utf-8')]
        
        # Check aliases limit
        can_create, current_count, max_count = can_create_alias(destination)
        
        if not can_create:
            warning = f'<p style="color: red; font-weight: bold;">{translations["alias_limit_reached"].format(count=max_count)}</p>'
            form_disabled = 'disabled'
        else:
            warning = f'<p>{translations["alias_count_display"].format(count=current_count, max=max_count)}</p>'
            form_disabled = ''
        # Generate form
        
        form = f"""
        {warning}
        <form method="POST">
            <label for="source">{translations['source_label']}</label><br>
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <input type="text" id="source" name="source" required><br><br>
            <label for="destination">{translations['destination_label']}</label><br>
            <input type="email" id="destination" name="destination" value="{destination}" readonly required><br><br>
            <button type="submit">{translations['btn_add']}</button>
            <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
        </form>
        """
        body = html_template(translations['add_alias_title'], form)
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
            return [translations['csrf_invalid'].encode('utf-8')]

        # Validation
        if not source or not destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['source_required'].encode('utf-8')]
        if '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_invalid'].encode('utf-8')]
        
        # Re-check aliases limit
        can_create, current_count, max_count = can_create_alias(destination)
        if not can_create:
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['error_alias_limit_exceeded'].format(count=max_count).encode('utf-8')]

        # Verifiy existing alias
        existing = fetch_all(config['sql_dovecot']['select_alias_by_source'], (source,))
        if existing:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            return [translations['alias_exists'].encode('utf-8')]

        # Fetch domain_id
        user = fetch_all(config['sql_dovecot']['select_user_by_email'], (destination,))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_unknown'].encode('utf-8')]
        domain_id = user[0]['domain_id']

        # insert new alias
        try:
            execute_query(config['sql_dovecot']['insert_alias'], (domain_id, source, destination))
            start_response("302 Found", [("Location", "/home")])
            return [b""]
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            logging.error(f"Error when adding alias: {e}")
            return [translations['alias_add_failed'].encode('utf-8')]

# --- Mailbox edits ---
def edit_user_handler(environ, start_response):
    session = environ.get('session', None)
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        user_id = params.get('id', [''])[0]

        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]

        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
  
        form = f"""
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <label for="email">{translations['email_field_label']}</label><br>
            <input type="email" id="email" name="email" value="{user[0]['email']}" required><br><br>
            <label for="password">{translations['password_field_label']}</label><br>
            <input type="password" id="password" name="password"><br><br>
            <button type="submit">{translations['btn_modify_mailbox']}</button>
            <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
        </form>
        """
        body = html_template(translations['edit_user_title'], form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['bad_request'].encode('utf-8')]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        new_password = data.get('password', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
        
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]
        
        # Get user_id and check ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['ownership_required'].encode('utf-8')]
        
        # Fetch original email
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
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
            return [b""]

        except Exception as e:
            logging.error(f"Error when modifying: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['user_modify_failed'].encode('utf-8')]

# --- Mailbox deletion ---
def delete_user_handler(environ, start_response):
    session = environ.get('session', None)
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]

    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        user_id = params.get('id', [''])[0]

        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]

        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
        form = f"""
        <p><strong>{translations['deletion_warning_title']}</strong></p>
        <p>{translations['deletion_warning_intro']}</p>
        <p>{translations['deletion_warning_sync']}</p>
        <p><strong>{translations['deletion_warning_final']}</strong></p>
        <p>{translations['deletion_confirm_prompt']} <strong>{user[0]['email']}</strong>?</p>
        <form method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            <button type="submit">{translations['btn_delete_definitely']}</button>
            <a href="/home"><button type="button">{translations['btn_no_cancel']}</button></a>
        </form>
        """
        body = html_template(translations['confirm_deletion_title'], form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['bad_request'].encode('utf-8')]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        user_id = data.get('user_id', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]
    
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
    
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]
    
        # Fetch user_id and check ownership
        user_id = int(user_id)
        admin_user_id = session.data['id']
    
        if not fetch_all(config['sql']['is_owner'], (admin_user_id, user_id)):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['ownership_required'].encode('utf-8')]

        # Fetch email
        user = fetch_all(config['sql']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
        email = user[0]['email']

        # Check whether there is no pending rekey
        rekey_active = fetch_all(config['sql']['select_rekey_pending'], (email,))
        
        if rekey_active:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            body = html_template(translations['confirm_deletion_title'], f"<p>{translations['deletion_blocked_rekey']}</p>")
            return [body.encode()]

        try:
            # Disable user
            execute_query(config['sql_dovecot']['disable_user'], (email,))
            
            # Generate token
            import hashlib
            import time
            token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()

            # Mark deletion as pending
            execute_query(config['sql']['insert_deletion_pending'], (email, token, token))
                        
            # Redirect to confirmation message
            start_response("302 Found", [("Location", "/home")])
            return [b""]
        
        except Exception as e:
            logging.error(f"Error when creating pending deletion: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['deletion_failed'].encode('utf-8')]
