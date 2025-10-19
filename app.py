# app.py

from middleware.session import SessionMiddleware
from routes.login import login_handler
from routes.dashboard import home_handler
from routes.user_management import edit_alias_handler, add_alias_handler, edit_user_handler, delete_user_handler
from routes.moderation import (
    confirm_registration_handler,
    moderation_queue_handler,
    approve_registration_handler,
    deny_registration_handler
)
from routes.register import register_handler
from handlers.static import static_handler

import logging
import os
log_dir = '/var/log/pymailadmin'

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pymailadmin/error.log'),
        logging.StreamHandler()
    ]
)

def application(environ, start_response):
    path = environ.get('PATH_INFO', '').rstrip('/')

    # Routes
     if path == '/login':
        return login_handler(environ, start_response)
    elif path == '/home':
        return home_handler(environ, start_response)
    elif path == '/editalias':
        return edit_alias_handler(environ, start_response)
    elif path == '/addalias':
        return add_alias_handler(environ, start_response)
    elif path == '/edituser':
        return edit_user_handler(environ, start_response)
    elif path == '/deleteuser':
        return delete_user_handler(environ, start_response)
    elif path.startswith('/static/'):
        return static_handler(environ, start_response)
    elif path == '/register':
        return register_handler(environ, start_response)
    elif path == '/register/confirm':
        return confirm_registration_handler(environ, start_response)
    elif path == '/moderate/pending':
        return moderation_queue_handler(environ, start_response)
    elif path == '/moderate/approve':
        return approve_registration_handler(environ, start_response)
    elif path == '/moderate/deny':
        return deny_registration_handler(environ, start_response)
    else:
        start_response("302 Found", [("Location", "/login")])
        return []

# Appliquer le middleware
app = SessionMiddleware(application)

