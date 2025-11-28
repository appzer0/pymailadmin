# routes/recovery_process.py

import time
import logging
import datetime
from utils.db import fetch_all, execute_query
from handlers.html import html_template
from libs import config, parse_qs, argon2, bcrypt, sha512_crypt, sha256_crypt, pbkdf2_sha256
from utils.alias_limits import can_create_alias
from utils.email import send_email
from utils.recovery import generate_recovery_key, encrypt_recovery, verify_recovery, recover_mb_password
from utils.doveadm_api import doveadm_create_mailbox, doveadm_rekey_mailbox_generate, doveadm_rekey_mailbox_password, doveadm_delete_user, doveadm_delete_mailbox
from i18n.en_US import translations

# --- Recovery process ---
def recovery_handler(environ, start_response):
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
                <p><strong>{translations['recovery_message']}</strong></p>

                <form method="POST">
                        <input type="hidden" name="user_id" value="{user_id}">
                        <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                        
                        <label for="email">{translations['lost_mailbox_password_label']}</label><br>
                        <input type="email" id="email" name="email" value="{user[0]['email']}" readonly><br>
                        
                        <p>{translations['lost_mailbox_password_hint']}</p>
                        
                        <label for="recovery_key">{translations['recovery_key_label']}</label><br>
                        <input type="password" id="recovery_key" name="recovery_key" required><br>
                        <small>{translations['recovery_key_hint']}</small>
                        
                        <label for="password">{translations['current_password_field_label']}</label><br>
                        <input type="password" id="current_password" name="current_password" required><br><br>
                        
                        <button type="submit">{translations['btn_change_pwd_reencrypt']}</button>
                        <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
                </form>
                
                <form method="POST">
                        <input type="hidden" name="user_id" value="{user_id}">
                        <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                        
                        <label for="email">{translations['lost_mailbox_recovery_label']}</label><br>
                        <input type="email" id="email" name="email" value="{user[0]['email']}" readonly><br><br>
                        
                        <p>{translations['lost_mailbox_recovery_hint']}</p>
                        
                        <label for="recovery_key">{translations['recovery_key_label']}</label><br>
                        <input type="password" id="recovery_key" name="recovery_key" required><br>
                        <small>{translations['recovery_key_hint']}</small>
                        
                        <label for="password">{translations['password_field_label']}</label><br>
                        <input type="password" id="password" name="password" required><br><br>
                        
                        <button type="submit">{translations['btn_change_recovery_reencrypt']}</button>
                        <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
                </form>
                
                <form method="POST">
                        <input type="hidden" name="user_id" value="{user_id}">
                        <input type="hidden" name="csrf_token" value="{session.get_csrf_token()}">
                        
                        <label for="email">{translations['lost_both_label']}</label><br>
                        <input type="email" id="email" name="email" value="{user[0]['email']}" readonly><br><br>
                        
                        <p><strong>{translations['lost_both_hint']}</strong></p>

                        <button type="submit">{translations['destroy_recreate_mailbox_button']}</button>
                        <a href="/home"><button type="button">{translations['btn_cancel']}</button></a>
                </form>
        """
        
        body = html_template(translations['recovery_title'], form, admin_user_email=admin_user_email, admin_role=admin_role)
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
                
                ## TODO: wait for doveadm to finish rekeying mailbox before reenable mailbox
                # Disable user
                email = user[0]['email']
                execute_query(config['sql_dovecot']['disable_user'], (email,))
                
                # Get recovery key pair
                recovery_records = fetch_all(config['sql']['select_recovery_key'], (user_id,))
                
                if not recovery_records:
                    # Rare testcases where key is missing, insert temporary blank pair
                    execute_query(config['sql']['insert_recovery_key'], (user_id, "", ""))
                
                enc_master_key = recovery_records[0]['recovery_key']
                enc_mb_password = recovery_records[0]['enc_mb_password']
                
                # Recover the old password as plain
                try:
                    old_mb_password = recover_mb_password(enc_master_key, enc_mb_password, recovery_key)
                
                 except Exception as e:
                    logging.error(f"Failed to recover password: {e}")
                
                # Everything seems OK here, let's update.
                
                # Generate and encrypt recoverable key pair with new password
                recovery_key = generate_recovery_key()
                enc_master_key, enc_mb_password = generate_and_store_master_key(mb_password=new_password, recovery_password=recovery_key)
                
                # Insert into recovery_keys table
                execute_query(config['sql']['update_recovery_key'], (enc_master_key, enc_mb_password, user_id))
                
                ### Add doveadm API stuff here
                
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
