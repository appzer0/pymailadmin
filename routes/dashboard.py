# routes/dashboard.py

from libs import config, fetch_all, execute_query
from handlers.html import html_template

# --- Affichage du dashboard ---
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
        # Filtrer les alias pour cet utilisateur
        user_aliases = [a for a in aliases_data if a['destination'] == user['email']]
        user_aliases.sort(key=lambda x: x['source'])

        alias_list = "".join(
            f"<li>{a['source']} → {a['destination']} "
            f"(<a href='/editalias?id={a['id']}'>Éditer</a>)</li>"
            for a in user_aliases
        )
        alias_html = f"<ul>{alias_list}</ul>" if alias_list else "<em>Aucun alias</em>"

        # États de rekey / suppression
        rekey_emails = [r['email'] for r in fetch_all(config['sql']['select_all_rekey_pending'], None)]
        deletion_emails = [r['email'] for r in fetch_all(config['sql']['select_all_deletion_pending'], None)]

        if user['email'] in rekey_emails:
            edit_user_link = "<em>⚠ En cours de rechiffrement…  ⚠</em>"
            delete_form = "<em>…</em>"
            add_link = "…"
            status_note = "<strong>⚠ RECHIFFREMENT EN COURS… NE RÉACTUALISEZ PAS CETTE PAGE !</strong> Votre boîte est en cours de rechiffrement."
        elif user['email'] in deletion_emails:
            edit_user_link = "<em>Suppression en cours…</em>"
            delete_form = "<em>Annulé</em>"
            add_link = "..."
            status_note = "<strong>🗑️ SUPPRESSION PROGRAMMÉE</strong> — Cette boîte sera supprimée dans 48h."
        else:
            edit_user_link = f'<a href="/edituser?id={user["id"]}"><button>Changer mot de passe</button></a>'
            delete_form = delete_user_form(user['id'], session.get_csrf_token())
            add_link = f'<a href="/addalias?destination={user["email"]}">Ajouter un alias</a>'
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
            <tr><th>Boîte Mail</th><th>Actions</th><th>Alias</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """
    return html_template("Mes Boîtes Mail", table_html)

def home_handler(environ, start_response):
    session = environ.get('session', None)
    if not session or not session.data.get('logged_in'):
        start_response("302 Found", [("Location", "/login")])
        return []

    admin_user_id = session.data['id']

    # Récupérer les user_ids via ownerships
    user_ids = [r['user_id'] for r in fetch_all(config['sql']['select_user_ids_by_owner'], (admin_user_id,))]
    
    if not user_ids:
        users = []
    else:
        placeholders = ','.join(['%s'] * len(user_ids))
        users = fetch_all(f"SELECT * FROM users WHERE id IN ({placeholders})", user_ids)

    # Récupérer les alias
    aliases = []
    for user in users:
        user_aliases = fetch_all(config['sql']['select_alias_by_mailbox'], (user['domain_id'], user['email']))
        aliases.extend(user_aliases)
    
    # Nettoyage
    timeout_minutes = 15
    execute_query(config['sql']['cleanup_expired_rekey'], (timeout_minutes,))
    execute_query(config['sql']['reactivate_user_after_rekey_timeout'], (timeout_minutes,))
    execute_query(config['sql']['cleanup_expired_deletion'], (48,))
    
    start_response("200 OK", [("Content-Type", "text/html")])
    return [home_page(users, aliases, session).encode()]
