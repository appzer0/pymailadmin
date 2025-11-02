# app.py

from middleware.session import SessionMiddleware
from routes.login import login_handler
from routes.dashboard import home_handler, domain_handler
from routes.mailbox_creation import create_mailbox_handler
from routes.user_management import (
    edit_alias_handler,
    add_alias_handler,
    edit_user_handler,
    delete_user_handler
)
from routes.moderation import (
    confirm_registration_handler,
    moderation_queue_handler,
    approve_registration_handler,
    deny_registration_handler
)
from routes.register import register_handler
from routes.logout import logout_handler
from handlers.static import static_handler
from utils.check_super_admin_exists import check_super_admin_exists
from routes.initial_setup import config_wizard_handler

import logging
import os
log_dir = '/var/log/pymailadmin'

from libs import config

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
    
    ## Unimplented for now:
    ## If superadmin does not exist, route to the initial-setup wizard
    #if not check_super_admin_exists():
    #    if path != '/setup/config':
    #        start_response("302 Found", [("Location", "/setup/config")])
    #        return [b"Redirecting to setup..."]
    #else:            
    #    if path == '/setup/config':
    #        try: return config_wizard_handler(environ, start_response)
    #        except Exception as e: logging.error(f"Error in config_wizard_handler: {e}"); return [b"Error in initial_setup.py"]
 
    try:
        # Routes
        if path == '' or path == '/':
            start_response("302 Found", [("Location", "/login")])
            return [b"Redirecting to login..."]
        elif path == '/login':
            response = login_handler(environ, start_response)
        elif path == '/home':
            response = home_handler(environ, start_response)
        elif path == '/domain':
            response = domain_handler(environ, start_response)
        elif path == '/mailbox':
            response = mailbox_handler(environ, start_response)
        elif path == '/createmailbox':
            response = create_mailbox_handler(environ, start_response)
        elif path == '/editalias':
            response = edit_alias_handler(environ, start_response)
        elif path == '/addalias':
            response = add_alias_handler(environ, start_response)
        elif path == '/edituser':
            response = edit_user_handler(environ, start_response)
        elif path == '/deleteuser':
            response = delete_user_handler(environ, start_response)
        elif path.startswith('/static/'):
            response = static_handler(environ, start_response)
        elif path == '/register':
            response = register_handler(environ, start_response)
        elif path == '/register/confirm':
            response = confirm_registration_handler(environ, start_response)
        elif path == '/moderate/pending':
            response = moderation_queue_handler(environ, start_response)
        elif path == '/moderate/approve':
            response = approve_registration_handler(environ, start_response)
        elif path == '/moderate/deny':
            response = deny_registration_handler(environ, start_response)
        elif path == '/logout':
            response = logout_handler(environ, start_response)
        else:
            start_response("302 Found", [("Location", "/login")])
            return [b"Redirecting to login (fallback)"]

        response = list(response) if response is not None else [b'Internal Server Error']

        if response is None:
            logging.error(f"Handler for {path} returned None")
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
            return [b"Internal Server Error: no response"]

        return response

    except Exception as e:
        logging.error(f"Unhandled exception in handler for {path}: {e}", exc_info=True)
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [b"Internal Server Error"]

# Middleware
app = SessionMiddleware(application)

