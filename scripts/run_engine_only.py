from flask import request

from app import create_app
from app.portal import engine_site_response


app = create_app()


@app.before_request
def restrict_to_engine_dcarb():
    path = request.path
    if path == '/':
        return engine_site_response()
    if path == '/engine-d-carb':
        return None
    if path in {'/api/engine-d-carb/centres', '/api/engine-d-carb/quotations'}:
        return None
    if path.startswith('/static/engine-') or path == '/static/images/batterywala-logo-original.png':
        return None
    return 'Not found', 404


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001, debug=False)
