"""Launch configuration checks, safe request diagnostics and readiness."""
import json
import logging
import os
import re
import secrets
import shutil
import time
from urllib.parse import urlsplit
from flask import g,jsonify,request,redirect


def configuration_errors(app):
    def value(key,default=''):return str(app.config.get(key,os.environ.get(key,default)))
    mode=value('SOLACE_ENV','development')
    if mode not in ('development','production','test'):return ['SOLACE_ENV must be development, production or test']
    if mode!='production':return []
    errors=[];url=urlsplit(value('SOLACE_PUBLIC_URL'))
    if url.scheme!='https' or not url.hostname or url.path or url.query or url.fragment or url.username:errors.append('SOLACE_PUBLIC_URL must be an HTTPS origin')
    if len(str(app.secret_key or ''))<32 or str(app.secret_key).startswith('replace-'):errors.append('A persistent SECRET_KEY of at least 32 characters is required')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value('SOLACE_CONTACT_EMAIL')):errors.append('SOLACE_CONTACT_EMAIL must be configured')
    if app.debug:errors.append('Debug mode must be disabled')
    if not app.config.get('SESSION_COOKIE_SECURE'):errors.append('Secure cookies must be enabled for production')
    from PIL import __version__ as image_version
    if tuple(int(part) for part in image_version.split('.')[:2])<(13,0):errors.append('Install the pinned Pillow security update')
    if value('SOLACE_REQUIRE_EMAIL','1')=='1' and not app.extensions['solace_account_mail']['ready']():errors.append('Configure SMTP and mail sender, or explicitly set SOLACE_REQUIRE_EMAIL=0 for a limited launch')
    if value('SOLACE_SMTP_HOST'):
        try:port=int(value('SOLACE_SMTP_PORT','587'));assert 1<=port<=65535
        except (ValueError,AssertionError):errors.append('SOLACE_SMTP_PORT must be valid')
        if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+',value('SOLACE_MAIL_FROM')):errors.append('SOLACE_MAIL_FROM must be a sender email')
        if value('SOLACE_SMTP_USERNAME') and not value('SOLACE_SMTP_PASSWORD'):errors.append('SOLACE_SMTP_PASSWORD is required with username')
    return errors


def register_production(app,db):
    if os.environ.get('SOLACE_LOG_REQUESTS')=='1':app.logger.setLevel(logging.INFO)
    app.extensions['solace_draining']=False
    def request_start():
        supplied=request.headers.get('X-Request-ID','')
        g.request_id=supplied if re.fullmatch(r'[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}',supplied) else secrets.token_hex(16)
        g.csp_nonce=secrets.token_urlsafe(24)
        g.request_started=time.perf_counter()
        if os.environ.get('SOLACE_ENV')=='production' and not request.is_secure and request.path not in ('/api/health','/api/ready'):
            origin=app.extensions['solace_launch']['public_url']()
            if request.method in ('GET','HEAD') and origin:return redirect(origin+request.full_path.rstrip('?'),code=308)
            return jsonify(error='Use the configured HTTPS site.',code='https_required'),426
        if app.extensions['solace_draining'] and request.path!='/api/health':
            response=jsonify(error='The server is restarting. Please retry.',code='server_draining');response.status_code=503;response.headers['Retry-After']='2';return response
    app.before_request_funcs.setdefault(None,[]).insert(0,request_start)

    @app.after_request
    def request_finish(response):
        response.headers['X-Request-ID']=getattr(g,'request_id',secrets.token_hex(16))
        if (request.path.startswith('/ops/') or request.path in ('/profile','/report','/world','/safety','/watch-together','/watch-rooms','/friends-messaging','/open-world','/play-together','/community-guidelines','/','/features','/how-it-works','/about','/faq','/contact','/privacy','/terms','/signin','/signup','/account','/history','/room-media','/media-view','/messages','/settings','/friends','/rooms','/games','/home','/welcome','/invite','/room-control','/reset-password','/verify-email')) and not (request.path=='/' and request.args.get('room')):
            response.headers.setdefault('Content-Security-Policy',"default-src 'self'; script-src 'self' 'nonce-"+getattr(g,'csp_nonce','')+"'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")
        if os.environ.get('SOLACE_LOG_REQUESTS')=='1' or response.status_code>=500:
            level=logging.ERROR if response.status_code>=500 else logging.INFO
            app.logger.log(level,json.dumps({'event':'http_request','request_id':response.headers['X-Request-ID'],'endpoint':request.endpoint or 'unknown','method':request.method,'status':response.status_code,'handler_ms':round((time.perf_counter()-getattr(g,'request_started',time.perf_counter()))*1000,2)},separators=(',',':')))
        return response

    @app.get('/api/ready')
    def readiness():
        healthy=True
        try:healthy=db().execute('SELECT MAX(version) FROM launch_migrations').fetchone()[0]>=8
        except Exception:healthy=False
        configured=not configuration_errors(app)
        try:space=shutil.disk_usage(app.instance_path).free>=256*1024*1024
        except OSError:space=False
        ready=bool(healthy and configured and space and not app.extensions['solace_draining'])
        return jsonify(status='ready' if ready else 'not_ready',checks={'database':healthy,'configuration':configured,'disk_headroom':space}),200 if ready else 503

    if os.environ.get('SOLACE_ENV')=='production':
        app.config['SESSION_COOKIE_SECURE']=True
        host=urlsplit(os.environ.get('SOLACE_PUBLIC_URL','')).hostname
        if host:app.config['TRUSTED_HOSTS']=[host]
    app.context_processor(lambda:{'csp_nonce':getattr(g,'csp_nonce','')})
