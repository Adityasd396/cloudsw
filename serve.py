"""Cloud entrypoint. Put an HTTPS reverse proxy in front of this server."""
import os
import signal
os.environ.setdefault('SOLACE_ENV','production')
from waitress import create_server
from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

app.config['SESSION_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', '1') == '1'
if os.environ.get('TRUST_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == '__main__':
    from production import configuration_errors
    errors=configuration_errors(app)
    if errors:raise SystemExit('Launch configuration: '+'; '.join(errors))
    server=create_server(app,host=os.environ.get('HOST','0.0.0.0'),port=int(os.environ.get('PORT','8080')),threads=8,channel_timeout=30,
        connection_limit=100,backlog=128,max_request_header_size=16384,max_request_body_size=8404992,outbuf_high_watermark=1048576,expose_tracebacks=False,log_socket_errors=False)
    def stopping(signum,frame):
        app.extensions['solace_draining']=True
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stopping)
    if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,stopping)
    try:server.run()
    finally:
        app.extensions['solace_draining']=True
        server.task_dispatcher.shutdown(timeout=10);server.close()
