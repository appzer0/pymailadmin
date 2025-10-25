# routes/login.py

from passlib.hash import argon2
from utils.security import get_client_ip, check_rate_limit
from utils.db import fetch_all, execute_query
from handlers.html import html_template
from libs import translations, parse_qs, config
import logging
import os

def check_super_admin_exists():
    """Check if at least one super_admin exists"""
    try:
        result = fetch_all(config['sql']['count_super_admins'], ())
        return result[0]['count'] > 0 if result else False
    except Exception as e:
        logging.error(f"Error checking super_admin existence: {e}")
        return False

def check_config_completed():
    """Check if initial configuration has been completed"""
    # Check if a marker file exists
    config_marker = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.config_completed')
    return os.path.exists(config_marker)

def mark_config_completed():
    """Mark configuration as completed"""
    config_marker = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.config_completed')
    try:
        with open(config_marker, 'w') as f:
            f.write('1')
        return True
    except Exception as e:
        logging.error(f"Error creating config marker: {e}")
        return False

def get_available_languages():
    """Scan i18n directory for available language files"""
    i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'i18n')
    language_files = glob.glob(os.path.join(i18n_dir, '*_*.py'))
    
    languages = []
    for filepath in language_files:
        filename = os.path.basename(filepath)
        if filename == '__init__.py':
            continue
        
        # Extract locale from filename (e.g., en_US.py -> en-US)
        locale = filename.replace('.py', '').replace('_', '-')
        
        # Try to load display name from the file
        try:
            module_name = filename.replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            display_name = getattr(module, 'language_name', locale)
        except Exception:
            display_name = locale
        
        languages.append({
            'code': locale,
            'name': display_name
        })
    
    # Sort by code
    languages.sort(key=lambda x: x['code'])
    
    return languages if languages else [{'code': 'en-US', 'name': 'English (US)'}]

def load_translations(locale_code):
    """Load translations for a specific locale"""
    # Convert locale code to module name (en-US -> en_US)
    module_name = locale_code.replace('-', '_')
    
    try:
        i18n_module = importlib.import_module(f'i18n.{module_name}')
        return getattr(i18n_module, 'translations', {})
    except Exception as e:
        logging.error(f"Error loading translations for {locale_code}: {e}")
        # Fallback to en_US
        try:
            i18n_module = importlib.import_module('i18n.en_US')
            return getattr(i18n_module, 'translations', {})
        except Exception:
            return {}

def write_language_to_env(language_code):
    """Write APP_LANGUAGE to .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    try:
        # Read existing .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update APP_LANGUAGE
        new_lines = []
        found = False
        for line in lines:
            if line.startswith('APP_LANGUAGE='):
                new_lines.append(f'APP_LANGUAGE={language_code}\n')
                found = True
            else:
                new_lines.append(line)
        
        # If not found, add it
        if not found:
            new_lines.append(f'APP_LANGUAGE={language_code}\n')
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        logging.error(f"Error writing language to .env: {e}")
        return False


def first_setup_page(session, error_msg=None):
    """Display first-time setup page to create super_admin"""
    token = session.get_csrf_token()
    
    # Load default translations (en-US)
    trans = load_translations('en-US')
    
    error_html = f'<p style="color: red; font-weight: bold;">{error_msg}</p>' if error_msg else ''
    
    content = f"""
    <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 2px solid #28a745; border-radius: 8px; background: #f0f9ff;">
        <h2 style="color: #28a745;">🎉 {trans.get('first_setup_title', 'Welcome!')}</h2>
        <p>{trans.get('first_setup_intro', 'Create your first administrator account.')}</p>
        <p><strong>{trans.get('first_setup_warning', 'This account will have full privileges.')}</strong></p>
        
        {error_html}
        
        <form method="POST" action="/login/setup">
            <input type="hidden" name="csrf_token" value="{token}">
            
            <label for="email">{trans.get('email_label', 'Email')}</label><br>
            <input type="email" id="email" name="email" placeholder="admin@example.com" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="password">{trans.get('password_label', 'Password')}</label><br>
            <input type="password" id="password" name="password" required style="width: 100%; padding: 8px; margin-bottom: 5px;"><br>
            <small style="color: #666;">{trans.get('password_requirements', 'Minimum 8 characters')}</small><br><br>
            
            <label for="password_confirm">{trans.get('password_confirm_label', 'Confirm Password')}</label><br>
            <input type="password" id="password_confirm" name="password_confirm" required style="width: 100%; padding: 8px; margin-bottom: 15px;"><br>
            
            <button type="submit" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                {trans.get('btn_create_super_admin', 'Create Admin')}
            </button>
        </form>
    </div>
    """
    return html_template(trans.get('first_setup_title', 'Setup'), content)

def config_wizard_page(session, step=1, error_msg=None, data=None, locale='en-US'):
    """Display configuration wizard"""
    token = session.get_csrf_token()
    data = data or {}
    
    # Load translations for selected locale
    trans = load_translations(locale)
    
    error_html = f'<p style="color: red; font-weight: bold;">{error_msg}</p>' if error_msg else ''
    
    if step == 1:
        # Step 1: Language selection
        languages = get_available_languages()
        
        language_options = ""
        for lang in languages:
            selected = 'selected' if lang['code'] == data.get('language', 'en-US') else ''
            language_options += f'<option value="{lang["code"]}" {selected}>{lang["name"]}</option>'
        
        content = f"""
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_1_title', 'Step 1: Language')}</h2>
        <p>{trans.get('config_step_1_intro', 'Select your preferred language for the interface.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="1">
            
            <label for="language">{trans.get('language_label', 'Interface Language')}</label><br>
            <select name="language" id="language" required style="width: 100%; padding: 8px; margin-bottom: 20px;">
                {language_options}
            </select>
            
            <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                {trans.get('btn_next', 'Next')}
            </button>
        </form>
        """
    
    elif step == 2:
        # Step 2: Database schema - domains and users
        content = f"""
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_2_title', 'Step 2: Database Schema')}</h2>
        <p>{trans.get('config_step_2_intro', 'Configure your Dovecot database table and field names.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="2">
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
    
    elif step == 3:
        # Step 3: Aliases table
        content = f"""
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_3_title', 'Step 3: Aliases Table')}</h2>
        <p>{trans.get('config_step_3_intro', 'Configure your aliases table structure.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="3">
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
    
    elif step == 4:
        # Step 4: Business limits
        content = f"""
        <h2>{trans.get('config_wizard_title', 'Configuration')} - {trans.get('config_step_4_title', 'Step 4: Business Limits')}</h2>
        <p>{trans.get('config_step_4_intro', 'Set default limits for your users.')}</p>
        
        {error_html}
        
        <form method="POST" action="/setup/config">
            <input type="hidden" name="csrf_token" value="{token}">
            <input type="hidden" name="step" value="4">
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
    
    return html_template(trans.get('config_wizard_title', 'Configuration'), content)

def _preserve_all_data(data):
    """Generate hidden fields to preserve all previous data"""
    excluded = ['csrf_token', 'step']
    hidden_fields = ""
    for key, value in data.items():
        if key not in excluded:
            hidden_fields += f'<input type="hidden" name="{key}" value="{value}">\n'
    return hidden_fields

def write_env_config(data):
    """Write configuration to .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    try:
        # Read existing .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update variables
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
        
        # Update lines
        new_lines = []
        updated_keys = set()
        
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
        
        # Add missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f'{key}={value}\n')
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        logging.error(f"Error writing .env configuration: {e}")
        return False

def login_page(session, error_msg=None):
    """Display standard login page"""
    token = session.get_csrf_token()
    
    error_html = f'<p style="color: red; font-weight: bold;">{error_msg}</p>' if error_msg else ''
    
    content = f"""
    <div style="max-width: 400px; margin: 0 auto; padding: 20px;">
        {error_html}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{token}">
            
            <label for="email">{translations['email_label']}</label><br>
            <input type="email" id="email" name="email" placeholder="your@email.com" required style="width: 100%; padding: 8px; margin-bottom: 10px;"><br>
            
            <label for="password">{translations['password_label']}</label><br>
            <input type="password" id="password" name="password" required style="width: 100%; padding: 8px; margin-bottom: 15px;"><br>
            
            <button type="submit" style="width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                {translations['btn_login']}
            </button>
        </form>
    </div>
    """
    return html_template(translations['login_title'], content)

def login_handler(environ, start_response):
    """Handle login or first-time setup"""
    
    # Check if this is first-time setup
    if not check_super_admin_exists():
        # Display setup page
        if environ['REQUEST_METHOD'] == 'GET':
            session = environ['session']
            if not session.id:
                session.save()
            start_response("200 OK", [("Content-Type", "text/html")])
            return [first_setup_page(session).encode()]
        
        # POST to /login during setup shouldn't happen, redirect
        start_response("302 Found", [("Location", "/login")])
        return []
    
    # Normal login flow
    if environ['REQUEST_METHOD'] == 'GET':
        session = environ['session']
        if not session.id:
            session.save()
        start_response("200 OK", [("Content-Type", "text/html")])
        return [login_page(session).encode()]

    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)

        email = data.get('email', [''])[0].strip()
        password = data.get('password', [''])[0]
        csrf_token = data.get('csrf_token', [''])[0]

        # Rate limiting
        ip = get_client_ip(environ)
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
            return [translations['too_many_attempts'].encode('utf-8')]

        # CSRF validation
        session = environ['session']
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [translations['csrf_invalid'].encode('utf-8')]

        # Email validation
        if not email or '@' not in email:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [login_page(session, translations['invalid_email']).encode()]

        # Authenticate user
        user = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
        if user and argon2.verify(password, user[0]['password_hash']):
            # Successful login
            session.data['logged_in'] = True
            session.data['email'] = email
            session.data['role'] = user[0]['role']
            session.data['id'] = user[0]['id']
            if not session.id:
                session.save()
            start_response("302 Found", [("Location", "/home")])
            return []
        else:
            # Failed login
            start_response("401 Unauthorized", [("Content-Type", "text/html")])
            return [login_page(session, translations['invalid_credentials']).encode()]

def setup_handler(environ, start_response):
    """Handle first-time super_admin creation"""
    
    # Security: Check if super_admin already exists
    if check_super_admin_exists():
        start_response("302 Found", [("Location", "/login")])
        return []
    
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/html")])
        return [b"Method not allowed"]
    
    content_length = int(environ.get('CONTENT_LENGTH', 0))
    post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
    data = parse_qs(post_data)
    
    session = environ['session']
    csrf_token = data.get('csrf_token', [''])[0]
    
    # Load translations
    trans = load_translations('en-US')
    
    # CSRF validation
    if not session.validate_csrf_token(csrf_token):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [trans.get('csrf_invalid', 'Invalid token').encode('utf-8')]
    
    email = data.get('email', [''])[0].strip()
    password = data.get('password', [''])[0]
    password_confirm = data.get('password_confirm', [''])[0]
    
    # Validation (same as before)
    if not email or '@' not in email:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [first_setup_page(session, trans.get('invalid_email', 'Invalid email')).encode()]
    
    if len(password) < 8:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [first_setup_page(session, trans.get('password_too_short', 'Password too short')).encode()]
    
    if password != password_confirm:
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [first_setup_page(session, trans.get('password_mismatch', 'Passwords do not match')).encode()]
    
    existing = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
    if existing:
        start_response("409 Conflict", [("Content-Type", "text/html")])
        return [first_setup_page(session, trans.get('email_already_exists', 'Email exists')).encode()]
    
    # Create super_admin
    try:
        password_hash = argon2.using(
            type='ID',
            time_cost=config['security']['argon2id']['time_cost'],
            memory_cost=config['security']['argon2id']['memory_cost'] // 1024,
            parallelism=config['security']['argon2id']['threads']
        ).hash(password)
        
        execute_query(config['sql']['insert_admin_user'], (email, password_hash))
        execute_query(config['sql']['update_admin_role_and_activate'], ('super_admin', email))
        
        logging.info(f"First super_admin created: {email}")
        
        # Auto-login
        user = fetch_all(config['sql']['select_admin_user_by_email'], (email,))
        if user:
            session.data['logged_in'] = True
            session.data['email'] = email
            session.data['role'] = user[0]['role']
            session.data['id'] = user[0]['id']
            session.save()
        
        # Redirect to configuration wizard
        start_response("302 Found", [("Location", "/setup/config")])
        return []
        
    except Exception as e:
        logging.error(f"Error creating super_admin: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [first_setup_page(session, trans.get('setup_failed', 'Setup failed')).encode()]

def config_wizard_handler(environ, start_response):
    """Handle configuration wizard steps"""
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in') or session.data.get('role') != 'super_admin':
        start_response("302 Found", [("Location", "/login")])
        return []
    
    # Check if config already completed
    if check_config_completed():
        start_response("302 Found", [("Location", "/home")])
        return []
    
    if environ['REQUEST_METHOD'] == 'GET':
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        step = int(params.get('step', ['1'])[0])
        locale = params.get('locale', ['en-US'])[0]
        
        start_response("200 OK", [("Content-Type", "text/html")])
        return [config_wizard_page(session, step, locale=locale).encode()]
    
    elif environ['REQUEST_METHOD'] == 'POST':
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        data = parse_qs(post_data)
        
        csrf_token = data.get('csrf_token', [''])[0]
        if not session.validate_csrf_token(csrf_token):
            start_response("403 Forbidden", [("Content-Type", "text/html")])
            return [b"Invalid CSRF token"]
        
        step = int(data.get('step', ['1'])[0])
        
        # Convert parsed data to dict
        form_data = {k: v[0] if isinstance(v, list) else v for k, v in data.items()}
        
        # Get selected locale
        locale = form_data.get('language', 'en-US')
        
        # Step 1: Write language to .env and reload
        if step == 1:
            if write_language_to_env(locale):
                # Reload config to apply new language
                importlib.reload(importlib.import_module('config_loader'))
                
                # Go to step 2 with selected language
                start_response("200 OK", [("Content-Type", "text/html")])
                return [config_wizard_page(session, 2, data=form_data, locale=locale).encode()]
            else:
                trans = load_translations(locale)
                start_response("500 Internal Server Error", [("Content-Type", "text/html")])
                return [config_wizard_page(session, 1, error_msg=trans.get('config_write_failed', 'Write failed'), data=form_data, locale=locale).encode()]
        
        elif step < 4:
            # Go to next step
            start_response("200 OK", [("Content-Type", "text/html")])
            return [config_wizard_page(session, step + 1, data=form_data, locale=locale).encode()]
        else:
            # Final step - write configuration
            if write_env_config(form_data):
                mark_config_completed()
                logging.info("Configuration wizard completed")
                start_response("302 Found", [("Location", "/home")])
                return []
            else:
                trans = load_translations(locale)
                start_response("500 Internal Server Error", [("Content-Type", "text/html")])
                return [config_wizard_page(session, 4, error_msg=trans.get('config_write_failed', 'Write failed'), data=form_data, locale=locale).encode()]

