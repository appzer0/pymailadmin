def logout_handler(environ, start_response):
    session = environ.get('session')
    if session:
        session.data.clear()
        session.save()
    start_response("302 Found", [("Location", "/login")])
    return [b""]
