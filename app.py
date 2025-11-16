# app.py

from middleware.session import SessionMiddleware
from utils.route_dispatcher import dispatch_route
from routes.login import login_handler
from routes.dashboard import home_handler, domain_handler, mailbox_handler
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
    method = environ.get('REQUEST_METHOD', 'GET')
    
    ## Initial-setup wizard, unimplented for now:
    ## If superadmin does not exist, route to the initial-setup wizard
    #if not check_super_admin_exists():
    #    if path != '/setup/config':
    #        start_response("302 Found", [("Location", "/setup/config")])
    #        return [b"Redirecting to setup..."]
    #else:            
    #    if path == '/setup/config':
    #        try: return config_wizard_handler(environ, start_response)
    #        except Exception as e: logging.error(f"Error in config_wizard_handler: {e}"); return [b"Error in initial_setup.py"]
    
    # Routes
    if path.startswith('/static/'):
        return static_handler(environ, start_response)
    
    if path == '/login':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=login_handler,
            post_handler=login_handler
        )
    
    elif path == '/home':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=home_handler,
            post_action_mapping={
                'domain': domain_handler,
                'create_mailbox': create_mailbox_handler
            }
        )
    
    elif path == '/domain':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=None,
            post_action_mapping={
                'view_mailbox': mailbox_handler,
                'manage_mailbox': mailbox_handler
            }
        )
    
    elif path == '/mailbox':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=None,
            post_action_mapping={
                'edit_alias': edit_alias_handler,
                'add_alias': add_alias_handler,
                'edit_user': edit_user_handler,
                'delete_user': delete_user_handler
            }
        )
    
    elif path == '/register':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=register_handler,
            post_handler=register_handler
        )
    
    elif path == '/register/confirm':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=confirm_registration_handler
        )
    
    elif path == '/moderate/pending':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=moderation_queue_handler
        )
    
    elif path == '/moderate/approve':
        return dispatch_route(
            path, method, environ, start_response,
            post_handler=approve_registration_handler
        )
    
    elif path == '/moderate/deny':
        return dispatch_route(
            path, method, environ, start_response,
            post_handler=deny_registration_handler
        )
    
    elif path == '/createmailbox':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=create_mailbox_handler
        )
    
    elif path == '/logout':
        return dispatch_route(
            path, method, environ, start_response,
            get_handler=logout_handler
        )
    
    # Fallback on login
    start_response("302 Found", [("Location", "/login")])
    return [b"Redirecting to login (fallback)"]

# Middleware
app = SessionMiddleware(application)

