"""Real loopback HTTPS/Range fixture for engines with native media networking."""
import ipaddress,re,ssl,tempfile,threading
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

class MediaFixture:
    def __init__(self,body):self.body=body
    def __enter__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='solace-https-fixture-');folder=Path(self.temp.name)
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Solace local test')]);now=datetime.now(timezone.utc)
        cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256())
        (folder/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));(folder/'key.pem').chmod(0o600);(folder/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        body=self.body
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path!='/clip.mp4':self.send_error(404);return
                start=0;end=len(body)-1;status=200;value=self.headers.get('Range','')
                if value:
                    match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
                    if not match:self.send_error(416);return
                    a,b=match.groups();start=int(a) if a else max(0,len(body)-int(b));end=min(int(b),len(body)-1) if b and a else len(body)-1;status=206
                    if start>end:self.send_error(416);return
                self.send_response(status);self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1));self.send_header('Access-Control-Allow-Origin','*')
                if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{len(body)}')
                self.end_headers()
                try:self.wfile.write(body[start:end+1])
                except (ConnectionError,OSError):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True;context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(folder/'cert.pem',folder/'key.pem');self.server.socket=context.wrap_socket(self.server.socket,server_side=True);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='https://127.0.0.1:'+str(self.server.server_port)+'/clip.mp4';return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join(5);self.temp.cleanup()
