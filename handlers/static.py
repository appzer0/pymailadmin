# handlers/static.py

import logging
from libs import translations

def static_handler(environ, start_response):
    requested_path = environ.get('PATH_INFO', '').lstrip('/')
    
    filename = os.path.basename(requested_path)
    
    if not filename.endswith('.css'):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    
    static_dir = os.path.abspath(config['paths']['static_dir'])
    secure_path = os.path.join(static_dir, filename)
    
    if not os.path.abspath(secure_path).startswith(static_dir):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [translations['forbidden_access'].encode('utf-8')]
    
    try:
        if os.path.isfile(secure_path):
            with open(secure_path, 'r') as f:
                content = f.read()
            start_response("200 OK", [("Content-Type", "text/css")])
            return [content.encode()]
    
        else:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [translations['not_found'].encode('utf-8')]
    
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [translations['internal_server_error'].encode('utf-8')]
