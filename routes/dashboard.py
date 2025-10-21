# routes/dashboard.py

from libs import config, fetch_all
from handlers.html import html_template

# --- Dashboard display ---
def delete_user_form(user_id, csrf_token):
    return f'''
    <form method="POST" action="/deleteuser" style="display:inline;">
        <input type="hidden" name="user_id" value="{user_id}">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <button type="submit" onclick="return confirm('Êtes-vous sûr⋅e ?')">Supprimer</button>
    </form>'''

def home_page(users_data, aliases_data, session):
    rows = ""
        
    for user in users_data:
        # Filter user aliases
        user_aliases = [a for a in aliases_data if a['destination'] == user['email']]
        user_aliases.sort(key=lambda x: x['source'])

        alias_list = "".join(
            f"<li>{a['source']} → {a['destination']} "
            f"(<a href='/editalias?id={a['id']}'>Éditer</a>)</li>"
            for a in user_aliases
        )
        alias_html = f"<ul>{alias_list}</ul>" if alias_list else "<em>Aucun alias</em>"

        # Rekey / Deletion pending states
        rekey_emails = [r['email'] for r in fetch_all(config['sql']['select_all_rekey_pending'], None)]
        deletion_emails = [r['email'] for r in fetch_all(config['sql']['select_all_deletion_pending'], None)]

        if user['email'] in rekey_emails:
            edit_user_link = "<em>⚠ En cours de rechiffrement…  ⚠</em>"
            delete_form = "<em>…</em>"
            add_link = "…"
            status_note = "<strong>⚠ RE-ENRCRYPTION RUNNING… ⚠</strong> Your mailbox is being re-encrypted. It is disabled for 15 minutes waiting to finish to be re-encrypt  with your new password."
        elif user['email'] in deletion_emails:
            edit_user_link = "<em>⚠ Pending Deletion… ⚠</em>"
            delete_form = "<em>…</em>"
            add_link = "…"
            status_note = "<strong>⚠ SCHEDULED DELETION… ⚠</strong> This mailbox will be definitely deleted in 48h."
        else:
            edit_user_link = f'<a href="/edituser?id={user["id"]}"><button>Change Password</button></a>'
            delete_form = delete_user_form(user['id'], session.get_csrf_token())
            add_link = f'<a href="/addalias?destination={user["email"]}">Add an alias</a>'
            status_note = ""

        rows += f"""
        <div class="notice">{status_note}</div>
        <tr>
            <td>{user['email']}</td>
            <td>{edit_user_link} {delete_form}</td>
            <td>{alias_html} - {add_link}</td>
        </tr>
        """

    table_html = f"""
    <table border="1">
        <thead>
            <tr><th>Mailbox</th><th>Actions</th><th>Alias</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """
    return html_template("My mailboxes", table_html)

def home_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    admin_user_id = session.data['id']

    # Get ownership IDs
    user_ids = [r['user_id'] for r in fetch_all(config['sql']['select_user_ids_by_owner'], (admin_user_id,))]
    
    if not user_ids:
        users = []
    else:
        placeholders = ','.join(['%s'] * len(user_ids))
        query = config['sql']['select_user_by_id_in'].replace('{user_ids}', placeholders)
        users = fetch_all(query, user_ids)

    # Get aliases
    aliases = []
    for user in users:
        user_aliases = fetch_all(config['sql']['select_alias_by_mailbox'], (user['domain_id'], user['email']))
        aliases.extend(user_aliases)
    
    start_response("200 OK", [("Content-Type", "text/html")])
    return [home_page(users, aliases, session).encode()]
