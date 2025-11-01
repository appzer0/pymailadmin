# handlers/html.py

from libs import config, translations

def html_template(title, content):
    css_path = config['css']['main_css']
    pretty_name = config['PRETTY_NAME']
    
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
        <h1>{title}</h1>
        {content}
    </body>
    </html>
    """
