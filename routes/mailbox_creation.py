# routes/mailbox_creation.py

from libs import config, parse_qs, datetime, timedelta, translations, argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
import base64, secrets
import hashlib
from utils.db import fetch_all, execute_query
from utils.limits import can_create_mailbox
from utils.recovery import generate_recovery_key, generate_hint_from_key
from handlers.html import html_template
import time
import logging

def create_mailbox_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return [b""]

    admin_user_id = session.data['id']
    admin_user_email = session.data.get('email', '')
    admin_role = session.data.get('role', 'user')
    
    # Check limit
    can_create, current_count, max_count = can_create_mailbox(admin_user_id)
    
    if environ['REQUEST_METHOD'] == 'GET':
    
        # Get domains
        try:
            if admin_role == 'super_admin':
                # Get all domains for superadmin
                domains = fetch_all(config['sql_dovecot']['select_all_domains'], ())
                
            else:
                # Get allowed domains only for users/admins
                allowed_domain_rows = fetch_all(config['sql']['select_domains_by_admin_user'], (admin_user_id,))
                allowed_domain_ids = [row['domain_id'] for row in allowed_domain_rows] if allowed_domain_rows else []
                
                if not allowed_domain_ids:
                    domains = []
                
                else:
                    domains = fetch_all(config['sql_dovecot']['select_allowed_domains_by_admin'], (admin_user_id,))
        
        except Exception as e:
            logging.error(f"Error fetching domains: {e}")
            domains = []
        
        # Build the domains drop-down list
        domain_options = "".join(f'<option value="{d["id"]}">{d["domain"]}</option>' for d in domains)
        
        # Warning if limit reached
        if not can_create:
            warning = f'<p style="color: red; font-weight: bold;">{translations["mailbox_limit_reached"]}</p>'
            form_disabled = 'disabled'
        else:
            warning = f'<p>{translations["mailbox_count_display"].format(count=current_count)}</p>'
            form_disabled = ''
        
        # Generate form
        form_html = f"""
            {warning}
            <form method="POST" id="mailboxForm">
                <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                
                <fieldset>
                    <legend>{translations['mailbox_creation_mailbox']}</legend>
                    
                    <label for="local_part">{translations['local_part_label']}</label><br>
                    <input type="text" id="local_part" name="local_part" placeholder="username" minlength="6" maxlength="64" pattern="^[a-z0-9_-]+$" required {form_disabled}><br>
                    <small>{translations['mailbox_creation_mailbox_hint']}{config['POSTFIX_SEPARATOR']}</small><br><br>
                    
                    <label for="domain_id">{translations['domain_label']}</label><br>
                    <select id="domain_id" name="domain_id" required {form_disabled}>
                        {domain_options}
                    </select><br>
                    <small>{translations['mailbox_creation_domain_hint']}</small><br><br>
                </fieldset>
                
                <fieldset>
                    <legend>{translations['mailbox_creation_password']}</legend>
                    
                    <label for="password">{translations['password_label']}</label><br>
                    <input type="password" id="password" name="password" minlength="12" maxlength="64" pattern="[^%]+" required {form_disabled}><br>
                    <small>{translations['mailbox_creation_password_hint']}</small><br><br>
                    
                    <label for="password_confirm">{translations['confirm_password_label']}</label><br>
                    <input type="password" id="password_confirm" name="password_confirm" minlength="12" maxlength="64" pattern="[^%]+" required {form_disabled}><br>
                    <small>{translations['mailbox_creation_passwords_match_hint']}</small><br><br>
                </fieldset>
                
                <fieldset>
                    <legend>{translations['mailbox_creation_quota']}</legend>
                    
                    <label for="quota">{translations['quota_label']}</label><br>
                    <input type="number" id="quota" name="quota" min="1" max="5" value="1" required {form_disabled}><br>
                    <small>{translations['mailbox_creation_quota_hint']}</small><br><br>
                </fieldset>
                
                <div id="preview" style="font-weight:bold; font-size:1.3em; margin-bottom:15px; color:red; text-align:center;">
                    ?@domain.tld (X GB)
                </div>
                
                <button type="submit" disabled {form_disabled}>{translations['btn_create']}</button>
                <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
            </form>
        """
        
        script_js = """
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const localPart = document.getElementById('local_part');
                const domainSelect = document.getElementById('domain_id');
                const quotaInput = document.getElementById('quota');
                const preview = document.getElementById('preview');
                const password = document.getElementById('password');
                const passwordConfirm = document.getElementById('password_confirm');
                const submitBtn = document.querySelector('#mailboxForm button[type="submit"]');
                
                function validateLocalPart(str) {
                    return /^[a-z0-9_-]{6,}$/.test(str);
                }
                
                function validatePassword(pwd) {
                    return pwd.length >= 12 && !pwd.includes('%');
                }
                
                function updatePreview() {
                    const email = localPart.value + '@' + (domainSelect.options[domainSelect.selectedIndex]?.text || '');
                    const quota = quotaInput.value || 'X';
                    let valid = true;
                    
                    if (!validateLocalPart(localPart.value)) valid = false;
                    if (!validatePassword(password.value)) valid = false;
                    if (password.value !== passwordConfirm.value) valid = false;
                    if (!(quota >= 1 && quota <= 5)) valid = false;
                    if (!domainSelect.value) valid = false;
                    
                    preview.textContent = email + " (" + quota + " GB)";
                    preview.style.color = valid ? 'green' : 'red';
                    submitBtn.disabled = !valid;
                }
                
                localPart.addEventListener('input', updatePreview);
                domainSelect.addEventListener('change', updatePreview);
                quotaInput.addEventListener('input', updatePreview);
                password.addEventereventListener('input', updatePreview);
                passwordConfirm.addEventListener('input', updatePreview);
                
                updatePreview(); // initial update
            });
            </script>
        """
        
        form = form_html + script_js
        
        body = html_template(translations['create_mailbox_title'], form, admin_user_email=admin_user_email, admin_role=admin_role)
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
        
        admin_user_id = session.data['id']
        
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
            
            # Argon2 hashing
            if alg in ['argon2id', 'argon2i']:
                
                if alg == 'argon2id':
                    argon2_type = 'ID'
                
                if alg == 'argon2i':
                    argon2_type = 'I'
                
                # Generate unique salt
                salt_bytes = secrets.token_bytes(16)
                
                # Salted-hash the password
                hash_obj = argon2.using(
                    type=argon2_type,
                    salt=salt_bytes,
                    time_cost=config['mailbox_hash']['argon2_time_cost'],
                    memory_cost=config['mailbox_hash']['argon2_memory_cost'],
                    parallelism=config['mailbox_hash']['argon2_parallelism']
                )
                hashed = hash_obj.hash(password)
                
                # Extract passlib hash ("$argon2id$v=...$...$salt$hash")
                parts = hashed.split('$')
                salt_part = parts[-2]
                hash_part = parts[-1]
                
                # Dovecot-style format
                crypt_value = f"{prefix}${salt_part}${hash_part}"
            
            # Other algos hashing
            elif alg == 'bcrypt':
                crypt_value = prefix + bcrypt.using(rounds=config['mailbox_hash']['bcrypt_rounds']).hash(password)
            
            elif alg == 'sha512-crypt':
                crypt_value = prefix + sha512_crypt.hash(password)
            
            elif alg == 'sha256-crypt':
                crypt_value = prefix + sha256_crypt.hash(password)
            
            elif alg == 'pbkdf2':
                crypt_value = prefix + pbkdf2_sha256.using(rounds=config['mailbox_hash']['pbkdf2_rounds']).hash(password)
            
            else:
                raise ValueError("Unsupported hash algorithm")
            
            # Insert mailbox
            user_id = execute_query(
                config['sql_dovecot']['insert_user'], 
                (domain_id, email, crypt_value, quota, 1)  # active=1
            )
            
            # Add ownership
            execute_query(
                config['sql']['add_ownership'],
                (admin_user_id, user_id, 1)  # is_primary=1 (unimplemented)
            )
            
            # Add pending creation for Dovecot
            token = hashlib.sha256(f"{email}{config['SECRET_KEY']}{int(time.time()/120)}".encode()).hexdigest()
            execute_query(config['sql']['insert_creation_pending'], (email, token, token))
            
            logging.info(f"Mailbox {email} created and marked for doveadm initialization")
            
            # Generate recovery key and hint from the key
            full_recovery_key = generate_recovery_key()
            hint = generate_hint_from_key(full_recovery_key)
            
            # Insert only short hint in table
            execute_query(config['sql']['insert_recovery_key'], (user_id, hint))
            
            confirmation_html = f"""
                <p>{translations['recovery_key_hint']}</p>
                <p style="font-family:monospace; font-size:1.2em; background:#ffe; padding:10px; border:1px solid #cc0;">
                    {full_recovery_key}
                </p>
                <button onclick="navigator.clipboard.writeText('{full_recovery_key}')">{translations['copy_the_key']}</button>
                <p>{translations['recovery_key_copy_save']}</p>
                <p><strong>{translations['recovery_key_not_visible_again']}</strong></p><br>
                <p>{translations['mailbox_ongoing_creation_note']}</p><br>
                <p><a href="/home">{translations['btn_i_saved_it']}</a></p>
                
            """
            
            body = html_template(translations['mailbox_created_title'], confirmation_html, admin_user_email=admin_user_email, admin_role=admin_role)
            start_response("200 OK", [("Content-Type", "text/html")])
            return [body.encode()]
        
        except Exception as e:
            logging.error(f"Error creating mailbox: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [translations['mailbox_creation_failed'].encode('utf-8')]
