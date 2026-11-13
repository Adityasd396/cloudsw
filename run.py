"""Run Solace with a production WSGI server on the local computer."""
import os
from waitress import serve
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    print(f'Solace is ready at http://127.0.0.1:{port}', flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    serve(app, host='127.0.0.1', port=port, threads=8, channel_timeout=30)
