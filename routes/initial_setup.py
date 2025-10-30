from passlib.hash import argon2
from utils.db import fetch_all, execute_query
from handlers.html import html_template
from libs import parse_qs, config
import importlib
import logging
import os
import glob

def get_available_languages():
    i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'i18n')
    language_files = glob.glob(os.path.join(i18n_dir, '*_*.py'))
    languages = []
    for filepath in language_files:
        filename = os.path.basename(filepath)
        if filename == '__init__.py':
            continue
        locale = filename.replace('.py', '').replace('_', '-')
        try:
            module_name = filename.replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            display_name = getattr(module, 'language_name', locale)
        except Exception:
            display_name = locale
        languages.append({'code': locale, 'name': display_name})
    languages.sort(key=lambda x: x['code'])
    return languages if languages else [{'code': 'en_US', 'name': 'English (US)'}]

def load_translations(locale_code):
    module_name = locale_code.replace('-', '_')
    try:
        i18n_module = importlib.import_module(f'i18n.{module_name}')
        return getattr(i18n_module, 'translations', {})
    except Exception as e:
        logging.error(f"Error loading translations for {locale_code}: {e}")
        try:
            i18n_module = importlib.import_module('i18n.en_US')
            return getattr(i18n_module, 'translations', {})
        except Exception:
            return {}

def write_language_to_env(language_code):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
        new_lines, found = [], False
        for line in lines:
            if line.startswith('APP_LANGUAGE='):
                new_lines.append(f'APP_LANGUAGE={language_code}\n')
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f'APP_LANGUAGE={language_code}\n')
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        return True

    except Exception as e:
        logging.error(f"Error writing language to .env: {e}")
        return False

def write_env_config(data):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
        updates = {
            'APP_LANGUAGE': data.get('language', 'en-US'),
            'DB_TABLE_DOMAINS': data.get('db_table_domains', 'domain'),
            'DB_FIELD_DOMAIN_ID': data.get('db_field_domain_id', 'id'),
            'DB_FIELD_DOMAIN_NAME': data.get('db_field_domain_name', 'domain'),
            'DB_TABLE_USERS': data.get('db_table_users', 'users'),
            'DB_FIELD_USER_ID': data.get('db_field_user_id', 'id'),
            'DB_FIELD_USER_EMAIL': data.get('db_field_user_email', 'email'),
            'DB_FIELD_USER_PASSWORD': data.get('db_field_user_password', 'crypt'),
            'DB_FIELD_USER_ACTIVE': data.get('db_field_user_active', 'active'),
            'DB_TABLE_ALIASES': data.get('db_table_aliases', 'alias'),
            'DB_FIELD_ALIAS_ID': data.get('db_field_alias_id', 'id'),
            'DB_FIELD_ALIAS_SOURCE': data.get('db_field_alias_source', 'source'),
            'DB_FIELD_ALIAS_DESTINATION': data.get('db_field_alias_destination', 'destination'),
            'MAX_MAILBOXES_PER_USER': str(data.get('max_mailboxes_per_user', 3)),
            'MAX_ALIASES_PER_MAILBOX': str(data.get('max_aliases_per_mailbox', 100)),
        }
        new_lines, updated_keys = [], set()
        for line in lines:
            updated = False
            for key, value in updates.items():
                if line.startswith(f'{key}='):
                    new_lines.append(f'{key}={value}\n')
                    updated_keys.add(key)
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f'{key}={value}\n')
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        return True

    except Exception as e:
        logging.error(f"Error writing .env configuration: {e}")
        return False

def mark_config_completed():
    config_marker = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.config_completed')

    try:
        with open(config_marker, 'w') as f:
            f.write('1')
        return True

    except Exception as e:
        logging.error(f"Error creating config marker: {e}")
        return False

def check_config_completed():
    config_marker = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.config_completed')
    return os.path.exists(config_marker)

def generate_cron_script(data):
    template_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'pymailadmin-cron.py')
    with open(template_path, 'r') as f:
        template = f.read()
    replacements = {
        '{DB_HOST}': data.get('db_host', '127.0.0.1'),
        '{DB_USER}': data.get('db_user', 'sqluser'),
        '{DB_PASSWORD}': data.get('db_password', 'password'),
        '{DB_NAME}': data.get('db_name', 'pymailadmin'),
        '{DB_TABLE_USERS}': data.get('db_table_users', 'users'),
        '{DB_FIELD_USER_EMAIL}': data.get('db_field_user_email', 'email'),
        '{DB_FIELD_USER_ACTIVE}': data.get('db_field_user_active', 'active'),
        '{DB_FIELD_USER_ID}': data.get('db_field_user_id', 'id'),
    }
    for key, val in replacements.items():
        template = template.replace(key, val)
    return template

def _preserve_all_data(data):
    excluded = ['csrf_token', 'step']
    hidden_fields = ""
    for key, value in data.items():
        if key not in excluded:
            hidden_fields += f'<input type="hidden" name="{key}" value="{value}">\n'
    return hidden_fields

def config_wizard_page(session, step=1, error_msg=None, data=None, locale='en-US'):
    token = session.get_csrf_token()
    data = data or {}
    trans = load_translations(locale)
    error_html = f'<p style="color: red; font-weight: bold;">{error_msg}</p>' if error_msg else ''
    
    # Back button
    back_button = ""
    if step > 1:
        back_step = step - 1
        back_button = f'''
        <form method="GET" action="/setup/config" style="margin-bottom: 15px;">
            <input type="hidden" name="step" value="{back_step}">
            <input type="hidden" name="locale" value="{locale}">
            <button type="submit" style="padding: 8px 16px; margin-bottom: 20px;">{trans.get('btn_back','Back')}</button>
        </form>
        '''
    
    if step == 1:
        # Choose language and reload UX
        languages = get_available_languages()
        language_options = "".join(
            [f'<option value="{l["code"]}" {"selected" if l["code"] == data.get("language","en-US") else ""}>{l["name"]}</option>' for l in languages]
        )
        content = f"""
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_1_title', 'Step 1: Language')}</h2>
        {error_html}
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="1">
            <label for="language">{trans.get('language_label','Interface Language')}</label><br>
            <select name="language" id="language" required style="width: 100%; padding: 8px; margin-bottom: 20px;">
                {language_options}
            </select>
            <button type="submit" style="width: 100%; padding: 10px; font-weight: bold; background: #007bff; color: white; border:none; border-radius: 5px; cursor: pointer;">
                {trans.get('btn_next','Next')}
            </button>
        </form>
        """

    elif step == 2:
        # Step 2 : create Superadmin
        content = f"""
        {back_button}
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_2_title', 'Step 2: Create Super Admin')}</h2>
        {error_html}
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="2">
            {_preserve_all_data(data)}
            <label for="email">{trans.get('email_label','Email')}</label><br>
            <input type="email" id="email" name="email" required style="width: 100%;" value="{data.get('email','')}"><br>
            <label for="password">{trans.get('password_label','Password')}</label><br>
            <input type="password" id="password" name="password" required style="width: 100%;"><br>
            <label for="password_confirm">{trans.get('password_confirm_label','Confirm Password')}</label><br>
            <input type="password" id="password_confirm" name="password_confirm" required style="width: 100%;"><br><br>
            <button type="submit" style="width: 100%; padding: 10px; font-weight: bold; background: #28a745; color: white; border:none; border-radius: 5px; cursor: pointer;">
                {trans.get('btn_create_super_admin','Create Admin')}
            </button>
        </form>
        """

    elif step == 3:
        # Step 3: Database schema - domains and users
        content = f"""
        {back_button}
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_3_title', 'Step 3: Database Schema')}</h2>
        <p>{trans.get('config_step_3_intro', 'Configure your Dovecot database table and field names.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="3">
            {_preserve_all_data(data)}
            <input type="hidden" name="language" value="{data.get('language', 'en-US')}">
            
            <h3>{trans.get('domains_table_title', 'Domains Table')}</h3>
            
            <label for="db_table_domains">{trans.get('table_name_label', 'Table Name')}</label><br>
            <input type="text" name="db_table_domains" value="{data.get('db_table_domains', 'domain')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_domain_id">{trans.get('field_id_label', 'ID Field')}</label><br>
            <input type="text" name="db_field_domain_id" value="{data.get('db_field_domain_id', 'id')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_domain_name">{trans.get('field_domain_name_label', 'Domain Name Field')}</label><br>
            <input type="text" name="db_field_domain_name" value="{data.get('db_field_domain_name', 'domain')}" required style="width: 100%; padding: 8px; margin-bottom: 20px;"><br>
            
            <h3>{trans.get('users_table_title', 'Users/Mailboxes Table')}</h3>
            
            <label for="db_table_users">{trans.get('table_name_label', 'Table Name')}</label><br>
            <input type="text" name="db_table_users" value="{data.get('db_table_users', 'users')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_user_id">{trans.get('field_id_label', 'ID Field')}</label><br>
            <input type="text" name="db_field_user_id" value="{data.get('db_field_user_id', 'id')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_user_email">{trans.get('field_email_label', 'Email Field')}</label><br>
            <input type="text" name="db_field_user_email" value="{data.get('db_field_user_email', 'email')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_user_password">{trans.get('field_password_label', 'Password Field')}</label><br>
            <input type="text" name="db_field_user_password" value="{data.get('db_field_user_password', 'crypt')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_user_active">{trans.get('field_active_label', 'Active Field')}</label><br>
            <input type="text" name="db_field_user_active" value="{data.get('db_field_user_active', 'active')}" required style="width: 100%; padding: 8px; margin-bottom: 20px;"><br>
            
            <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                {trans.get('btn_next', 'Next')}
            </button>
        </form>
        """
    
    elif step == 4:
        # Step 4: Aliases table
        content = f"""
        {back_button}
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_4_title', 'Step 4: Aliases Table')}</h2>
        <p>{trans.get('config_step_4_intro', 'Configure your aliases table structure.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="4">
            {_preserve_all_data(data)}
            
            <h3>{trans.get('aliases_table_title', 'Aliases Table')}</h3>
            
            <label for="db_table_aliases">{trans.get('table_name_label', 'Table Name')}</label><br>
            <input type="text" name="db_table_aliases" value="{data.get('db_table_aliases', 'alias')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_alias_id">{trans.get('field_id_label', 'ID Field')}</label><br>
            <input type="text" name="db_field_alias_id" value="{data.get('db_field_alias_id', 'id')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_alias_source">{trans.get('field_alias_source_label', 'Source Field')}</label><br>
            <input type="text" name="db_field_alias_source" value="{data.get('db_field_alias_source', 'source')}" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="db_field_alias_destination">{trans.get('field_alias_destination_label', 'Destination Field')}</label><br>
            <input type="text" name="db_field_alias_destination" value="{data.get('db_field_alias_destination', 'destination')}" required style="width: 100%; padding: 8px; margin-bottom: 20px;"><br>
            
            <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                {trans.get('btn_next', 'Next')}
            </button>
        </form>
        """
    
    elif step == 5:
        # Step 5: Business limits
        content = f"""
        {back_button}
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_5_title', 'Step 5: Business Limits')}</h2>
        <p>{trans.get('config_step_5_intro', 'Set default limits for your users.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="5">
            {_preserve_all_data(data)}
            
            <h3>{trans.get('business_limits_title', 'Business Limits')}</h3>
            
            <label for="max_mailboxes_per_user">{trans.get('max_mailboxes_label', 'Max Mailboxes per User')}</label><br>
            <input type="number" name="max_mailboxes_per_user" value="{data.get('max_mailboxes_per_user', 3)}" required style="width: 100%; padding: 8px; margin-bottom: 10px;" min="1" max="100"><br>
            
            <label for="max_aliases_per_mailbox">{trans.get('max_aliases_label', 'Max Aliases per Mailbox')}</label><br>
            <input type="number" name="max_aliases_per_mailbox" value="{data.get('max_aliases_per_mailbox', 100)}" required style="width: 100%; padding: 8px; margin-bottom: 20px;" min="1" max="1000"><br>
            
            <button type="submit" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                {trans.get('btn_finish_setup', 'Finish Setup')}
            </button>
        </form>
        """

    elif step == 6:
        # Generate cron script
        cron_script = generate_cron_script(data)
        content = f"""
        <h2>{trans.get('cron_script_title','pymailadmin connector cron script for Dovecot')}</h2>
        <p>{trans.get('cron_script_instructions','You may now connect <strong>to your Dovecot mail server</strong>, then:<br><ul><li>make sure you have python3 and python3-mysqldb installed</li><li>Copy this script somewhere on your Dovecot server, e.g. /opt/pymailadmin/scripts/pymailadmin-cron.py</li><li>Then create a crontab task as follows:<br><pre>*/2 * * * * root /usr/bin/python3 /opt/pymailadmin/scripts/pymailadmin-cron.py</pre></li></ul>')}</p>
        <textarea id="cron_script" readonly style="width: 100%; height: 600px; font-family: monospace; white-space: pre-wrap;">{cron_script}</textarea>
        <button onclick="copyCronScript()" style="margin-top:10px; padding: 10px 20px;">{trans.get('btn_copy_clipboard','Copy to Clipboard')}</button>
        <p>{trans.get('cron_script_footer','Installation complete!')}</p>
        <p><a href="/home" style="font-weight: bold; color: #28a745;">{trans.get('goto_dashboard','Go to Admin Dashboard')}</a></p>
        
        <script>
        function copyCronScript() {{
            var copyText = document.getElementById("cron_script");
            copyText.select();
            copyText.setSelectionRange(0, 99999); /* For mobile devices */
            navigator.clipboard.writeText(copyText.value).then(function() {{
                alert('Script copied to clipboard!');
            }}, function(err) {{
                alert('Failed to copy script');
            }});
        }}
        </script>
        """

    else:
        # fallback
        return first_setup_page(session, 'Invalid step')
    
    return html_template(trans.get('config_wizard_title','Configuration'), content)

def config_wizard_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') != 'super_admin':
        start_response("302 Found", [("Location", "/login")])
        return []
    
    if check_config_completed():
        start_response("302 Found", [("Location", "/home")])
        return []
    
    if environ['REQUEST_METHOD'] == 'GET':
        params = parse_qs(environ.get('QUERY_STRING',''))
        step = int(params.get('step', ['1'])[0])
        locale = params.get('locale', ['en-US'])[0]
        start_response("200 OK", [("Content-Type","text/html")])
        return [config_wizard_page(session, step, locale=locale).encode()]
    
    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        csrf_token = data.get('csrf_token', [''])[0]
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type","text/html")])
            return [b"Invalid CSRF token"]
        
        step = int(data.get('step', ['1'])[0])
        form_data = {k: v[0] if isinstance(v,list) else v for k,v in data.items()}
        locale = form_data.get('language', 'en-US')
        
        trans = load_translations(locale)

        if step == 1:
            if write_language_to_env(locale):
                importlib.reload(importlib.import_module('config_loader'))
                start_response("200 OK", [("Content-Type","text/html")])
                return [config_wizard_page(session, 2, data=form_data, locale=locale).encode()]
            else:
                start_response("500 Internal Server Error", [("Content-Type","text/html")])
                return [config_wizard_page(session, 1, error_msg=trans.get('config_write_failed','Write failed'), data=form_data, locale=locale).encode()]
        
        elif step == 2:
            # Validate and create superadmin
            email = form_data.get('email', '').strip()
            password = form_data.get('password', '')
            password_confirm = form_data.get('password_confirm', '')
            
            if not email or '@' not in email:
                return [config_wizard_page(session, 2, error_msg=trans.get('invalid_email'), data=form_data, locale=locale).encode()]
            if len(password) < 12:
                return [config_wizard_page(session, 2, error_msg=trans.get('password_too_short'), data=form_data, locale=locale).encode()]
            if password != password_confirm:
                return [config_wizard_page(session, 2, error_msg=trans.get('password_mismatch'), data=form_data, locale=locale).encode()]
            
            existing = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
            if existing:
                return [config_wizard_page(session, 2, error_msg=trans.get('email_already_exists'), data=form_data, locale=locale).encode()]
            try:
                password_hash = argon2.using(
                    type='ID',
                    time_cost=config['security']['argon2id']['time_cost'],
                    memory_cost=config['security']['argon2id']['memory_cost'] // 1024,
                    parallelism=config['security']['argon2id']['threads']
                ).hash(password)
                execute_query(config['sql']['insert_admin_user'], (email, password_hash))
                execute_query(config['sql']['update_admin_role_and_activate'], ('super_admin', email))
                
                user = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
                if user:
                    session.data['logged_in'] = True
                    session.data['email'] = email
                    session.data['role'] = user[0]['role']
                    session.data['id'] = user[0]['id']
                    session.save()
                
                start_response("200 OK", [("Content-Type","text/html")])
                return [config_wizard_page(session, 3, data=form_data, locale=locale).encode()]
            except Exception as e:
                logging.error(f"Error creating super_admin: {e}")
                return [config_wizard_page(session, 2, error_msg=trans.get('setup_failed'), data=form_data, locale=locale).encode()]

        elif 3 <= step < 5:
            start_response("200 OK", [("Content-Type","text/html")])
            return [config_wizard_page(session, step + 1, data=form_data, locale=locale).encode()]

        elif step == 5:
            if write_env_config(form_data):
                mark_config_completed()
                start_response("200 OK", [("Content-Type","text/html")])
                return [config_wizard_page(session, 6, data=form_data, locale=locale).encode()]
            else:
                start_response("500 Internal Server Error", [("Content-Type","text/html")])
                return [config_wizard_page(session, 5, error_msg=trans.get('config_write_failed'), data=form_data, locale=locale).encode()]

        elif step == 6:
            logging.info("Configuration wizard completed")
            start_response("302 Found", [("Location", "/home")])
            return []

        else:
            start_response("302 Found", [("Location", "/home")])
            return []
