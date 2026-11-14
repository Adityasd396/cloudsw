"""LAN server used by the phone clients; the desktop app keeps port 8000."""
import os
from waitress import serve
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('AFTERGLOW_MOBILE_PORT', '8001'))
    print(f'Afterglow phone room server listening on port {port}', flush=True)
    serve(app, host='0.0.0.0', port=port, threads=8, channel_timeout=30)
