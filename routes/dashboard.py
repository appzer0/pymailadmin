# routes/dashboard.py

from libs import config, fetch_all, parse_qs
from handlers.html import html_template
from i18n.en_US import translations
from utils.limits import can_create_mailbox
from utils.alias_limits import can_create_alias, get_alias_count
import logging

def home_handler(environ, start_response):
    """Main dashboard - displays list of domains"""
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    admin_user_id = session.data['id']
    admin_role = session.data.get('role', 'user')
    admin_user_email = session.data.get('email', '')
        
    # Get all domains
    try:
        domains = fetch_all(config['sql_dovecot']['select_all_domains'], ())
    except Exception as e:
        logging.error(f"Error fetching domains: {e}")
        domains = []
    
    # Build domain list with mailbox counts
    domain_rows = ""
    for domain in domains:
        domain_id = domain['id']
        domain_name = domain['domain']
        
        # Get mailboxes count for this domain
        try:
            if admin_role == 'super_admin':
                # Super admin sees all mailboxes
                users_in_domain = fetch_all(
                    config['sql_dovecot']['select_users_by_domain'], 
                    (domain_id,)
                )
                mailbox_count = len(users_in_domain)
            else:
                # Regular users see only their owned mailboxes
                owned_ids_result = fetch_all(config['sql']['select_user_ids_by_owner'], (admin_user_id,))
                owned_ids = [row['user_id'] for row in owned_ids_result] if owned_ids_result else []
                
                if owned_ids:
                    users_in_domain = fetch_all(
                        config['sql_dovecot']['select_users_by_domain'], 
                        (domain_id,)
                    )
                    owned_users = [u for u in users_in_domain if u['id'] in owned_ids]
                    mailbox_count = len(owned_users)
                else:
                    mailbox_count = 0
                    
        except Exception as e:
            logging.error(f"Error counting mailboxes for domain {domain_name}: {e}")
            mailbox_count = 0
        
        domain_rows += f"""
        <tr>
            <td><a href="/domain?id={domain_id}">{domain_name}</a></td>
            <td>{mailbox_count}</td>
        </tr>
        """
    
    # Mailbox counter (only for non-super_admin)
    if admin_role != 'super_admin':
        can_create, current_count, max_count = can_create_mailbox(admin_user_id)
        counter_color = "red" if not can_create else "green"
        counter_html = f"""
        <div style="{counter_color};>
            <strong>{translations['mailbox_count_display'].format(count=current_count, max=max_count)}</strong>
        </div>
        """
        
        if can_create:
            create_btn = f'<a href="/createmailbox"><button>{translations["create_mailbox_btn"]}</button></a>'
        
        else:
            create_btn = f'<button disabled="disabled">{translations["create_mailbox_btn_disabled"]}</button>'
            
    else:
        counter_html = ""
        create_btn = ""
    
    content = f"""
    <h2>{translations['domains_list_title']}</h2>
    
    {counter_html}
    {create_btn}
    
    <table>
        <thead>
            <tr>
                <th>{translations['domain_col']}</th>
                <th>{translations['mailboxes_count_col']}</th>
            </tr>
        </thead>
        <tbody>
            {domain_rows if domain_rows else f'<tr><td colspan="2">{translations["no_domains"]}</td></tr>'}
        </tbody>
    </table>
    
    """
    
    body = html_template(translations['dashboard_title'], content, admin_user_email=admin_user_email, admin_role=admin_role)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]


def domain_handler(environ, start_response):
    """Display mailboxes for a specific domain"""
    session = environ.get('session', None)
    
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    # Get domain ID from query string
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    domain_id = params.get('id', [''])[0]
    
    if not domain_id or not domain_id.isdigit():
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Invalid domain ID"]
    
    admin_user_id = session.data['id']
    admin_role = session.data.get('role', 'user')
    admin_user_email = session.data.get('email', '')
    
    # Get domain info
    try:
        domain = fetch_all(config['sql_dovecot']['select_domain_by_id'], (int(domain_id),))
    
        if not domain:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Domain not found"]
    
        domain_name = domain[0]['domain']
    
    except Exception as e:
        logging.error(f"Error fetching domain: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [b"Error loading domain"]
    
    # Get mailboxes in this domain
    try:
        if admin_role == 'super_admin':
            # Super admin sees all mailboxes
            users_data = fetch_all(
                config['sql_dovecot']['select_users_by_domain'], 
                (int(domain_id),)
            )
        
        else:
            # Regular users see only their owned mailboxes
            owned_ids_result = fetch_all(config['sql']['select_user_ids_by_owner'], (admin_user_id,))
            owned_ids = [row['user_id'] for row in owned_ids_result] if owned_ids_result else []
            
            if owned_ids:
                users_in_domain = fetch_all(
                    config['sql_dovecot']['select_users_by_domain'], 
                    (int(domain_id),)
                )
                users_data = [u for u in users_in_domain if u['id'] in owned_ids]
            
            else:
                users_data = []
                
    except Exception as e:
        logging.error(f"Error fetching mailboxes: {e}")
        users_data = []
    
    # Get pending states
    try:
        rekey_emails = [r['email'] for r in fetch_all(config['sql']['select_all_rekey_pending'], ())]
        deletion_emails = [r['email'] for r in fetch_all(config['sql']['select_all_deletion_pending'], ())]
        creation_emails = [r['email'] for r in fetch_all(config['sql']['select_all_creation_pending'], ())]
    
    except Exception as e:
        logging.error(f"Error fetching pending states: {e}")
        rekey_emails = []
        deletion_emails = []
        creation_emails = []
    
    # Build mailbox rows
    rows = ""
    
    for user in users_data:
        email = user['email']
        user_id = user['id']
        
        # Get alias count for this mailbox
        alias_count = get_alias_count(email)
        
        # Determine status
        if email in creation_emails:
            status = translations['creation_status']
    
        elif email in rekey_emails:
            status = translations['rekey_status']
    
        elif email in deletion_emails:
            status = translations['deletion_status']
    
        else:
            status = translations['active_status']
        
        # Actions column (only for non-super_admin)
        if admin_role == 'super_admin':
            actions = f'<a href="/mailbox?id={user_id}">{translations["btn_view"]}</a>'
    
        else:
            # Check if can add alias
            can_add_alias, _, max_aliases = can_create_alias(email)
            
            if email in creation_emails or email in rekey_emails or email in deletion_emails:
                actions = f"<em>{translations['pending']}</em>"
    
            else:
                actions = f'<a href="/mailbox?id={user_id}">{translations["btn_manage"]}</a>'
        
        rows += f"""
        <tr>
            <td>{email}</td>
            <td>{alias_count}</td>
            <td>{status}</td>
            <td>{actions}</td>
        </tr>
        """
    
    content = f"""
    <h2>{domain_name}</h2>
    
    <table>
        <thead>
            <tr>
                <th>{translations['email_col']}</th>
                <th>{translations['aliases_count_col']}</th>
                <th>{translations['status_col']}</th>
                <th>{translations['actions_col']}</th>
            </tr>
        </thead>
        <tbody>
            {rows if rows else f'<tr><td colspan="4">{translations["no_mailboxes"]}</td></tr>'}
        </tbody>
    </table>
    """
    
    body = html_template(translations['domain_mailboxes_title'].format(domain=domain_name), content, admin_user_email=admin_user_email, admin_role=admin_role)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]


def mailbox_handler(environ, start_response):
    """Display detailed view of a specific mailbox with aliases"""
    session = environ.get('session', None)
    
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    # Get mailbox ID from query string
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    user_id = params.get('id', [''])[0]
    
    if not user_id or not user_id.isdigit():
        start_response("400 Bad Request", [("Content-Type", "text/html")])
        return [b"Invalid mailbox ID"]
    
    admin_user_id = session.data['id']
    admin_role = session.data.get('role', 'user')
    admin_user_email = session.data.get('email', '')
    
    # Check ownership (skip for super_admin)
    if admin_role != 'super_admin':
        try:
            is_owner = fetch_all(config['sql']['is_owner'], (admin_user_id, int(user_id)))
            
            if not is_owner:
                start_response("403 Forbidden", [("Content-Type", "text/html")])
                return [translations['ownership_required'].encode('utf-8')]
        
        except Exception as e:
            logging.error(f"Error checking ownership: {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/html")])
            return [b"Error checking permissions"]
    
    # Get mailbox info
    try:
        user = fetch_all(config['sql_dovecot']['select_user_by_id'], (int(user_id),))
        
        if not user:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Mailbox not found"]
        
        email = user[0]['email']
        domain_id = user[0]['domain_id']
        
        # Get domain name
        domain = fetch_all(config['sql_dovecot']['select_domain_by_id'], (domain_id,))
        domain_name = domain[0]['domain'] if domain else "Unknown"
        
    except Exception as e:
        logging.error(f"Error fetching mailbox: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [b"Error loading mailbox"]
    
    # Get aliases for this mailbox
    try:
        aliases = fetch_all(
            config['sql_dovecot']['select_alias_by_mailbox'], 
            (domain_id, email)
        )
    except Exception as e:
        logging.error(f"Error fetching aliases: {e}")
        aliases = []
    
    # Get alias count and check limit
    alias_count = len(aliases)
    can_add_alias, _, max_aliases = can_create_alias(email)
    
    # Build alias rows
    alias_rows = ""
    
    for alias in aliases:
        
        # Actions (only for non-super_admin)
        if admin_role == 'super_admin':
            actions = ""
        
        else:
            actions = f'<a href="/editalias?id={alias["id"]}">{translations["btn_modify"]}</a>'
        
        alias_rows += f"""
        <tr>
            <td>{alias['source']}</td>
            <td>{alias['destination']}</td>
            <td>{actions}</td>
        </tr>
        """
    
    # Add alias button (only for non-super_admin)
    if admin_role != 'super_admin':
        
        if can_add_alias:
            add_alias_btn = f'<a href="/addalias?destination={email}"><button>{translations["btn_add_alias"]}</button></a>'
        
        else:
            add_alias_btn = f'<button disabled style="opacity: 0.5; cursor: not-allowed;">{translations["btn_add_alias"]} ({translations["limit_reached"]})</button>'
    
    else:
        add_alias_btn = ""
    
    # Actions section (only for non-super_admin)
    if admin_role != 'super_admin':
        actions_section = f"""
        <h3>{translations['mailbox_actions_title']}</h3>
        <p>
            <a href="/edituser?id={user_id}"><button>{translations["change_password_btn"]}</button></a>
            <a href="/deleteuser?id={user_id}"><button style="background: red; color: white;">{translations["btn_delete"]}</button></a>
        </p>
        """
    
    else:
        actions_section = ""
    
    content = f"""
    <h2>{translations['mailbox_details_title']}</h2>
    
    <p><a href="/domain?id={domain_id}">{translations['back_to_domain']}</a></p>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <p><strong>{translations['email_label']}:</strong> {email}</p>
        <p><strong>{translations['domain_label']}:</strong> {domain_name}</p>
        <p><strong>{translations['aliases_count_label']}:</strong> {alias_count} / {max_aliases}</p>
    </div>
    
    {actions_section}
    
    <h3>{translations['aliases_title']}</h3>
    {add_alias_btn}
    
    <table border="1" style="margin-top: 15px;">
        <thead>
            <tr>
                <th>{translations['alias_source_col']}</th>
                <th>{translations['alias_destination_col']}</th>
                {'<th>' + translations["actions_col"] + '</th>' if admin_role != 'super_admin' else ''}
            </tr>
        </thead>
        <tbody>
            {alias_rows if alias_rows else f'<tr><td colspan="{"3" if admin_role != "super_admin" else "2"}">{translations["no_aliases"]}</td></tr>'}
        </tbody>
    </table>
    """
    
    body = html_template(translations['mailbox_details_title'], content, admin_user_email=admin_user_email, admin_role=admin_role)
    start_response("200 OK", [("Content-Type", "text/html")])
    return [body.encode()]
