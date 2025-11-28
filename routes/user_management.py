# routes/user_management.py

import time
import logging
import datetime
from utils.db import fetch_all, execute_query
from handlers.html import html_template
from libs import config, parse_qs, argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from utils.alias_limits import can_create_alias
from utils.email import send_email
from utils.doveadm_api import doveadm_create_mailbox, doveadm_rekey_mailbox_generate, doveadm_rekey_mailbox_password, doveadm_delete_user, doveadm_delete_mailbox
from i18n.en_US import translations

# --- Aliases management ---
def edit_alias_handler(environ, start_response):
    session = environ.get('session', None)
    
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]
    
    if environ['REQUEST_METHOD'] == 'GET':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Bad request"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        alias_id = data.get('alias_id', [''])[0]
        
        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['alias_id_invalid'].encode('utf-8')]
        
        alias = fetch_all(config['sql_dovecot']['select_alias_by_id'], (int(alias_id),))
        
        if not alias:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['alias_not_found'].encode('utf-8')]
        
        admin_user_email = session.data.get('email', '')
        admin_role = session.data.get('role', 'user')
        source_local = alias[0]['source'].split('@')[0]
        destination = alias[0]['destination']
        
        # Generate form
        form_html = f"""
            <form method="POST" id="aliasEditForm">
                <input type="hidden" name="alias_id" value="{alias_id}">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                
                <label for="source">{translations['source_label']}</label><br>
                <input type="text" id="source" name="source" value="{source_local}" minlength="8" pattern="^[a-z0-9_-]+$" required><br>
                <small>Lowercase letters, digits, underscore, dash; no dot or @; minimum 8 characters.</small><br><br>
                
                <label for="destination">{translations['destination_label']}</label><br>
                <input type="text" id="destination" name="destination" value="{destination}" readonly><br><br>
                
                <div id="preview" style="font-weight:bold; font-size:1.3em; margin-bottom:15px; color:red; text-align:center;">
                    {alias[0]['source']} → {destination}
                </div>
                
                <button type="submit" disabled>{translations['btn_modify']}</button>
                <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
            </form>
        """
        
        script_js = """
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const sourceInput = document.getElementById('source');
                const destinationInput = document.getElementById('destination');
                const preview = document.getElementById('preview');
                const submitBtn = document.querySelector('#aliasEditForm button[type="submit"]');
                
                function validateAlias(source) {
                    return /^[a-z0-9_-]{8,}$/.test(source);
                }
                
                function updatePreview() {
                    const sourceVal = sourceInput.value.trim();
                    const destVal = destinationInput.value.trim();
                    const domainPart = destVal.split('@')[1] || '';
                    const isValid = validateAlias(sourceVal);
                    
                    if (sourceVal) {
                        preview.textContent = sourceVal + '@' + domainPart + " → " + destVal;
                        preview.style.color = isValid ? 'green' : 'red';
                    } else {
                        preview.textContent = '?@' + domainPart + " → " + destVal;
                        preview.style.color = 'red';
                    }
                    
                    submitBtn.disabled = !isValid;
                }
                
                sourceInput.addEventListener('input', updatePreview);
                updatePreview();
            });
            </script>
        """
        
        form = form_html + script_js
        
        body = html_template(translations['edit_alias_title'], form,admin_user_email=admin_user_email,admin_role=admin_role)
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
        source_raw = data.get('source', [''])[0].strip()
        destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
        
        # Validate entries
        if not alias_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['alias_id_invalid'].encode('utf-8')]
        
        if '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_invalid'].encode('utf-8')]

        domain_part = destination.split('@', 1)[1]
        source = f"{source_raw}@{domain_part}"

        # Update aliases in database
        try:
            execute_query(config['sql_dovecot']['update_alias'], (source, destination, int(alias_id)))
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
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Bad request"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        destination = data.get('destination', [''])[0]

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
        
        admin_user_email = session.data.get('email', '')
        admin_role = session.data.get('role', 'user')
        
        # Generate form
        form_html = f"""
            {warning}
            <form method="POST" id="aliasAddForm">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                
                <label for="source">{translations['source_label']}</label><br>
                <input type="text" id="source" name="source" minlength="8" pattern="^[a-z0-9_-]+$" required {form_disabled} placeholder="alias"><br>
                <small>Lowercase letters, digits, underscore, dash; no dot or @; minimum 8 characters.</small><br><br>
                
                <label for="destination">{translations['destination_label']}</label><br>
                <input type="hidden" id="destination" name="destination" value="{destination}">
                <strong>{destination}</strong><br><br>
                
                <div id="preview" style="font-weight:bold; font-size:1.3em; margin-bottom:15px; color:red; text-align:center;">
                    ?@domain.tld → mailbox@domain.tld
                </div>
                
                <button type="submit" disabled {form_disabled}>{translations['btn_add']}</button>
                <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
            </form>
        """

        script_js = """
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const sourceInput = document.getElementById('source');
                const destInput = document.getElementById('destination');
                const previewDiv = document.getElementById('preview');
                const submitBtn = document.querySelector('#aliasAddForm button[type="submit"]');
                
                function validateAlias(alias) {
                    return /^[a-z0-9_-]{8,}$/.test(alias);
                }
                
                function updatePreview() {
                    const sourceVal = sourceInput.value.trim();
                    const destVal = destInput.value.trim();
                    const domainPart = destVal.split('@')[1] || '';
                    const valid = validateAlias(sourceVal) && destVal.includes('@');
                    
                    const previewText = valid
                        ? sourceVal + '@' + domainPart + ' → ' + destVal
                        : '?@domain.tld → mailbox@domain.tld';
                    
                    previewDiv.textContent = previewText;
                    previewDiv.style.color = valid ? 'green' : 'red';
                    submitBtn.disabled = !valid;
                }
                
                sourceInput.addEventListener('input', updatePreview);
                updatePreview();  // initial preview
            });
            </script>
        """
        
        form = form_html + script_js
        
        body = html_template(translations['add_alias_title'], form, admin_user_email=admin_user_email, admin_role=admin_role)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]
    
    elif environ['REQUEST_METHOD'] == 'POST':
        # Parse data
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        source_raw = data.get('source', [''])[0].strip()
        destination = data.get('destination', [''])[0].strip()
        csrf_token = data.get('csrf_token', [''])[0]
        
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
        
        # Validation
        if not source_raw or not destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['source_required'].encode('utf-8')]
        
        if '@' not in destination:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['destination_invalid'].encode('utf-8')]
        
        # Concat source with domain part of destination to form full alias source@domain
        domain_part = destination.split('@', 1)[1]
        source = f"{source_raw}@{domain_part}"
        
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
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Bad request"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        user_id = data.get('user_id', [''])[0]
        
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]
        
        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
        admin_user_email = session.data.get('email', '')
        admin_role = session.data.get('role', 'user')
        
        # Generate form
        form = f"""
            <form method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                
                <label for="email">{translations['email_field_label']}</label><br>
                <input type="email" id="email" name="email" value="{user[0]['email']}" readonly><br><br>
                
                <label for="recovery_key">{translations['recovery_key_label']}</label><br>
                <input type="password" id="recovery_key" name="recovery_key" required><br>
                <small>{translations['recovery_key_hint']}</small>
                
                <label for="password">{translations['password_field_label']}</label><br>
                <input type="password" id="password" name="password" required><br><br>
                
                <button type="submit">{translations['btn_modify_mailbox']}</button>
                <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
                
                <p><a href="/recovery">{translations['i_lost_password_or_recovery']}</a></p>
            </form>
        """
        
        body = html_template(translations['edit_user_title'], form, admin_user_email=admin_user_email, admin_role=admin_role)
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
        recovery_key = data.get('recovery_key', [''])[0]
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
        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
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
                execute_query(config['sql_dovecot']['update_user_password'], (crypt_value, int(user_id)))
                
                # Disable user
                email = user[0]['email']
                execute_query(config['sql_dovecot']['disable_user'], (email,))
                
                # Everything seems OK here, let's update.
                
                ### Add doveadm API stuff here
                ### TODO: wait for doveadm to finish rekeying mailbox before reenable mailbox
                
                # Send password change notification to admin
                subject = f"[{config['PRETTY_NAME']}] {translations['notify_password_changed_subject']}"
                body = f"""
                    {translations['notify_password_changed_body']}
                    {translations['notify_password_changed_date']} {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    {translations['notify_password_changed_admin']}
                """
                
                try:
                    send_email(admin_user_email, subject, body)
                
                except Exception as e:
                    logging.error(f"Failed to send email notification: {e}")
                
                # Display confirmation with new key to user
                confirmation_html = f"""
                    <p>{translations['password_changed']}</p>
                    <p>{translations['recovery_key_hint']}</p>
                    <p style="font-family:monospace; font-size:1.2em; background:#ffe; padding:10px; border:1px solid #cc0;">
                        {recovery_key}
                    </p>
                    <p>{translations['recovery_key_copy_save']}</p>
                    <p><strong>{translations['recovery_key_not_visible_again']}</strong></p><br>
                    <p><a href="/home">{translations['btn_i_saved_it']}</a></p>
                """
                
                body = html_template(translations['password_changed_title'], confirmation_html, admin_user_email=admin_user_email, admin_role=admin_role)
                start_response("200 OK", [("Content-Type", "text/html")])
                return [body.encode()]
        
        except Exception as e:
            logging.error(f"Error changing password: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['user_modify_failed'].encode('utf-8')]

# --- Mailbox deletion ---
def delete_user_handler(environ, start_response):
    session = environ.get('session', None)
    
    if session is None or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]
    
    if environ['REQUEST_METHOD'] == 'GET':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        
        if content_length == 0:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Bad request"]
        
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        user_id = data.get('user_id', [''])[0]
        
        if not user_id.isdigit():
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_id_invalid'].encode('utf-8')]
        
        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        
        if not user:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
        admin_user_email = session.data.get('email', '')
        admin_role = session.data.get('role', 'user')
    
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
        
        body = html_template(translations['confirm_deletion_title'], form,admin_user_email=admin_user_email,admin_role=admin_role)
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
        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['user_not_found'].encode('utf-8')]
        
        email = user[0]['email']
        
        try:
            # Disable user
            execute_query(config['sql_dovecot']['disable_user'], (email,))

            ### Trigger doveadm
                        
            # Redirect to confirmation message
            start_response("302 Found", [("Location", "/home")])
            return [b""]
        
        except Exception as e:
            logging.error(f"Error when deleting mailbox: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['deletion_failed'].encode('utf-8')]
