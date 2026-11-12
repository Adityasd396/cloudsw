"""Cloud entrypoint. Put an HTTPS reverse proxy in front of this server."""
import os
from waitress import serve
from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

app.config['SESSION_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', '1') == '1'
if os.environ.get('TRUST_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT','8080')), threads=8, channel_timeout=30)
