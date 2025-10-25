# routes/mailbox_creation.py

from libs import config, parse_qs, datetime, timedelta, translations, argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from utils.db import fetch_all, execute_query
from utils.limits import can_create_mailbox
from handlers.html import html_template
import hashlib
import time
import logging

def create_mailbox_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    admin_user_id = session.data['id']
    
    # Check limit
    can_create, current_count, max_count = can_create_mailbox(admin_user_id)
    
    if environ['REQUEST_METHOD'] == 'GET':
        # Get available domains
        domains = fetch_all(config['sql_dovecot']['select_all_domains'], ())
        
        domain_options = "".join(
            f'<option value="{d["id"]}">{d["domain"]}</option>' 
            for d in domains
        )
        
        # Warning if limit reached
        if not can_create:
            warning = f'<p style="color: red; font-weight: bold;">{translations["mailbox_limit_reached"]}</p>'
            form_disabled = 'disabled'
        else:
            warning = f'<p>{translations["mailbox_count_display"].format(count=current_count)}</p>'
            form_disabled = ''
        
        form = f"""
        {warning}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
            
            <label for="local_part">{translations['local_part_label']}</label><br>
            <input type="text" id="local_part" name="local_part" placeholder="username" required {form_disabled}><br><br>
            
            <label for="domain_id">{translations['domain_label']}</label><br>
            <select id="domain_id" name="domain_id" required {form_disabled}>
                {domain_options}
            </select><br><br>
            
            <label for="password">{translations['password_label']}</label><br>
            <input type="password" id="password" name="password" required {form_disabled}><br><br>
            
            <label for="quota">{translations['quota_label']} (MB)</label><br>
            <input type="number" id="quota" name="quota" value="1000" required {form_disabled}><br><br>
            
            <label for="note">{translations['note_label']}</label><br>
            <textarea id="note" name="note" {form_disabled}></textarea><br><br>
            
            <button type="submit" {form_disabled}>{translations['btn_create']}</button>
            <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
        </form>
        """
        
        body = html_template(translations['create_mailbox_title'], form)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [body.encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        # Re-check limit (security)
        if not can_create:
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['error_mailbox_limit_exceeded'].encode('utf-8')]
        
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        csrf_token = data.get('csrf_token', [''])[0]
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]
        
        local_part = data.get('local_part', [''])[0].strip()
        domain_id = data.get('domain_id', [''])[0]
        password = data.get('password', [''])[0]
        quota = data.get('quota', ['1000'])[0]
        note = data.get('note', [''])[0].strip()
        
        # Validation
        if not local_part or not domain_id or not password:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['all_fields_required'].encode('utf-8')]
        
        # Get domain ID
        domain = fetch_all(config['sql_dovecot']['select_domain_by_id'], (domain_id,))
        if not domain:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [translations['invalid_domain'].encode('utf-8')]
        
        email = f"{local_part}@{domain[0]['domain']}"
        
        # Check if email exists
        existing = fetch_all(config['sql_dovecot']['select_user_by_email'], (email,))
        if existing:
            start_response("409 Conflict", [("Content-Type", "text/html")])
            return [translations['email_already_exists'].encode('utf-8')]
        
        # Hash password
        try:
            alg = config['mailbox_hash']['algorithm']
            prefix = config['mailbox_hash']['prefix']

            if alg == 'argon2id':
                password_hash = argon2.using(
                    type='ID',
                    time_cost=config['mailbox_hash']['argon2_time_cost'],
                    memory_cost=config['mailbox_hash']['argon2_memory_cost'],
                    parallelism=config['mailbox_hash']['argon2_parallelism']
                ).hash(password)
            elif alg == 'argon2i':
                password_hash = argon2.using(
                    type='I',
                    time_cost=config['mailbox_hash']['argon2_time_cost'],
                    memory_cost=config['mailbox_hash']['argon2_memory_cost'],
                    parallelism=config['mailbox_hash']['argon2_parallelism']
                ).hash(password)
            elif alg == 'bcrypt':
                password_hash = bcrypt.using(rounds=config['mailbox_hash']['bcrypt_rounds']).hash(password)
            elif alg == 'sha512-crypt':
                password_hash = sha512_crypt.hash(password)
            elif alg == 'sha256-crypt':
                password_hash = sha256_crypt.hash(password)
            elif alg == 'pbkdf2':
                password_hash = pbkdf2_sha256.using(rounds=config['mailbox_hash']['pbkdf2_rounds']).hash(password)
            else:
                raise ValueError("Unsupported hash algorithm")

            crypt_value = prefix + password_hash

            # Insert mailbox
            user_id = execute_query(
                config['sql_dovecot']['insert_user'], 
                (domain_id, email, crypt_value, quota, note, 1)  # active=1
            )
            
            # Add ownership
            execute_query(
                config['sql']['add_ownership'],
                (admin_user_id, user_id, 1)  # is_primary=1
            )
            
            token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()
            execute_query(config['sql']['insert_creation_pending'], (email, token, token))
            
            logging.info(f"Mailbox {email} created and marked for doveadm initialization")
            
            start_response("302 Found", [("Location", "/home")])
            return []

        except Exception as e:
            logging.error(f"Error creating mailbox: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['mailbox_creation_failed'].encode('utf-8')]
