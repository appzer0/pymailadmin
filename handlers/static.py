# handlers/static.py

import logging

def static_handler(environ, start_response):
    """Gère les fichiers statiques de manière sécurisée."""
    requested_path = environ.get('PATH_INFO', '').lstrip('/')
    
    # Garder uniquement le nom du fichier et forcer le répertoire
    filename = os.path.basename(requested_path)
    # Vérifier l'extension pour autoriser uniquement certains types
    if not filename.endswith('.css'):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Accès interdit"]
    
    # Construire le chemin sécurisé
    static_dir = os.path.abspath(config['paths']['static_dir'])
    secure_path = os.path.join(static_dir, filename)
    
    # Vérifier que le chemin est bien dans le répertoire autorisé
    if not os.path.abspath(secure_path).startswith(static_dir):
        start_response("403 Forbidden", [("Content-Type", "text/html")])
        return [b"Accès interdit"]
    
    try:
        if os.path.isfile(secure_path):
            with open(secure_path, 'r') as f:
                content = f.read()
            start_response("200 OK", [("Content-Type", "text/css")])
            return [content.encode()]
        else:
            start_response("404 Not Found", [("Content-Type", "text/html")])
            return [b"Not Found"]
    except Exception as e:
        logging.error(f"Erreur de lecture du fichier: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/html")])
        return [b"Erreur interne du serveur"]
