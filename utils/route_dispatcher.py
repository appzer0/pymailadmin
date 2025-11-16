# utils/route_dispatcher.py

import urllib.parse

def dispatch_route(path, method, environ, start_response, get_handler=None, post_handler=None, post_action_mapping=None):
    """
    Dispatch GET/POST contexts towards handlers
    """
    # Check if POST method is used
    if method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            
            if content_length == 0:
                start_response("400 Bad Request", [("Content-Type", "text/html")])
                return [b"Bad request"]
            
            post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
            data = urllib.parse.parse_qs(post_data)
            environ['_post_data'] = data
        
        except Exception:
            start_response("400 Bad Request", [("Content-Type", "text/html")])
            return [b"Bad request"]

        # Check if POST contains mapped-actions from forms
        if post_action_mapping and 'action' in data:
            action = data['action'][0]
            handler = post_action_mapping.get(action)
            
            if handler:
                return handler(environ, start_response)

        # Simple POST
        if post_handler:
            return post_handler(environ, start_response)

    # No POST
    if get_handler:
        environ['_post_data'] = {}
        return get_handler(environ, start_response)
    
    # No handler? Redirect to home
    else:
        start_response("302 Found", [("Location", "/home")])
        return [b"Redirecting to home (fallback)"]
