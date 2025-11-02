# handlers/html.py

import os
from libs import config, translations

def navigation_menu(admin_user_email, admin_role):
    
    if admin_user_email:
        user_infos=f"""
            <li>{admin_user_email}({admin_role})</li>
            <li><a href="/logout">{translations["menu_logout_link"]}</a></li>
        """
    
    else:
        user_infos=""
        
    return f"""
    <nav>
        <ul>
            <li><a href="/home">{translations["menu_home_link"]}</a></li>
            <li><a href="/home">{translations["menu_dashboard_link"]}</a></li>
            {user_infos}
        </ul>
    </nav>
    """
    
def html_template(title, content, admin_user_email=None, admin_role=None):
    css_path = config['css']['main_css']
    pretty_name = config['PRETTY_NAME']
    menu = navigation_menu(admin_user_email, admin_role)
    
    return f"""
    <!DOCTYPE html>
    <html lang="{translations['html_lang']}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{pretty_name} - {title}</title>
        <link rel="stylesheet" href="/static/{css_path}">
    </head>
    <body>
        {menu}
        <h1>{title}</h1>
        {content}
    </body>
    </html>
    """
