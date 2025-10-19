# handlers/html.py

from libs import config

def html_template(title, content):
    css_path = config['css']['main_css']
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="stylesheet" href="/static/{css_path}">
    </head>
    <body>
        <h1>{title}</h1>
        {content}
    </body>
    </html>
    """
