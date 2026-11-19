"""Loopback-only audit server with disposable storage and synthetic media."""
import argparse,os,sys,tempfile,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser();parser.add_argument('--staff-fixture',action='store_true');parser.add_argument('--port',type=int,default=8027);parser.add_argument('--source',default=str(ROOT));args=parser.parse_args()
source=Path(args.source).resolve()
if source not in (ROOT,ROOT/'release'):raise ValueError('Only the workspace or its release snapshot may be audited')
sys.path.insert(0,str(source))
with tempfile.TemporaryDirectory(prefix='solace-stream-audit-') as instance:
    os.environ['SECRET_KEY']='disposable-stream-audit-fixture-not-a-user-secret'
    os.environ['SOLACE_ENV']='development'
    import flask
    original=flask.Flask.__init__
    def isolated(self,*a,**kw):
        kw['instance_path']=instance;original(self,*a,**kw)
    flask.Flask.__init__=isolated
    from app import app
    if args.staff_fixture:
        import base64
        with app.app_context():
            for browser in ['chromium','webkit']:app.extensions['solace_staff']['create']('auditor-'+browser,'Synthetic-Staff-Password-2026!','administrator',base64.b32encode(b'12345678901234567890').decode())
    flask.Flask.__init__=original
    from flask import jsonify,send_from_directory,Response,request
    from waitress import serve
    media=ROOT/'.openai/stream-audit/media'
    @app.get('/__audit__/info')
    def info():
        modules=[name for name in ['app.py','community.py','messaging.py','people.py','platform_safety.py','staff_auth.py','room_game.py','ludo_game.py','game_options.py','launch.py','account_mail.py','user_storage.py','production.py','admin_panel.py'] if (source/name).is_file()]
        return jsonify(disposable=True,pid=os.getpid(),media_bytes=(media/'clip.mp4').stat().st_size,fingerprint_modules=modules,source_fingerprint=hashlib.sha256(b''.join((source/name).read_bytes() for name in modules)).hexdigest())
    @app.get('/__audit__/media/<path:name>')
    def audit_media(name):return send_from_directory(media,name,conditional=True)
    @app.get('/__audit__/slow.mp4')
    def slow():
        def chunks():
            with (media/'clip.mp4').open('rb') as stream:
                while part:=stream.read(8192):
                    yield part;time.sleep(.08)
        return Response(chunks(),mimetype='video/mp4')
    @app.get('/__audit__/bad.mp4')
    def malformed():return Response(b'not a media container',mimetype='video/mp4')
    @app.get('/__audit__/protected.mp4')
    def protected():
        if request.headers.get('Authorization')!='Bearer disposable-test':return Response(status=401)
        return send_from_directory(media,'clip.mp4',conditional=True)
    @app.get('/__audit__/expired.mp4')
    def expired():return Response(status=403)
    app.config.update(SESSION_COOKIE_SECURE=False,SOLACE_SMTP_HOST='')
    print('DISPOSABLE AUDIT READY',flush=True)
    serve(app,host='127.0.0.1',port=args.port,threads=8,channel_timeout=30)
