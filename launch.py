"""Public pages, revocable accounts and private watch history for the Flask app."""
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from flask import abort, g, jsonify, redirect, render_template, request, send_file, session
from PIL import Image, ImageOps, UnidentifiedImageError, __version__ as pillow_version
from werkzeug.security import check_password_hash, generate_password_hash

watch_time=time.time

PUBLIC = {
    '/': ('Watch together, feel closer', 'Watch supported videos together with shared playback, room chat, playful reactions and small multiplayer games.'),
    '/watch-together': ('Watch videos together online', 'Share play, pause and seek controls, chat and a video queue in a synchronized Solace watch party.'),
    '/watch-rooms': ('Public and private watch rooms', 'Choose a private invitation-only watch space or deliberately share a public room with Solace discovery.'),
    '/friends-messaging': ('Friends and private messaging', 'Connect with friend codes, accept requests and share messages, pictures and GIFs independently of watch rooms.'),
    '/open-world': ('Open World: a shared community chat', 'Meet people in Solace’s public community chat. Share messages, pictures and GIFs, preview profiles and connect by choice.'),
    '/play-together': ('Small games, shared moments', 'Chat and play Love Hoops, Little Ludo and Little Hearts & Stars with someone in your Solace room.'),
    '/community-guidelines': ('A welcoming space for everyone', 'Solace community expectations, reporting, blocking, moderation and appeals.'),
    '/features': ('A shared screen, a little more connection', 'Explore shared video controls, room chat, queues, reactions and games in Solace.'),
    '/how-it-works': ('From an invite to a shared moment', 'Create a Solace room, invite someone and choose a supported video to watch together.'),
    '/about': ('A quieter kind of together', 'Why Solace brings watching, conversation and little moments of play into one warm space.'),
    '/faq': ('A few things to know', 'Answers about supported videos, guests, accounts, synchronization and privacy in Solace.'),
    '/contact': ('Say hello', 'Contact the Solace operator for support, privacy requests or a playback issue.'),
    '/privacy': ('Your moments, your privacy', 'Understand Solace accounts, watch history, operational logs, retention and deletion controls.'),
    '/terms': ('Sharing this space', 'Practical terms for using Solace, supported content, account security and respectful use.'),
}


def register_launch(app, db):
    initialized = set()
    cleaned = {}
    lock = threading.RLock()

    def initialize():
        key = str(Path(app.instance_path).resolve())
        with lock:
            if key in initialized:
                return
            db().executescript('''
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS launch_migrations(version INTEGER PRIMARY KEY, applied REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,password TEXT NOT NULL,name TEXT NOT NULL,created REAL NOT NULL,avatar BLOB);
            CREATE TABLE IF NOT EXISTS account_sessions(token TEXT PRIMARY KEY,owner TEXT NOT NULL,expires REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS account_session_owner ON account_sessions(owner);
            CREATE TABLE IF NOT EXISTS account_limits(bucket TEXT PRIMARY KEY,count INTEGER NOT NULL,until REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS account_limit_expiry ON account_limits(until);
            CREATE INDEX IF NOT EXISTS account_session_expiry ON account_sessions(expires);
            CREATE TABLE IF NOT EXISTS launch_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS user_quotas(owner TEXT PRIMARY KEY,bytes INTEGER NOT NULL CHECK(bytes>=1048576));
            INSERT OR IGNORE INTO launch_settings VALUES('user_storage_bytes','52428800');
            CREATE TABLE IF NOT EXISTS watch_history(id INTEGER PRIMARY KEY,owner TEXT NOT NULL,room TEXT NOT NULL,playback TEXT NOT NULL,video TEXT NOT NULL,title TEXT NOT NULL,started REAL NOT NULL,last REAL NOT NULL,seconds REAL NOT NULL DEFAULT 0,beat REAL NOT NULL,active INTEGER NOT NULL DEFAULT 0,UNIQUE(owner,room,playback));
            CREATE INDEX IF NOT EXISTS watch_owner_date ON watch_history(owner,started);
            CREATE INDEX IF NOT EXISTS watch_last ON watch_history(last);
            CREATE TABLE IF NOT EXISTS watch_people(entry INTEGER NOT NULL,person TEXT NOT NULL,name TEXT NOT NULL,PRIMARY KEY(entry,person));
            CREATE TABLE IF NOT EXISTS watch_slices(entry INTEGER NOT NULL,ended REAL NOT NULL,seconds REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS watch_slice_entry ON watch_slices(entry,ended);
            CREATE TABLE IF NOT EXISTS history_suppress(owner TEXT NOT NULL,room TEXT NOT NULL,playback TEXT NOT NULL,PRIMARY KEY(owner,room,playback));
            CREATE TABLE IF NOT EXISTS account_tokens(token TEXT PRIMARY KEY,owner TEXT NOT NULL,purpose TEXT NOT NULL,expires REAL NOT NULL,created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS account_token_owner ON account_tokens(owner,purpose);
            CREATE INDEX IF NOT EXISTS account_token_expiry ON account_tokens(expires);
            INSERT OR IGNORE INTO launch_migrations VALUES(1,strftime('%s','now'));
            COMMIT;
            ''')
            db().execute('BEGIN IMMEDIATE')
            if 'verified' not in {row['name'] for row in db().execute('PRAGMA table_info(accounts)')}:
                db().execute('ALTER TABLE accounts ADD COLUMN verified INTEGER NOT NULL DEFAULT 0')
            db().execute('INSERT OR IGNORE INTO launch_migrations VALUES(2,?)',(time.time(),))
            db().execute('INSERT OR IGNORE INTO launch_migrations VALUES(3,?)',(time.time(),));db().commit()
            initialized.add(key)

    def setting(name, default=''):
        row = db().execute('SELECT value FROM launch_settings WHERE key=?', (name,)).fetchone()
        return row[0] if row else default

    def config(name, default=''):
        return app.config.get(name, os.environ.get(name, default))

    def public_url():
        value = str(config('SOLACE_PUBLIC_URL')).rstrip('/')
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            return ''
        return value

    def seo(path):
        name = str(config('SOLACE_SITE_NAME', 'Solace'))[:60]
        title, description = PUBLIC.get(path, ('Your space', 'Your private Solace space.'))
        base = public_url()
        return dict(name=name, title=title+' · '+name, description=description, url=base+path if base and path in PUBLIC and not request.query_string else '',
                    image=base+'/static/social-preview.png' if base else '', indexable=bool(base and path in PUBLIC and not request.query_string),
                    contact=str(config('SOLACE_CONTACT_EMAIL')),
                    schema={'@context':'https://schema.org','@type':'WebApplication' if path=='/' else 'WebPage','name':name if path=='/' else title,'url':base+path if base and path in PUBLIC else '',
                            'description':description,**({'applicationCategory':'EntertainmentApplication','operatingSystem':'Web browser'} if path=='/' else {})})

    def csrf():
        session.setdefault('account_csrf', secrets.token_urlsafe(32))
        return session['account_csrf']

    def csrf_valid():
        value = request.headers.get('X-CSRF-Token') or request.form.get('csrf', '')
        return bool(value and session.get('account_csrf')) and hmac.compare_digest(str(value), session['account_csrf'])

    def fail(message, status=400):
        return jsonify(error=message), status

    def limited(kind, maximum=12, duration=900):
        # Reuse the existing explicit trusted-proxy policy; never trust arbitrary forwarded headers.
        address=app.extensions['solace_ops']['client_ip']()
        bucket = hmac.new(str(app.secret_key).encode(),(kind if ':' in kind else kind+':'+address).encode(),hashlib.sha256).hexdigest()
        now = time.time()
        row = db().execute('''INSERT INTO account_limits VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET
            count=CASE WHEN until<? THEN 1 ELSE count+1 END,until=CASE WHEN until<? THEN excluded.until ELSE until END RETURNING count''',
            (bucket,now+duration,now,now)).fetchone()
        db().execute('DELETE FROM account_limits WHERE until<?',(now,));db().commit()
        return row[0] > maximum

    def require_account():
        if not g.account:
            abort(401)
        return g.account

    def revoke():
        token=request.cookies.get('solace_account','')
        db().execute('DELETE FROM account_sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))

    def leave_identity(owner):
        from app import delete_room_records,prune_participant_games
        rooms=db().execute('SELECT room FROM members WHERE id=?',(owner,)).fetchall()
        for item in rooms:
            room=item['room']
            for table in ('members','presence','typing','participant_ads'):
                db().execute(f'DELETE FROM {table} WHERE room=? AND id=?',(room,owner))
            prune_participant_games(room,owner)
            successor=db().execute('SELECT id FROM members WHERE room=? ORDER BY seen DESC LIMIT 1',(room,)).fetchone()
            if not successor:delete_room_records(room)
            else:db().execute('UPDATE rooms SET host=? WHERE id=? AND host=?',(successor['id'],room,owner))

    def issue(account,revoke_existing=True):
        if revoke_existing:revoke()
        if session['uid']!=account['id']:
            leave_identity(session['uid']);db().execute('DELETE FROM discovery_leases WHERE owner=?',(session['uid'],));db().execute('DELETE FROM world_presence WHERE owner=?',(session['uid'],))
        db().execute("DELETE FROM discovery_leases WHERE owner=? AND auth=''",(account['id'],));db().execute("DELETE FROM world_presence WHERE owner=? AND auth=''",(account['id'],))
        token=secrets.token_urlsafe(40)
        now=time.time()
        db().execute('DELETE FROM account_sessions WHERE expires<?',(now,))
        db().execute('INSERT INTO account_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),account['id'],now+30*86400))
        db().commit()
        session['uid']=account['id'];session['account_uid']=account['id'];session['account_csrf']=secrets.token_urlsafe(32);session.pop('identity_expired',None)
        
        if session.get('safety_identity')!=account['id']:session.pop('safety_identity',None)
        g.auth_event_name=account['name']
        response=jsonify(ok=True,next='/join?room='+session['pending_room']['room'] if session.get('pending_room') else '/home')
        response.set_cookie('solace_account',token,max_age=30*86400,httponly=True,secure=request.is_secure or app.config.get('SESSION_COOKIE_SECURE',False),samesite='Lax')
        return response

    @app.before_request
    def launch_identity():
        initialize()
        app.extensions['solace_social']['initialize']();app.extensions['solace_messaging']['initialize']();app.extensions['solace_people']['initialize']();app.extensions['solace_safety']['initialize']();app.extensions['solace_world']['initialize']();app.extensions['solace_companions']['initialize']()
        if request.path=='/api/me/media' and request.method=='POST':request.max_content_length=8*1024*1024+16384
        key=app.instance_path;now=time.time()
        if now-cleaned.get(key,0)>3600:
            # Unclaimed guest history has the same bounded retention as operations.
            old=db().execute('''SELECT watch_history.id FROM watch_history LEFT JOIN accounts ON accounts.id=watch_history.owner
                WHERE accounts.id IS NULL AND watch_history.last<? LIMIT 1000''',(now-30*86400,)).fetchall()
            for row in old:
                db().execute('DELETE FROM watch_people WHERE entry=?',(row['id'],));db().execute('DELETE FROM watch_slices WHERE entry=?',(row['id'],));db().execute('DELETE FROM watch_history WHERE id=?',(row['id'],))
            if old:db().commit()
            cleaned[key]=now
        g.account=None
        token=request.cookies.get('solace_account','')
        if token:
            g.account=db().execute('''SELECT accounts.id,accounts.email,accounts.password,accounts.name,accounts.created,accounts.verified,accounts.avatar IS NOT NULL AS avatar
                FROM account_sessions JOIN accounts ON accounts.id=account_sessions.owner
                WHERE account_sessions.token=? AND expires>?''',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        if g.account:
            session['uid']=g.account['id'];session['account_uid']=g.account['id']
        elif session.pop('account_uid',None) or db().execute('SELECT 1 FROM accounts WHERE id=?',(session['uid'],)).fetchone():
            # An expired/revoked account cookie must never retain the old guest authority.
            
            if app.extensions['solace_safety']['restricted'](session['uid']):session['safety_identity']=session['uid']
            session['uid']=secrets.token_urlsafe(24);session['identity_expired']=True;session['account_csrf']=secrets.token_urlsafe(32)
        if request.path=='/api/me/avatar' and request.method=='POST':
            request.max_content_length=2*1024*1024+16384
        protected=request.path.startswith('/api/me') or request.path.startswith('/api/auth/')
        if protected and request.method not in ('GET','HEAD','OPTIONS') and not csrf_valid():
            return fail('Your security token expired. Refresh the page and try again.',403)
        result=app.extensions['solace_safety']['gate']()
        if result is not None:return result
        # Retired personal assets must remain inaccessible on older installations.
        if request.path.startswith('/static/love') or request.path.startswith('/static/media/'):
            abort(404)
        if request.path.startswith('/api/rooms/') and request.method=='POST':
            data=request.get_json(silent=True) or {}
            if data.get('action')=='join' and limited('room-join',120,60):return fail('Too many room join attempts. Please wait a minute.',429)
        elif request.path=='/api/rooms' and request.method=='POST' and limited('room-create',30,900):
            return fail('Too many new rooms. Please try again later.',429)
        if request.path=='/api/videos' and request.args.get('q','').strip():
            if not db().execute('SELECT 1 FROM members WHERE id=? AND seen>? LIMIT 1',(session['uid'],now-30)).fetchone():return fail('Join a room before searching for videos.',403)
            if limited('video-search',30,60):return fail('Please wait a moment before searching again.',429)

    @app.after_request
    def launch_headers(response):
        public=request.path in PUBLIC and not request.query_string and not (request.path=='/' and response.status_code in (301,302,303,307,308))
        private=not public and request.path not in ('/robots.txt','/sitemap.xml')
        if private and not request.path.startswith('/static/'):
            response.headers.update({'Cache-Control':'no-store, private','X-Robots-Tag':'noindex, nofollow','Vary':'Cookie'})
        elif public:
            response.headers['Cache-Control']='no-cache'
            if not public_url():response.headers['X-Robots-Tag']='noindex, nofollow'
        if request.path.startswith('/static/love') or request.path.startswith('/static/media/'):
            response.headers['X-Robots-Tag']='noindex, nofollow';response.headers['Cache-Control']='no-store'
        response.headers.setdefault('X-Content-Type-Options','nosniff')
        response.headers.setdefault('Referrer-Policy','strict-origin-when-cross-origin')
        response.headers.setdefault('X-Frame-Options','SAMEORIGIN')
        if request.is_secure:response.headers.setdefault('Strict-Transport-Security','max-age=31536000')
        return response

    def launch_context():
        room=None
        if request.path not in PUBLIC:
            row=db().execute('SELECT room FROM members WHERE id=? ORDER BY seen DESC LIMIT 1',(session['uid'],)).fetchone()
            if row:room=row['room']
        return dict(app_space=request.path in ('/profile','/report','/world','/play','/safety','/home','/friends','/rooms','/settings','/messages','/games','/account','/history','/room-control','/room-media','/media-view'),nav_profile=app.extensions['solace_social']['person'](session['uid']),has_profile=bool(app.extensions['solace_social']['person'](session['uid'])),launch_seo=seo(request.path),account_csrf=csrf(),signed_in=bool(getattr(g,'account',None)),resume_room=room)
    app.context_processor(launch_context)

    def public_page():
        return render_template('public.html',page=request.path)
    for path in PUBLIC:
        if path!='/':app.add_url_rule(path,'public_'+path[1:],public_page)
    app.extensions['solace_public_home']=lambda:render_template('public.html',page='/')
    app.add_url_rule('/app','app_entry',lambda:redirect('/home',303))

    @app.get('/robots.txt')
    def robots():
        base=public_url()
        body='User-agent: *\nDisallow: /\n' if not base else 'User-agent: *\n'+''.join('Disallow: '+p+'\n' for p in ['/api/','/ops/','/messages','/settings','/friends','/rooms','/games','/room-media','/media-view','/home','/welcome','/invite','/room-control','/account','/history','/signin','/signup','/app','/create','/join','/love','/static/love','/*?'])+'Sitemap: '+base+'/sitemap.xml\n'
        return app.response_class(body,mimetype='text/plain')

    @app.get('/sitemap.xml')
    def sitemap():
        base=public_url()
        body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+(''.join('<url><loc>'+escape(base+p)+'</loc><lastmod>2026-11-19</lastmod></url>' for p in PUBLIC) if base else '')+'</urlset>'
        return app.response_class(body,mimetype='application/xml',status=200 if base else 503)

    @app.get('/signin')
    @app.get('/signup')
    @app.get('/account')
    @app.get('/history')
    def account_page():
        person=app.extensions['solace_social']['person'](session['uid'])
        if request.path in ('/account','/history') and not person:return redirect('/welcome',code=303)
        return render_template('account.html',page=request.path,person=person)

    @app.get('/api/me')
    def me():
        account=app.extensions['solace_social']['person'](session['uid'])
        return jsonify(guest=not bool(g.account),csrf=csrf(),storage=app.extensions['solace_user_storage']['snapshot'](session['uid']),email_delivery=app.extensions['solace_account_mail']['ready'](),profile=None if not account else dict(name=account['name'],email=account['email'],verified=bool(account['verified']),created=account['created'],avatar='/api/me/avatar' if account['avatar'] else '/static/default-avatar.svg'))

    @app.post('/api/auth/signup')
    @app.post('/api/auth/signin')
    def authenticate():
        if limited('auth',20):return fail('Too many attempts. Try again in 15 minutes.',429)
        if g.account:return fail('Sign out before switching accounts.',409)
        data=request.get_json(silent=True) or {}
        email=str(data.get('email','')).strip().casefold()
        password=data.get('password','')
        if not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',email) or len(email)>254:return fail('Enter a valid email address.')
        if not isinstance(password,str) or not 12<=len(password)<=128:return fail('Use a password between 12 and 128 characters.')
        row=db().execute('SELECT * FROM accounts WHERE email=?',(email,)).fetchone()
        if request.path.endswith('signup'):
            if limited('signup',5,3600):return fail('Account creation is temporarily limited. Try later.',429)
            if data.get('accept_terms') not in (True,'on'):return fail('Please read and accept the Terms and Privacy Policy before creating an account.')
            name=str(data.get('name','')).strip()
            if not 1<=len(name)<=24 or any(ord(c)<32 for c in name):return fail('Choose a display name of 1–24 characters.')
            if row:return fail('An account could not be created with these details. Try signing in.',409)
            try:
                db().execute('INSERT INTO accounts(id,email,password,name,created,avatar) VALUES(?,?,?,?,?,(SELECT avatar FROM guest_data WHERE owner=?))',(session['uid'],email,generate_password_hash(password,method='scrypt'),name,time.time(),session['uid']))
                db().execute('DELETE FROM guest_data WHERE owner=?',(session['uid'],))
                db().execute('INSERT INTO profiles VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated=excluded.updated',(session['uid'],name,time.time()))
                db().execute('UPDATE members SET name=? WHERE id=?',(name,session['uid']))
                db().commit()
            except sqlite3.IntegrityError:
                db().rollback();return fail('An account could not be created with these details.',409)
            row=db().execute('SELECT * FROM accounts WHERE id=?',(session['uid'],)).fetchone()
            mail=app.extensions['solace_account_mail']
            if mail['ready']():mail['send'](row['id'],row['email'],'verify')
        else:
            # The dummy hash work keeps unknown-email failures from being a cheap path.
            digest=row['password'] if row else app.extensions['solace_dummy_password']
            if not check_password_hash(digest,password) or not row:return fail('Email or password not accepted.',401)
        return issue(row)

    @app.post('/api/auth/signout')
    def signout():
        require_account();g.auth_event_name=g.account['name'];revoke();leave_identity(session['uid']);db().commit()
        session.pop('account_uid',None);session['uid']=secrets.token_urlsafe(24);session['account_csrf']=secrets.token_urlsafe(32)
        response=jsonify(ok=True);response.delete_cookie('solace_account',httponly=True,samesite='Lax');return response

    @app.post('/api/me/profile')
    def account_profile():
        account={'id':session['uid']}
        if limited('profile',30):return fail('Please wait before updating again.',429)
        name=str((request.get_json(silent=True) or {}).get('name','')).strip()
        if not 1<=len(name)<=24 or any(ord(c)<32 for c in name):return fail('Choose a display name of 1–24 characters.')
        db().execute('UPDATE accounts SET name=? WHERE id=?',(name,account['id']))
        db().execute('INSERT INTO profiles VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated=excluded.updated',(account['id'],name,time.time()))
        db().execute('UPDATE members SET name=? WHERE id=?',(name,account['id']))
        if not g.account:db().execute('INSERT OR IGNORE INTO guest_data(owner,created) VALUES(?,?)',(account['id'],time.time()))
        db().commit()
        session.pop('identity_expired',None)
        return jsonify(ok=True,next='/join?room='+session['pending_room']['room'] if session.get('pending_room') else '/home')

    @app.route('/api/me/avatar',methods=['GET','POST','DELETE'])
    def avatar():
        account=app.extensions['solace_social']['named']();table='guest_data' if account['guest'] else 'accounts';column='owner' if account['guest'] else 'id'
        if request.method=='GET':
            if not account['avatar']:return redirect('/static/default-avatar.svg')
            picture=db().execute('SELECT avatar FROM '+table+' WHERE '+column+'=?',(account['id'],)).fetchone()[0]
            return send_file(io.BytesIO(picture),mimetype='image/png',max_age=0)
        if limited('avatar',15):return fail('Please wait before changing your picture again.',429)
        if request.method=='DELETE':
            db().execute('UPDATE '+table+' SET avatar=NULL WHERE '+column+'=?',(account['id'],));db().execute('UPDATE profiles SET updated=? WHERE id=?',(time.time(),account['id']));db().commit();return jsonify(ok=True)
        if tuple(int(part) for part in pillow_version.split('.')[:2])<(13,0):return fail('Picture uploads require the server security update. Contact the operator.',503)
        upload=request.files.get('picture')
        if not upload:return fail('Choose a JPEG, PNG or WebP image up to 2 MiB.')
        raw=upload.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:return fail('The picture must be no larger than 2 MiB.',413)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw),formats=['JPEG','PNG','WEBP']) as image:
                    if image.width*image.height>16_000_000 or getattr(image,'n_frames',1)!=1:raise ValueError()
                    image.load();picture=ImageOps.fit(ImageOps.exif_transpose(image).convert('RGB'),(256,256));picture.info.clear();out=io.BytesIO();picture.save(out,'PNG')
        except (UnidentifiedImageError,OSError,ValueError,SyntaxError,EOFError,Image.DecompressionBombError,Image.DecompressionBombWarning):
            return fail('Use a valid, still JPEG, PNG or WebP picture under 16 megapixels.')
        quota=app.extensions['solace_user_storage'];db().execute('BEGIN IMMEDIATE')
        if account['guest']:db().execute('INSERT OR IGNORE INTO guest_data(owner,created) VALUES(?,?)',(account['id'],time.time()))
        old=db().execute('SELECT COALESCE(length(avatar),0) FROM '+table+' WHERE '+column+'=?',(account['id'],)).fetchone()[0]
        if quota['usage'](account['id'])-old+len(out.getvalue())>quota['limit'](account['id']):db().rollback();return fail('Your storage limit is reached. Remove a picture or delete some history.',413)
        db().execute('UPDATE '+table+' SET avatar=? WHERE '+column+'=?',(out.getvalue(),account['id']));db().execute('UPDATE profiles SET updated=? WHERE id=?',(time.time(),account['id']));db().commit();return jsonify(ok=True)

    def delete_history(owner,entry=None):
        if not db().in_transaction:db().execute('BEGIN IMMEDIATE')
        clause='owner=?'+(' AND id=?' if entry is not None else '');params=(owner,entry) if entry is not None else (owner,)
        db().execute('INSERT OR IGNORE INTO history_suppress SELECT owner,room,playback FROM watch_history WHERE '+clause,params)
        for table in ('watch_people','watch_slices'):
            db().execute('DELETE FROM '+table+' WHERE entry IN (SELECT id FROM watch_history WHERE '+clause+')',params)
        return db().execute('DELETE FROM watch_history WHERE '+clause,params).rowcount

    @app.post('/api/me/watch')
    def watch():
        if limited('watch:'+session['uid'],90,60):return fail('Please wait a moment.',429)
        data=request.get_json(silent=True) or {};room_id=data.get('room');now=watch_time()
        room=db().execute('SELECT rooms.* FROM rooms JOIN members ON members.room=rooms.id WHERE rooms.id=? AND members.id=? AND members.seen>?',(room_id,session['uid'],now-30)).fetchone()
        if not room:return fail('Join this room before recording playback.',403)
        owner=session['uid'];playback=room['playback_id']
        active=bool(data.get('active') is True and room['playing'])
        source=room['video'];parts=urlsplit(source)
        if parts.scheme:source=parts.scheme+'://'+parts.netloc+parts.path
        title=str(data.get('title','')).strip()[:160] or ('Direct video' if parts.scheme else 'YouTube video')
        # Only a decoded, visible playing sample begins a history entry.
        db().execute('BEGIN IMMEDIATE')
        if db().execute('SELECT 1 FROM history_suppress WHERE owner=? AND room=? AND playback=?',(owner,room_id,playback)).fetchone():
            db().rollback();return jsonify(ok=True,suppressed=True)
        quota=app.extensions['solace_user_storage']
        if quota['usage'](owner)+512>quota['limit'](owner):
            db().execute('UPDATE watch_history SET active=0,beat=? WHERE owner=? AND room=? AND playback=?',(now,owner,room_id,playback));db().commit()
            return jsonify(ok=True,history_paused=True,reason='storage_limit'),202
        row=db().execute('SELECT * FROM watch_history WHERE owner=? AND room=? AND playback=?',(owner,room_id,playback)).fetchone()
        if row:
            gap=now-row['beat'];seconds=gap if active and row['active'] and 0<gap<=25 else 0
            db().execute('UPDATE watch_history SET last=?,seconds=seconds+?,beat=?,active=? WHERE id=?',(now,seconds,now,int(active),row['id']))
            entry=row['id']
            if seconds:db().execute('INSERT INTO watch_slices VALUES(?,?,?)',(entry,now,seconds))
        elif active:
            entry=db().execute('INSERT INTO watch_history(owner,room,playback,video,title,started,last,beat,active) VALUES(?,?,?,?,?,?,?,?,1)',(owner,room_id,playback,source,title,now,now,now)).lastrowid
        else:
            db().rollback();return jsonify(ok=True)
        for member in db().execute('SELECT id,name FROM members WHERE room=? AND seen>? AND id<>?',(room_id,now-30,owner)).fetchall():
            db().execute('INSERT INTO watch_people VALUES(?,?,?) ON CONFLICT(entry,person) DO UPDATE SET name=excluded.name',(entry,member['id'],member['name']))
        if quota['usage'](owner)>quota['limit'](owner):
            db().rollback();db().execute('UPDATE watch_history SET active=0,beat=? WHERE owner=? AND room=? AND playback=?',(now,owner,room_id,playback));db().commit()
            return jsonify(ok=True,history_paused=True,reason='storage_limit'),202
        db().commit();return jsonify(ok=True)

    def history_filter():
        try:
            zone=ZoneInfo(request.args.get('timezone','UTC'))
            end=datetime.strptime(request.args.get('end',datetime.now(zone).date().isoformat()),'%Y-%m-%d').replace(tzinfo=zone)+timedelta(days=1)
            start=datetime.strptime(request.args.get('start',(end-timedelta(days=30)).date().isoformat()),'%Y-%m-%d').replace(tzinfo=zone)
            if not 0<(end-start).days<=366:raise ValueError()
        except (ValueError,ZoneInfoNotFoundError):abort(400,description='Choose a valid timezone and a date range up to 366 days.')
        return zone,start,end

    @app.route('/api/me/history',methods=['GET','DELETE'])
    @app.delete('/api/me/history/<int:entry>')
    def history(entry=None):
        owner=app.extensions['solace_social']['named']()['id']
        if request.method=='DELETE':
            count=delete_history(owner,entry);db().commit()
            return jsonify(ok=True,deleted=count),200 if entry is None or count else 404
        zone,start,end=history_filter()
        rows=db().execute('SELECT * FROM watch_history WHERE owner=? AND started<? AND last>=? ORDER BY started DESC LIMIT 500',(owner,end.timestamp(),start.timestamp())).fetchall()
        days={};day=start
        while day<end:days[day.date().isoformat()]={'date':day.date().isoformat(),'sessions':0,'seconds':0};day+=timedelta(days=1)
        result=[]
        for record in db().execute('SELECT started FROM watch_history WHERE owner=? AND started>=? AND started<?',(owner,start.timestamp(),end.timestamp())):
            key=datetime.fromtimestamp(record['started'],zone).date().isoformat()
            days[key]['sessions']+=1
        for chunk in db().execute('''SELECT ended,watch_slices.seconds FROM watch_slices JOIN watch_history ON watch_history.id=watch_slices.entry
            WHERE watch_history.owner=? AND ended>? AND ended-watch_slices.seconds<?''',(owner,start.timestamp(),end.timestamp())):
            left=max(chunk['ended']-chunk['seconds'],start.timestamp());right=min(chunk['ended'],end.timestamp())
            while left<right:
                date=datetime.fromtimestamp(left,zone);boundary=datetime.combine(date.date()+timedelta(days=1),datetime.min.time(),tzinfo=zone).timestamp();stop=min(right,boundary)
                days[date.date().isoformat()]['seconds']+=stop-left;left=stop
        for row in rows:
            result.append(dict(id=row['id'],video=row['video'],title=row['title'],started=row['started'],last=row['last'],seconds=round(row['seconds'],1),people=[r['name'] for r in db().execute('SELECT name FROM watch_people WHERE entry=?',(row['id'],))]))
        return jsonify(entries=result,days=list(days.values()),timezone=str(zone),limit=500,truncated=len(rows)==500,measurement='Visible decoded playback, sampled every 15 seconds; only consecutive active samples at most 25 seconds apart count. Sessions group by room and playback instance. Daily session count uses start date; duration splits at local midnight.')

    @app.post('/api/me/delete-account')
    def delete_account():
        account=require_account();data=request.get_json(silent=True) or {}
        if limited('delete-account',10):return fail('Try again later.',429)
        password=data.get('password','')
        if not isinstance(password,str) or len(password)>128 or not check_password_hash(account['password'],password):return fail('Enter your current password.',403)
        owner=account['id'];delete_history(owner)
        db().execute("UPDATE watch_people SET name='Former participant' WHERE person=?",(owner,))
        db().execute('DELETE FROM history_suppress WHERE owner=?',(owner,))
        db().execute('DELETE FROM profiles WHERE id=?',(owner,));db().execute('DELETE FROM account_sessions WHERE owner=?',(owner,));db().execute('DELETE FROM accounts WHERE id=?',(owner,))
        db().execute('DELETE FROM account_tokens WHERE owner=?',(owner,))
        db().execute('DELETE FROM user_quotas WHERE owner=?',(owner,))
        app.extensions['solace_social']['erase'](owner);leave_identity(owner);db().commit()
        session.pop('account_uid',None);session['uid']=secrets.token_urlsafe(24);session['account_csrf']=secrets.token_urlsafe(32)
        response=jsonify(ok=True);response.delete_cookie('solace_account');return response

    app.extensions['solace_launch']={'initialize':initialize,'setting':setting,'public_url':public_url,'issue':issue,'leave_identity':leave_identity}
    from account_mail import register_account_mail
    app.extensions['solace_account_mail']=register_account_mail(app,db,config,public_url,limited,require_account)
    from user_storage import register_user_storage
    register_user_storage(app,db)
    app.extensions['solace_dummy_password']=generate_password_hash(secrets.token_urlsafe(32),method='scrypt')
    from social import register_social
    register_social(app,db,limited,csrf_valid)
    from messaging import register_messaging
    register_messaging(app,db,limited,csrf_valid)
    from people import register_people
    register_people(app,db,limited)
    from platform_safety import register_safety
    register_safety(app,db,limited)
    from community import register_world
    register_world(app,db,limited)
    from companions import register_companions
    register_companions(app,db,limited)
    with app.app_context():
        initialize();app.extensions['solace_social']['initialize']();app.extensions['solace_messaging']['initialize']();app.extensions['solace_people']['initialize']();app.extensions['solace_safety']['initialize']();app.extensions['solace_world']['initialize']();app.extensions['solace_companions']['initialize']()
