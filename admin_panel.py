"""Private operations panel. Telemetry is isolated from room transactions."""
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import closing, contextmanager
from pathlib import Path
from flask import Response, abort, g, jsonify, redirect, render_template, request, session, stream_with_context
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException

RETENTION_DAYS=30
BASE='/ops/solace'


def register_admin(app):
    ready=set();touches={};metrics={};lock=threading.RLock()
    started=time.monotonic();cpu_started=time.process_time();last_purge={}

    def credential():
        configured=app.config.get('OPS_PASSWORD_HASH') or os.environ.get('SOLACE_ADMIN_PASSWORD_HASH')
        if configured:return configured
        try:return (Path(app.instance_path)/'admin-password.hash').read_text().strip()
        except FileNotFoundError:return None

    def visitor():
        return hmac.new(str(app.secret_key).encode(),session.get('uid','').encode(),hashlib.sha256).hexdigest()[:24]

    def client_ip():
        # PythonAnywhere guarantees this header; enable only behind that trusted proxy.
        trusted=app.config.get('OPS_TRUST_X_REAL_IP') or os.environ.get('SOLACE_TRUST_X_REAL_IP')=='1'
        address=(request.headers.get('X-Real-IP') if trusted else None) or request.remote_addr or ''
        try:return str(ipaddress.ip_address(address))
        except ValueError:return 'unknown'

    @contextmanager
    def storage(timeout=.15):
        path=Path(app.instance_path)/'solace-admin.db'
        connection=sqlite3.connect(path,timeout=timeout)
        connection.row_factory=sqlite3.Row
        try:
            with lock:
                if str(path) not in ready:
                    connection.executescript('''
                    PRAGMA journal_mode=WAL;
                    CREATE TABLE IF NOT EXISTS visitors(id TEXT PRIMARY KEY,name TEXT,ip TEXT,agent TEXT,first REAL,last REAL,last_join REAL,last_leave REAL,active INTEGER NOT NULL DEFAULT 1);
                    CREATE TABLE IF NOT EXISTS visitor_ips(visitor TEXT,ip TEXT,first REAL,last REAL,PRIMARY KEY(visitor,ip));
                    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,visitor TEXT,name TEXT,ip TEXT,event TEXT,room TEXT,created REAL);
                    CREATE INDEX IF NOT EXISTS event_time ON events(created);
                    CREATE TABLE IF NOT EXISTS chat_archive(room TEXT,message_id INTEGER,visitor TEXT,name TEXT,body TEXT,reply TEXT,created REAL,PRIMARY KEY(room,message_id));
                    CREATE TABLE IF NOT EXISTS requests(minute INTEGER PRIMARY KEY,total INTEGER,errors INTEGER,elapsed REAL);
                    CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT PRIMARY KEY,attempts INTEGER,until REAL);
                    ''')
                    if 'active' not in {column['name'] for column in connection.execute('PRAGMA table_info(visitors)')}:connection.execute('ALTER TABLE visitors ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
                    try:path.chmod(0o600)
                    except OSError:pass
                    ready.add(str(path))
            yield connection
            connection.commit()
        except Exception:
            connection.rollback();raise
        finally:connection.close()

    def purge(connection,now):
        key=app.instance_path
        if now-last_purge.get(key,0)<3600:return
        cutoff=now-RETENTION_DAYS*86400
        for table,column in [('visitors','last'),('visitor_ips','last'),('events','created'),('chat_archive','created'),('requests','minute')]:
            connection.execute(f'DELETE FROM {table} WHERE {column}<?',(cutoff/60 if table=='requests' else cutoff,))
        connection.execute('DELETE FROM login_attempts WHERE until<?',(now,))
        last_purge[key]=now

    def flush(connection,force=False):
        key=app.instance_path
        with lock:
            sample=metrics.get(key)
            if not sample or (not force and time.monotonic()-sample['flushed']<5):return
            for minute,total,errors,elapsed in sample['buckets'].values():
                connection.execute('INSERT INTO requests VALUES(?,?,?,?) ON CONFLICT(minute) DO UPDATE SET total=total+excluded.total,errors=errors+excluded.errors,elapsed=elapsed+excluded.elapsed',(minute,total,errors,elapsed))
            sample['buckets'].clear();sample['flushed']=time.monotonic()

    def seed_archive():
        """Owner-run setup can copy still-existing, recent room messages."""
        path=Path(app.instance_path)/'afterglow.db'
        if not path.exists():return 0
        with closing(sqlite3.connect(path,timeout=5)) as source, storage() as connection:
            source.row_factory=sqlite3.Row;before=connection.total_changes
            for row in source.execute('SELECT m.*,r.name AS reply_name,r.body AS reply_body FROM messages m LEFT JOIN messages r ON r.room=m.room AND r.id=m.reply_to WHERE m.created>=?',(time.time()-RETENTION_DAYS*86400,)):
                who=hmac.new(str(app.secret_key).encode(),str(row['sender'] or row['name']).encode(),hashlib.sha256).hexdigest()[:24]
                reply={'id':row['reply_to'],'name':row['reply_name'],'body':row['reply_body'][:160]} if row['reply_to'] and row['reply_body'] is not None else None
                connection.execute('INSERT OR IGNORE INTO chat_archive VALUES(?,?,?,?,?,?,?)',(row['room'],row['id'],who,row['name'],row['body'],json.dumps(reply),row['created']))
            return connection.total_changes-before

    app.extensions['solace_ops']={'seed_archive':seed_archive}

    @app.before_request
    def operations_timer():g.ops_started=time.perf_counter()

    @app.after_request
    def collect_operations(response):
        if request.path.startswith(BASE):
            # Preserve Origin on same-site form posts; no-referrer can produce Origin:null.
            response.headers.update({'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
            return response
        if request.path!='/' and not request.path.startswith('/api/'):return response
        now=time.time();key=app.instance_path;uid=visitor();ip=client_ip()
        try:payload=request.get_json(silent=True) if request.is_json else {}
        except HTTPException:payload={}
        payload=payload if isinstance(payload,dict) else {}
        action=payload.get('action');room=(request.view_args or {}).get('room_id')
        event=None
        if response.status_code<400:
            if request.path=='/':event='opened_site'
            elif action=='join' and room and request.path=='/api/rooms/'+room:event='joined_room'
            elif request.path.endswith('/leave'):event='left_room'
            elif request.path.endswith('/presence'):event='active' if payload.get('active') else 'inactive'
        chat=response.status_code<400 and action=='chat' and room and request.path=='/api/rooms/'+room
        with lock:
            sample=metrics.setdefault(key,{'flushed':time.monotonic(),'buckets':{}})
            minute=int(now//60);bucket=sample['buckets'].setdefault(minute,[minute,0,0,0.0]);bucket[1]+=1;bucket[2]+=int(response.status_code>=500);bucket[3]+=max(0,time.perf_counter()-getattr(g,'ops_started',time.perf_counter()))
            touch_key=(key,uid,ip);due=event or chat or now-touches.get(touch_key,0)>=5
            if due:touches[touch_key]=now
            if len(touches)>4096:touches.clear()
        if not due:return response
        try:
            with storage() as connection:
                prior=connection.execute('SELECT name,active FROM visitors WHERE id=?',(uid,)).fetchone()
                name=(str(payload.get('name','')).strip()[:24] or 'Guest') if event=='joined_room' else (prior['name'] if prior else 'Guest')
                active=0 if event in ('inactive','left_room') else 1 if event in ('active','joined_room','opened_site') or not prior else prior['active']
                connection.execute('INSERT INTO visitors VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,ip=excluded.ip,agent=excluded.agent,last=excluded.last,last_join=COALESCE(excluded.last_join,visitors.last_join),last_leave=COALESCE(excluded.last_leave,visitors.last_leave),active=excluded.active',(uid,name,ip,request.user_agent.string[:200],now,now,now if event=='joined_room' else None,now if event=='left_room' else None,active))
                connection.execute('INSERT INTO visitor_ips VALUES(?,?,?,?) ON CONFLICT(visitor,ip) DO UPDATE SET last=excluded.last',(uid,ip,now,now))
                if event:connection.execute('INSERT INTO events(visitor,name,ip,event,room,created) VALUES(?,?,?,?,?,?)',(uid,name,ip,event,room,now))
                if chat:
                    body=response.get_json(silent=True) or {}
                    message=next((m for m in reversed(body.get('messages',[])) if m.get('you') and m.get('body')==str(payload.get('body','')).strip()[:500]),None)
                    if message:connection.execute('INSERT OR IGNORE INTO chat_archive VALUES(?,?,?,?,?,?,?)',(room,message['id'],uid,message['name'],message['body'],json.dumps(message.get('reply')),message['created']))
                purge(connection,now);flush(connection)
        except (sqlite3.Error,OSError):
            # Operational logging must not block or fail a room/chat request.
            app.logger.warning('Private operations sample could not be saved.')
        return response

    def configured():
        if not app.testing and not request.is_secure and request.remote_addr not in ('127.0.0.1','::1'):
            abort(403)
        value=credential()
        if not value:abort(404)
        return value

    def authorized():
        value=configured()
        expected=hashlib.sha256(value.encode()).hexdigest()
        return session.get('ops_version')==expected and 0<=time.time()-session.get('ops_issued',0)<1800

    def csrf_valid():
        token=request.form.get('csrf') or request.headers.get('X-CSRF-Token','')
        return bool(session.get('ops_csrf')) and hmac.compare_digest(str(token),session['ops_csrf'])

    @app.route(BASE,methods=['GET','POST'])
    def operations_home():
        value=configured();error=None
        if authorized():return render_template('admin.html',csrf=session['ops_csrf'])
        if request.method=='POST':
            if not csrf_valid():abort(403)
            now=time.time();ip=client_ip()
            with storage(timeout=2) as connection:
                connection.execute('BEGIN IMMEDIATE')
                entry=connection.execute('SELECT attempts,until FROM login_attempts WHERE ip=?',(ip,)).fetchone()
                if entry and entry['until']>now and entry['attempts']>=5:
                    return render_template('admin-login.html',csrf=session['ops_csrf'],error='Too many attempts. Try again in 15 minutes.'),429
                if check_password_hash(value,request.form.get('password','')[:1024]):
                    connection.execute('DELETE FROM login_attempts WHERE ip=?',(ip,))
                    connection.execute('INSERT INTO events(visitor,name,ip,event,room,created) VALUES(?,?,?,?,?,?)',(visitor(),'Administrator',ip,'admin_login',None,now))
                    session.update(ops_version=hashlib.sha256(value.encode()).hexdigest(),ops_issued=now,ops_csrf=secrets.token_urlsafe(32))
                    return redirect(BASE,code=303)
                count=entry['attempts']+1 if entry and entry['until']>now else 1
                until=entry['until'] if entry and entry['until']>now else now+900
                connection.execute('INSERT INTO login_attempts VALUES(?,?,?) ON CONFLICT(ip) DO UPDATE SET attempts=excluded.attempts,until=excluded.until',(ip,count,until))
                error='Password not accepted.'
        session['ops_csrf']=session.get('ops_csrf') or secrets.token_urlsafe(32)
        return render_template('admin-login.html',csrf=session['ops_csrf'],error=error),401 if error else 200

    @app.post(BASE+'/logout')
    def operations_logout():
        if not authorized() or not csrf_valid():abort(403)
        with storage() as connection:
            connection.execute('INSERT INTO events(visitor,name,ip,event,room,created) VALUES(?,?,?,?,?,?)',(visitor(),'Administrator',client_ip(),'admin_logout',None,time.time()))
        for key in ('ops_version','ops_issued','ops_csrf'):session.pop(key,None)
        return redirect(BASE,code=303)

    @app.get(BASE+'/data')
    def operations_data():
        if not authorized():abort(401)
        now=time.time()
        with storage() as connection:
            purge(connection,now);flush(connection,force=True)
            visitors=[dict(r) for r in connection.execute('SELECT * FROM visitors WHERE last>=? ORDER BY last DESC LIMIT 300',(now-RETENTION_DAYS*86400,))]
            events=[dict(r) for r in connection.execute('SELECT name,ip,event,room,created FROM events WHERE created>=? ORDER BY id DESC LIMIT 200',(now-RETENTION_DAYS*86400,))]
            matches=[dict(r) for r in connection.execute("SELECT ip,COUNT(DISTINCT visitor) AS devices FROM visitor_ips WHERE ip!='unknown' AND last>=? GROUP BY ip HAVING COUNT(DISTINCT visitor)>1 ORDER BY devices DESC LIMIT 100",(now-RETENTION_DAYS*86400,))]
            traffic=dict(connection.execute('SELECT COALESCE(SUM(total),0) AS requests,COALESCE(SUM(errors),0) AS errors,COALESCE(SUM(elapsed),0) AS elapsed FROM requests WHERE minute>=?',(int(now//60)-4,)).fetchone())
            backups=connection.execute('SELECT count(*) FROM chat_archive WHERE created>=?',(now-RETENTION_DAYS*86400,)).fetchone()[0]
        check=time.perf_counter();rooms=members=0;status='online'
        try:
            with closing(sqlite3.connect(Path(app.instance_path)/'afterglow.db',timeout=.15)) as connection:
                rooms=connection.execute('SELECT count(*) FROM rooms').fetchone()[0]
                members=connection.execute('SELECT count(*) FROM members WHERE seen>?',(now-15,)).fetchone()[0]
        except sqlite3.Error:status='database_unavailable'
        load=list(os.getloadavg()) if hasattr(os,'getloadavg') else None
        uptime=max(.001,time.monotonic()-started)
        return jsonify(status=status,db_check_ms=round((time.perf_counter()-check)*1000,2),rooms=rooms,active_members=members,visitors=visitors,events=events,ip_matches=matches,chat_backup_count=backups,traffic=traffic,host_load_averages=load,worker_uptime_seconds=round(uptime),worker_cpu_average_percent=round((time.process_time()-cpu_started)/uptime*100,2),retention_days=RETENTION_DAYS,ip_source='Trusted X-Real-IP' if app.config.get('OPS_TRUST_X_REAL_IP') or os.environ.get('SOLACE_TRUST_X_REAL_IP')=='1' else 'WSGI remote address',now=now)

    @app.get(BASE+'/chat-backup.json')
    def operations_backup():
        if not authorized():abort(401)
        @stream_with_context
        def content():
            with storage() as connection:
                purge(connection,time.time())
                yield '{"retention_days":30,"messages":['
                first=True
                for row in connection.execute('SELECT room,message_id,name,body,reply,created FROM chat_archive WHERE created>=? ORDER BY created,message_id',(time.time()-RETENTION_DAYS*86400,)):
                    message=dict(row);message['reply']=json.loads(message['reply'])
                    yield ('' if first else ',')+json.dumps(message,ensure_ascii=False);first=False
                yield ']}'
        return Response(content(),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="solace-chat-backup.json"'})
