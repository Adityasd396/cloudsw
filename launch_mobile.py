"""Start a LAN room server and the Expo phone-client QR code."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parent

def main():
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm:
        raise SystemExit('Install Node.js, then run this launcher again.')
    if not (ROOT/'mobile'/'node_modules'/'expo').exists():
        print('Installing phone app dependencies...', flush=True)
        subprocess.run([npm,'ci','--no-audit','--no-fund'],cwd=ROOT/'mobile',check=True)
    addresses = [address for address in socket.gethostbyname_ex(socket.gethostname())[2] if not address.startswith(('127.','169.254.'))]
    ip = os.environ.get('AFTERGLOW_LAN_IP') or (addresses[0] if addresses else '')
    if not ip:
        raise SystemExit('Connect this computer to Wi-Fi first, then run the launcher again.')
    port = int(os.environ.get('AFTERGLOW_MOBILE_PORT','8001'))
    opener = build_opener(ProxyHandler({}))
    def server_ready():
        try:
            with opener.open(f'http://127.0.0.1:{port}/api/health',timeout=2) as response:
                return json.load(response).get('application')=='afterglow'
        except Exception:
            return False
    process = None
    log = None
    try:
        if not server_ready():
            (ROOT/'instance').mkdir(exist_ok=True)
            log = (ROOT/'instance'/'mobile-server.log').open('a')
            process = subprocess.Popen([sys.executable,str(ROOT/'run_mobile_server.py')],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for _ in range(20):
                if server_ready(): break
                if process.poll() is not None: raise RuntimeError('The phone server could not start. See instance/mobile-server.log.')
                time.sleep(.25)
            else: raise RuntimeError('The phone server did not become ready.')
        env = os.environ.copy()
        env['EXPO_PUBLIC_API_URL'] = f'http://{ip}:{port}'
        print(f'\nPhone room server: {env["EXPO_PUBLIC_API_URL"]}\n',flush=True)
        print('Install Expo Go on both phones and connect them to the same Wi-Fi.',flush=True)
        print('Scan the Expo QR code below. Keep this window open.\n',flush=True)
        subprocess.run([npm,'start'],cwd=ROOT/'mobile',env=env,check=True)
    except KeyboardInterrupt:
        pass
    finally:
        if process:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill()
        if log: log.close()

if __name__=='__main__':
    main()
