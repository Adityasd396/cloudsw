import os
import re
import secrets
import sqlite3
import time
import json
import html
import math
import threading
import hashlib
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse, parse_qs, urlencode
from flask import Flask, g, jsonify, render_template, request, session
from flask.sessions import SecureCookieSessionInterface

app = Flask(__name__)
Path(app.instance_path).mkdir(exist_ok=True)
key_file = Path(app.instance_path) / 'secret'
configured_secret=os.environ.get('SECRET_KEY')
if configured_secret:
    app.secret_key=configured_secret
else:
    try:
        descriptor=os.open(key_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:pass
    else:
        with os.fdopen(descriptor,'w') as output:
            output.write(secrets.token_hex(32));output.flush();os.fsync(output.fileno())
    # An exclusive creator may still be finishing its tiny write in another worker.
    for attempt in range(40):
        try:saved_secret=key_file.read_text()
        except PermissionError:saved_secret=''
        if saved_secret.strip():
            app.secret_key=saved_secret;break
        time.sleep(.025)
    else:raise RuntimeError('The saved server secret is unavailable; keep the existing instance directory and retry startup.')
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=16384, PERMANENT_SESSION_LIFETIME=timedelta(days=365), ROOM_RECONNECT_GRACE_SECONDS=1800)

class HttpsSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self, application):
        return request.is_secure or super().get_cookie_secure(application)

app.session_interface=HttpsSessionInterface()
from admin_panel import register_admin
register_admin(app)



def youtube_key():
    try:
        saved = (Path(app.instance_path) / 'youtube.key').read_text().strip()
        if saved:
            return saved
    except FileNotFoundError:
        pass
    return os.environ.get('YOUTUBE_API_KEY', '').strip().strip('"\'')


class YouTubeError(Exception):
    def __init__(self, message, code='youtube_unavailable'):
        super().__init__(message)
        self.code = code


def youtube_request(params, key):
    try:
        with urlopen('https://www.googleapis.com/youtube/v3/search?' + urlencode({**params, 'key': key}), timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            details = json.load(error).get('error', {})
            reasons = [entry.get('reason', '') for entry in details.get('errors', [])]
            message = details.get('message', '').lower()
        except (ValueError, AttributeError):
            reasons, message = [], ''
        if any(reason in ('quotaExceeded', 'dailyLimitExceeded') for reason in reasons):
            raise YouTubeError('YouTube search quota has been reached. Try again after the quota resets.', 'quota_exceeded') from None
        if 'accessNotConfigured' in reasons or 'not been used' in message or 'disabled' in message:
            raise YouTubeError('Enable YouTube Data API v3 in the Google Cloud project that owns this key.', 'api_disabled') from None
        if 'keyInvalid' in reasons or 'api key not valid' in message:
            raise YouTubeError('Google rejected this API key. Copy the full key from Google Cloud and try again.', 'invalid_key') from None
        if error.code == 403:
            raise YouTubeError('Google blocked this key. Check its API restrictions and allow YouTube Data API v3 for server requests.', 'key_restricted') from None
        raise YouTubeError('YouTube could not complete this search. Please try again.', 'youtube_unavailable') from None
    except (URLError, TimeoutError, ValueError, OSError):
        raise YouTubeError('Cannot reach YouTube right now. Check the server internet connection and try again.', 'connection_failed') from None


def local_settings_allowed():
    return request.remote_addr in ('127.0.0.1', '::1') and request.host.split(':')[0] in ('127.0.0.1', 'localhost', '[::1]')


@app.get('/api/settings')
def settings_status():
    return jsonify(search_enabled=bool(youtube_key()), can_configure=local_settings_allowed() and not bool(youtube_key()))


@app.post('/api/settings/youtube')
def configure_youtube():
    if not local_settings_allowed():
        return jsonify(error='YouTube settings can only be changed on the server computer.'), 403
    if youtube_key():
        return jsonify(error='YouTube is already configured. Manage the saved key on the server.'),409
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Enter your YouTube API key.'), 400
    key = str(data.get('key', '')).strip().strip('"\'')
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,100}', key):
        return jsonify(error='Paste the full API key, without command text or brackets.'), 400
    try:
        youtube_request({'part':'snippet', 'type':'video', 'videoEmbeddable':'true', 'maxResults':1, 'q':'music'}, key)
    except YouTubeError as error:
        return jsonify(error=str(error), code=error.code), 400
    key_path = Path(app.instance_path) / 'youtube.key'
    temporary = key_path.with_suffix('.tmp')
    temporary.write_text(key)
    temporary.replace(key_path)
    # A newly validated key takes effect in this process immediately.
    os.environ['YOUTUBE_API_KEY'] = key
    search_cache.clear()
    return jsonify(search_enabled=True, message='YouTube search is connected.')

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(Path(app.instance_path) / 'afterglow.db', timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA busy_timeout=5000')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

with app.app_context():
    db().executescript('''
    BEGIN IMMEDIATE;
    CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, name TEXT, host TEXT, video TEXT, playing INTEGER DEFAULT 0, position REAL DEFAULT 0, updated REAL);
    CREATE TABLE IF NOT EXISTS members(room TEXT, id TEXT, name TEXT, seen REAL, PRIMARY KEY(room,id));
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, name TEXT, body TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, video TEXT, title TEXT, added_by TEXT, sort_order INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL, updated REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS typing(room TEXT, id TEXT, updated REAL NOT NULL, PRIMARY KEY(room,id));
    CREATE TABLE IF NOT EXISTS presence(room TEXT,id TEXT,active INTEGER NOT NULL,PRIMARY KEY(room,id));
    CREATE TABLE IF NOT EXISTS room_ads(room TEXT PRIMARY KEY,active INTEGER NOT NULL,updated REAL NOT NULL);
    CREATE INDEX IF NOT EXISTS message_room_idx ON messages(room,id);
    ''')
    db().execute('CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    db().execute('INSERT OR IGNORE INTO app_metadata VALUES(?,?)',('generation',secrets.token_hex(16)))
    if 'sort_order' not in {column['name'] for column in db().execute('PRAGMA table_info(queue)')}:
        db().execute('ALTER TABLE queue ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0')
        db().execute('UPDATE queue SET sort_order=id')
    if 'sender' not in {column['name'] for column in db().execute('PRAGMA table_info(messages)')}:
        db().execute('ALTER TABLE messages ADD COLUMN sender TEXT')
    if 'playback_id' not in {column['name'] for column in db().execute('PRAGMA table_info(rooms)')}:
        db().execute("ALTER TABLE rooms ADD COLUMN playback_id TEXT NOT NULL DEFAULT ''")
        db().execute('UPDATE rooms SET playback_id=lower(hex(randomblob(12)))')
    if 'reply_to' not in {column['name'] for column in db().execute('PRAGMA table_info(messages)')}:
        db().execute('ALTER TABLE messages ADD COLUMN reply_to INTEGER')
    db().execute('CREATE TABLE IF NOT EXISTS participant_ads(room TEXT,id TEXT,active INTEGER NOT NULL,updated REAL NOT NULL,started REAL NOT NULL,PRIMARY KEY(room,id))')
    db().execute('CREATE TABLE IF NOT EXISTS room_games(room TEXT PRIMARY KEY,state TEXT NOT NULL)')
    if 'playback_revision' not in {column['name'] for column in db().execute('PRAGMA table_info(rooms)')}:
        db().execute('ALTER TABLE rooms ADD COLUMN playback_revision INTEGER NOT NULL DEFAULT 0')
    if 'command_revision' not in {column['name'] for column in db().execute('PRAGMA table_info(rooms)')}:
        db().execute('ALTER TABLE rooms ADD COLUMN command_revision INTEGER NOT NULL DEFAULT 0')
        db().execute('UPDATE rooms SET command_revision=playback_revision')
    db().executescript("""
    CREATE TABLE IF NOT EXISTS mutation_receipts(room TEXT,actor TEXT,request_id TEXT,payload_hash TEXT,result TEXT,created REAL,PRIMARY KEY(room,actor,request_id));
    CREATE INDEX IF NOT EXISTS receipt_time ON mutation_receipts(created);
    CREATE TABLE IF NOT EXISTS reliability_metrics(minute INTEGER,name TEXT,count INTEGER,total REAL,maximum REAL,PRIMARY KEY(minute,name));
    CREATE INDEX IF NOT EXISTS member_room_seen ON members(room,seen);
    CREATE INDEX IF NOT EXISTS queue_room_order ON queue(room,sort_order,id);
    """)
    db().commit()

@app.before_request
def identity():
    if 'uid' not in session:
        session['uid'] = secrets.token_urlsafe(24)
    session.permanent = True
    if request.method == 'POST' and request.headers.get('Origin') and request.headers['Origin'] != request.host_url.rstrip('/'):
        return jsonify(error='Cross-origin requests are not allowed.'), 403
    if request.method == 'POST' and request.is_json and not isinstance(request.get_json(silent=True), dict):
        return jsonify(error='Send a valid request object.'), 400
    if request.path.startswith('/api/'):
        cleanup_empty_rooms()


def delete_room_records(room_id):
    for table in ('messages','queue','typing','presence','room_ads','participant_ads','room_games','mutation_receipts','members'):
        db().execute(f'DELETE FROM {table} WHERE room=?',(room_id,))
    db().execute('DELETE FROM rooms WHERE id=?',(room_id,))


def cleanup_empty_rooms():
    """Expire abandoned rooms when the next API request reaches this worker."""
    cutoff=time.time()-max(120,int(app.config['ROOM_RECONNECT_GRACE_SECONDS']))
    expired=db().execute('SELECT id FROM rooms WHERE updated<? AND NOT EXISTS (SELECT 1 FROM members WHERE members.room=rooms.id AND members.seen>=?)',(cutoff,cutoff)).fetchall()
    if not expired:return
    db().execute('BEGIN IMMEDIATE')
    for candidate in expired:
        still_empty=db().execute('SELECT id FROM rooms WHERE id=? AND updated<? AND NOT EXISTS (SELECT 1 FROM members WHERE members.room=rooms.id AND members.seen>=?)',(candidate['id'],cutoff,cutoff)).fetchone()
        if still_empty:delete_room_records(candidate['id'])
    db().commit()

def video_id(value):
    value = str(value).strip()
    if re.fullmatch(r'[\w-]{11}', value, flags=re.ASCII):
        return value
    try:
        u = urlparse(value)
        hostname = u.hostname
    except ValueError:
        return None
    if u.scheme not in ('http', 'https'):
        return None
    if hostname in ('youtu.be', 'www.youtu.be'):
        value = u.path.strip('/').split('/')[0]
    elif hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        value = parse_qs(u.query).get('v', [''])[0] if u.path == '/watch' else u.path.split('/')[-1] if u.path.startswith(('/shorts/', '/embed/', '/live/')) else ''
    else:
        return None
    return value if re.fullmatch(r'[\w-]{11}', value, flags=re.ASCII) else None

@app.get('/')
def index():
    return render_template('index.html')


def release_info():
    try:return json.loads(Path(__file__).with_name('release.json').read_text())
    except (OSError,ValueError):return {'version':'development'}


CURRENT_RELEASE=release_info()

@app.get('/api/health')
def health():
    return jsonify(application='solace', release=CURRENT_RELEASE, reconnect_grace_seconds=app.config['ROOM_RECONNECT_GRACE_SECONDS'], protocol=1, status='ok', capabilities=['room_leave_v2','shared_playback_v3','tictactoe_v1','basketball_v1','chat_identity_v1','room_experience_v4','ordered_playback_v1','safe_retries_v1'])


@app.get('/api/profile')
def profile():
    saved=db().execute('SELECT name FROM profiles WHERE id=?',(session['uid'],)).fetchone()
    return jsonify(name=saved['name'] if saved else '')

FEATURED = [
    {'id':'aqz-KE-bpKQ','title':'Big Buck Bunny','channel':'Blender Foundation','category':'Films'},
    {'id':'eRsGyueVLvQ','title':'Sintel — animated short film','channel':'Blender Foundation','category':'Films'},
    {'id':'R6MlUcmOul8','title':'Tears of Steel','channel':'Blender Foundation','category':'Films'},
    {'id':'21X5lGlDOfg','title':'NASA live: Earth from space','channel':'NASA','category':'Explore'},
    {'id':'ysz5S6PUM-U','title':'A moment in nature','channel':'Featured video','category':'Explore'},
    {'id':'jNQXAC9IVRw','title':'Me at the zoo','channel':'jawed','category':'Explore'},
]
search_cache = {}
search_lock = threading.Lock()

@app.get('/api/videos')
def browse_videos():
    query = request.args.get('q', '').strip()[:120]
    category = request.args.get('category', 'All')
    key = youtube_key()
    if query and not key:
        return jsonify(error='YouTube search has not been connected on this server.',code='search_not_configured'),503
    if not query or not key:
        items = [item for item in FEATURED if (category == 'All' or item['category'] == category) and (not query or query.lower() in (item['title']+' '+item['channel']+' '+item['category']).lower())]
        return jsonify(items=items, source='featured', search_enabled=bool(key), notice='Search is limited to the featured collection. Full YouTube search is not connected yet.' if query and not key else '')
    token = request.args.get('page', '')[:200]
    cache_key = (query, token)
    with search_lock:
        cached = search_cache.get(cache_key)
    if cached and time.time() - cached[0] < 300:
        return jsonify(cached[1])
    if time.time() - session.get('last_search', 0) < 1:
        return jsonify(error='Please wait a second before searching again.'), 429
    session['last_search'] = time.time()
    params = {'key':key,'part':'snippet','type':'video','videoEmbeddable':'true','videoSyndicated':'true','maxResults':12,'q':query,'safeSearch':'moderate'}
    if token:
        params['pageToken'] = token
    try:
        result = youtube_request(params, key)
        data = {'items':[{'id':item['id']['videoId'],'title':html.unescape(item['snippet']['title']),'channel':html.unescape(item['snippet']['channelTitle'])} for item in result.get('items',[]) if item.get('id',{}).get('videoId')], 'next_page':result.get('nextPageToken'), 'source':'youtube', 'search_enabled':True}
        with search_lock:
            if len(search_cache) >= 100:
                search_cache.clear()
            search_cache[cache_key] = (time.time(), data)
        return jsonify(data)
    except YouTubeError as error:
        return jsonify(error=str(error), code=error.code), 502

def mutation_token(data):
    token=request.headers.get('X-Request-ID') or data.get('request_id')
    if token is None:return None,None
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,100}',token):
        raise ValueError('Invalid request ID.')
    body={key:value for key,value in data.items() if key!='request_id'}
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return token,digest


def receipt(room_id,token,digest):
    if not token:return None
    saved=db().execute('SELECT payload_hash,result FROM mutation_receipts WHERE room=? AND actor=? AND request_id=?',(room_id,session['uid'],token)).fetchone()
    if saved and saved['payload_hash']!=digest:raise ValueError('Request ID already used for another action.')
    return json.loads(saved['result']) if saved else None


def save_receipt(room_id,token,digest,result=None):
    if not token:return
    db().execute('INSERT INTO mutation_receipts VALUES(?,?,?,?,?,?)',(room_id,session['uid'],token,digest,json.dumps(result or {'ok':True}),time.time()))
    db().execute('DELETE FROM mutation_receipts WHERE created<?',(time.time()-86400,))


def reliability_record(name,value=1):
    minute=int(time.time()//60)
    db().execute('INSERT INTO reliability_metrics VALUES(?,?,1,?,?) ON CONFLICT(minute,name) DO UPDATE SET count=count+1,total=total+excluded.total,maximum=MAX(maximum,excluded.maximum)',(minute,name,value,value))


@app.post('/api/rooms')
def create_room():
    data = request.get_json(silent=True) or {}
    try:token,digest=mutation_token(data)
    except ValueError as error:return jsonify(error=str(error)),400
    db().execute('BEGIN IMMEDIATE')
    try:saved=receipt('__create__',token,digest)
    except ValueError as error:return jsonify(error=str(error)),409
    if saved:
        db().rollback();return jsonify(saved),201
    name = str(data.get('name', 'Late night lounge')).strip()[:60] or 'Late night lounge'
    for _ in range(20):
        room_id = str(secrets.randbelow(900000)+100000)
        try:
            db().execute('INSERT INTO rooms(id,name,host,video,updated,playback_id) VALUES(?,?,?,?,?,?)', (room_id,name,session['uid'],'aqz-KE-bpKQ',time.time(),secrets.token_hex(12)))
            break
        except sqlite3.IntegrityError:
            continue
    else:
        return jsonify(error='Could not create a room right now. Please try again.'),503
    save_receipt('__create__',token,digest,{'id':room_id})
    db().commit()
    return jsonify(id=room_id), 201

@app.route('/api/rooms/<room_id>', methods=['GET', 'POST'])
def room(room_id):
    if request.method=='POST':db().execute('BEGIN IMMEDIATE')
    room = db().execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        return jsonify(error='Room not found. Create a new room or check your invite link.'), 404
    if request.method=='GET' and not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone():return jsonify(error='Join the room first.'),403
    now = time.time()
    data = request.get_json(silent=True) or {}
    token=digest=None
    replayed=False
    mutation_result=None
    if request.method=='POST':
        try:
            token,digest=mutation_token(data)
            mutation_result=receipt(room_id,token,digest)
            replayed=mutation_result is not None
        except ValueError as error:return jsonify(error=str(error)),409
    if replayed and not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone():return jsonify(error='Join the room first.'),403
    if request.method == 'POST' and not replayed:
        action = data.get('action')
        name = str(data.get('name', 'Guest')).strip()[:24] or 'Guest'
        if action == 'join':
            db().execute('INSERT INTO members VALUES(?,?,?,?) ON CONFLICT(room,id) DO UPDATE SET name=excluded.name,seen=excluded.seen', (room_id,session['uid'],name,now))
            db().execute('INSERT INTO profiles VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated=excluded.updated',(session['uid'],name,now))
            db().execute('INSERT INTO presence VALUES(?,?,1) ON CONFLICT(room,id) DO UPDATE SET active=1',(room_id,session['uid']))
        else:
            member = db().execute('SELECT * FROM members WHERE room=? AND id=?', (room_id,session['uid'])).fetchone()
            if not member:
                return jsonify(error='Join the room first.'), 403
            if action == 'ad_status':
                active=int(bool(data.get('active')))
                db().execute('INSERT INTO participant_ads VALUES(?,?,?,?,?) ON CONFLICT(room,id) DO UPDATE SET active=excluded.active,updated=excluded.updated,started=CASE WHEN excluded.active=1 AND (participant_ads.active=0 OR participant_ads.updated<excluded.updated-10) THEN excluded.started ELSE participant_ads.started END',(room_id,session['uid'],active,now,now))
                if room['host']==session['uid']:
                    db().execute('INSERT INTO room_ads VALUES(?,?,?) ON CONFLICT(room) DO UPDATE SET active=excluded.active,updated=excluded.updated',(room_id,active,now))
            elif action == 'typing':
                if data.get('active'):
                    db().execute('INSERT INTO typing VALUES(?,?,?) ON CONFLICT(room,id) DO UPDATE SET updated=excluded.updated',(room_id,session['uid'],now))
                else:
                    db().execute('DELETE FROM typing WHERE room=? AND id=?',(room_id,session['uid']))
            elif action == 'chat':
                body = str(data.get('body', '')).strip()[:500]
                if not body:
                    return jsonify(error='Write a message first.'), 400
                recent = db().execute('SELECT created FROM messages WHERE room=? AND sender=? ORDER BY id DESC LIMIT 1', (room_id,session['uid'])).fetchone()
                if recent and now-recent['created'] < .5:
                    return jsonify(error='Please wait a moment before sending again.'), 429
                reply=data.get('reply_to')
                if reply is not None and (type(reply) is not int or not db().execute('SELECT 1 FROM messages WHERE room=? AND id=?',(room_id,reply)).fetchone()):
                    return jsonify(error='That reply is not available in this room.'),400
                db().execute('INSERT INTO messages(room,name,body,created,sender,reply_to) VALUES(?,?,?,?,?,?)', (room_id,member['name'],body,now,session['uid'],reply))
                db().execute('DELETE FROM typing WHERE room=? AND id=?',(room_id,session['uid']))
            elif action == 'add':
                video = video_id(data.get('url', ''))
                if not video:
                    return jsonify(error='Enter a valid YouTube video link.'), 400
                if db().execute('SELECT count(*) FROM queue WHERE room=?',(room_id,)).fetchone()[0] >= 100:
                    return jsonify(error='The queue is full.'),400
                db().execute('INSERT INTO queue(room,video,title,added_by,sort_order) VALUES(?,?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM queue WHERE room=?))', (room_id,video,str(data.get('title','')).strip()[:100] or 'YouTube video',member['name'],room_id))
            elif action == 'claim_host':
                host = db().execute('SELECT seen FROM members WHERE room=? AND id=?',(room_id,room['host'])).fetchone()
                if host and now-host['seen'] < 30 and room['host'] != session['uid']:
                    return jsonify(error='The host is still connected.'),409
                db().execute('UPDATE rooms SET host=? WHERE id=?',(session['uid'],room_id))
            elif action in ('playback','next','select','remove','watch','transfer_host','move'):
                if action=='transfer_host' and room['host'] != session['uid']:
                    return jsonify(error='Only the host can transfer hosting.'), 403
                if action == 'move':
                    direction = data.get('direction')
                    if direction not in ('up','down'):
                        return jsonify(error='Choose up or down.'),400
                    items = db().execute('SELECT id,sort_order FROM queue WHERE room=? ORDER BY sort_order,id',(room_id,)).fetchall()
                    index = next((i for i,item in enumerate(items) if item['id']==data.get('id')),None)
                    if index is None:
                        return jsonify(error='That playlist item has already been removed.'),404
                    adjacent = index + (-1 if direction=='up' else 1)
                    if 0 <= adjacent < len(items):
                        ordered = [item['id'] for item in items]
                        ordered[index],ordered[adjacent] = ordered[adjacent],ordered[index]
                        db().executemany('UPDATE queue SET sort_order=? WHERE room=? AND id=?',[(i,room_id,item_id) for i,item_id in enumerate(ordered,1)])
                elif action == 'transfer_host':
                    target = next((member for member in db().execute('SELECT id FROM members WHERE room=? AND seen>?',(room_id,now-20)) if hashlib.sha256((room_id+member['id']).encode()).hexdigest()[:20] == data.get('member_id')),None)
                    if not target:
                        return jsonify(error='That participant is no longer connected.'),400
                    db().execute('UPDATE rooms SET host=? WHERE id=?',(target['id'],room_id))
                    db().execute('DELETE FROM room_ads WHERE room=?',(room_id,))
                elif action == 'watch':
                    video = video_id(data.get('url',''))
                    if not video:
                        return jsonify(error='Enter a valid YouTube video.'),400
                    db().execute('UPDATE rooms SET video=?,position=0,playing=1,updated=?,playback_id=? WHERE id=?',(video,now,secrets.token_hex(12),room_id))
                elif action == 'playback':
                    source=data.get('source','command')
                    if source not in ('command','observation'):return jsonify(error='Invalid playback source.'),400
                    if source=='observation' and room['host']!=session['uid']:return jsonify(error='Only the host publishes observations.'),403
                    expected=data.get('expected_revision')
                    if 'expected_revision' in data and (type(expected) is not int or expected<0 or expected>room['playback_revision'] or (source=='observation' and expected!=room['playback_revision']) or (source=='command' and expected<room['command_revision'])):
                        return jsonify(error='Playback changed. Refresh room state.',code='stale_playback',playback_revision=room['playback_revision']),409
                    if 'expected_playback_id' in data and data['expected_playback_id']!=room['playback_id']:return jsonify(error='The video changed.',code='stale_playback'),409
                    if source=='observation' and 'expected_revision' not in data:return jsonify(error='Refresh playback before publishing.'),409
                    if 'expected_updated' in data:
                        latest=db().execute('SELECT updated FROM rooms WHERE id=?',(room_id,)).fetchone()
                        if data['expected_updated']!=latest['updated']:return jsonify(error='Playback changed. Refresh room state.',code='stale_playback'),409
                    try:
                        position = float(data.get('position',0))
                        if not math.isfinite(position):
                            raise ValueError()
                        position = max(0, min(position, 864000))
                    except (ValueError, TypeError):
                        return jsonify(error='Invalid playback position.'),400
                    db().execute('UPDATE rooms SET position=?,playing=?,updated=? WHERE id=?',(position,int(bool(data.get('playing'))),now,room_id))
                else:
                    if action=='next':
                        latest=db().execute('SELECT playback_id FROM rooms WHERE id=?',(room_id,)).fetchone()
                        if not latest or ('expected_playback_id' in data and data['expected_playback_id']!=latest['playback_id']):
                            return jsonify(error='The queue has already advanced.',code='stale_playback'),409
                    item = db().execute('SELECT * FROM queue WHERE room=? ORDER BY sort_order,id LIMIT 1',(room_id,)).fetchone() if action == 'next' else db().execute('SELECT * FROM queue WHERE room=? AND id=?',(room_id,data.get('id'))).fetchone()
                    if item:
                        if action != 'remove':
                            db().execute('UPDATE rooms SET video=?,position=0,playing=1,updated=?,playback_id=? WHERE id=?',(item['video'],now,secrets.token_hex(12),room_id))
                        db().execute('DELETE FROM queue WHERE id=?',(item['id'],))
                    elif action != 'next':
                        return jsonify(error='That playlist item has already been removed.'),404
                    else:
                        db().execute('UPDATE rooms SET playing=0,updated=?,playback_id=? WHERE id=?',(now,secrets.token_hex(12),room_id))
            else:
                return jsonify(error='Unknown action.'),400
        if data.get('action') in ('playback','watch','select','next'):
            db().execute('UPDATE rooms SET playback_revision=playback_revision+1 WHERE id=?',(room_id,))
            if data.get('action')!='playback' or data.get('source','command')=='command':db().execute('UPDATE rooms SET command_revision=playback_revision WHERE id=?',(room_id,))
        if data.get('action')=='playback':
            clock=db().execute('SELECT updated,playback_id,playback_revision FROM rooms WHERE id=?',(room_id,)).fetchone()
            mutation_result={'ok':True,**dict(clock)}
        save_receipt(room_id,token,digest,mutation_result)
        db().commit()
    elif replayed:
        reliability_record('mutation_replay');db().commit()
    db().execute('UPDATE members SET seen=? WHERE room=? AND id=? AND seen<?',(now,room_id,session['uid'],now-1))
    db().commit()
    if request.method == 'POST' and data.get('action') == 'playback' and data.get('compact'):
        return jsonify(mutation_result)
    db().execute('BEGIN')
    room = dict(db().execute('SELECT * FROM rooms WHERE id=?',(room_id,)).fetchone())
    host_id = room.pop('host')
    room['is_host'] = host_id == session['uid']
    room['can_control']=bool(db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone())
    ad=db().execute('SELECT active,updated FROM room_ads WHERE room=?',(room_id,)).fetchone()
    room['host_ad']=bool(ad and ad['active'] and now-ad['updated']<10)
    room['ad_alerts']=[{'member_id':hashlib.sha256((room_id+row['id']).encode()).hexdigest()[:20],'name':row['name'],'you':row['id']==session['uid'],'started':row['started']} for row in db().execute('SELECT a.id,m.name,a.started FROM participant_ads a JOIN members m ON a.room=m.room AND a.id=m.id WHERE a.room=? AND a.active=1 AND a.updated>?',(room_id,now-10))]

    host = db().execute('SELECT seen FROM members WHERE room=? AND id=?',(room_id,host_id)).fetchone()
    room['can_claim_host'] = not host or now-host['seen'] >= 30
    room['release_version']=CURRENT_RELEASE.get('version','development')
    room['server_time'] = time.time()
    room['storage_generation']=db().execute("SELECT value FROM app_metadata WHERE key='generation'").fetchone()[0]
    room['members']=[dict(x) for x in db().execute('SELECT members.name,members.id,members.seen,COALESCE(presence.active,1) AS presence_active FROM members LEFT JOIN presence ON members.room=presence.room AND members.id=presence.id WHERE members.room=? ORDER BY members.seen DESC LIMIT 100',(room_id,))]
    for member in room['members']:
        member['you'] = member['id'] == session['uid']
        member['is_host'] = member['id'] == host_id
        # Member IDs are room-scoped opaque values, never session credentials.
        member['member_id'] = hashlib.sha256((room_id+member.pop('id')).encode()).hexdigest()[:20]
        age=max(0,now-member.pop('seen'))
        available=bool(member.pop('presence_active'))
        member['status']='inactive' if not available or age>=8 else 'reconnecting' if age>=2.5 else 'active'
        member['active']=member['status']!='inactive'
    room['participants']=room['members']
    room['members']=[member for member in room['participants'] if member['active']]
    after=None
    if request.method=='GET' and 'after' in request.args:
        try:
            after=int(request.args['after'])
            if not 0<=after<=9223372036854775807:raise ValueError()
        except (ValueError,TypeError):return jsonify(error='Invalid chat cursor.'),400
    if request.args.get('generation') and request.args['generation']!=room['storage_generation']:after=None
    room['messages_delta']=after is not None
    query='SELECT m.id,m.name,m.body,m.created,m.sender,r.id AS reply_id,r.name AS reply_name,r.body AS reply_body FROM messages m LEFT JOIN messages r ON r.room=m.room AND r.id=m.reply_to WHERE m.room=?'
    if after is not None:query+=' AND m.id>?'
    room['messages'] = list(reversed([dict(x) for x in db().execute(query+' ORDER BY m.id DESC LIMIT 100',(room_id,after) if after is not None else (room_id,))]))
    for message in room['messages']:
        sender=message.pop('sender')
        message['you']=sender==session['uid']
        message['is_host']=sender==host_id
        reply_id=message.pop('reply_id');reply_name=message.pop('reply_name');reply_body=message.pop('reply_body')
        message['reply']={'id':reply_id,'name':reply_name,'body':reply_body[:160]} if reply_id else None
        message['sender_id']=hashlib.sha256((room_id+(sender or message['name'])).encode()).hexdigest()[:16]
    room['typing'] = [row['name'] for row in db().execute('SELECT members.name FROM typing JOIN members ON typing.room=members.room AND typing.id=members.id WHERE typing.room=? AND typing.id<>? AND typing.updated>? AND members.seen>?',(room_id,session['uid'],now-4,now-20))]
    room['queue'] = [dict(x) for x in db().execute('SELECT * FROM queue WHERE room=? ORDER BY sort_order,id',(room_id,))]
    return jsonify(room)

@app.post('/api/rooms/<room_id>/telemetry')
def room_telemetry(room_id):
    if not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone():return jsonify(error='Join the room first.'),403
    data=request.get_json(silent=True) or {}
    name=data.get('name');value=data.get('value',1)
    if name not in ('playback_drift_ms','reconnect','stale_snapshot') or type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=600000:
        return jsonify(error='Invalid metric.'),400
    reliability_record(name,value)
    db().execute('DELETE FROM reliability_metrics WHERE minute<?',(int(time.time()//60)-30*1440,));db().commit()
    return jsonify(ok=True)


@app.post('/api/rooms/<room_id>/presence')
def room_presence(room_id):
    if not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone():return jsonify(error='Join the room first.'),403
    active=bool((request.get_json(silent=True) or {}).get('active'))
    db().execute('INSERT INTO presence VALUES(?,?,?) ON CONFLICT(room,id) DO UPDATE SET active=excluded.active',(room_id,session['uid'],int(active)))
    if active:db().execute('UPDATE members SET seen=? WHERE room=? AND id=?',(time.time(),room_id,session['uid']))
    else:db().execute('DELETE FROM typing WHERE room=? AND id=?',(room_id,session['uid']))
    db().commit()
    return jsonify(ok=True)


@app.post('/api/rooms/<room_id>/diagnostics')
def client_diagnostics(room_id):
    member=db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone()
    if not member:return jsonify(error='Join the room first.'),403
    room=db().execute('SELECT host,playing,playback_revision FROM rooms WHERE id=?',(room_id,)).fetchone()
    if not room:return jsonify(error='Room not found.'),404
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or len(request.data)>8192:return jsonify(error='Invalid diagnostics.'),400
    saved=app.extensions['solace_ops']['record_client'](room_id,'host' if room['host']==session['uid'] else 'peer',data,{'server_playing':bool(room['playing']),'playback_revision':room['playback_revision']})
    return jsonify(ok=True,saved=saved),202


@app.post('/api/rooms/<room_id>/leave')
def leave_room(room_id):
    db().execute('BEGIN IMMEDIATE')
    if not db().execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():
        db().rollback()
        return jsonify(ok=True,room_deleted=True)
    member=db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone()
    if not member:
        db().rollback()
        return jsonify(ok=True,room_deleted=False)
    for table in ('members','presence','typing','participant_ads'):
        db().execute(f'DELETE FROM {table} WHERE room=? AND id=?',(room_id,session['uid']))
    game=db().execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
    if game and session['uid'] in json.loads(game['state'])['players'].values():db().execute('DELETE FROM room_games WHERE room=?',(room_id,))
    empty=not db().execute('SELECT 1 FROM members WHERE room=? LIMIT 1',(room_id,)).fetchone()
    if empty:delete_room_records(room_id)
    else:
        room=db().execute('SELECT host FROM rooms WHERE id=?',(room_id,)).fetchone()
        if room and room['host']==session['uid']:
            successor=db().execute('SELECT id FROM members WHERE room=? ORDER BY seen DESC LIMIT 1',(room_id,)).fetchone()
            db().execute('UPDATE rooms SET host=? WHERE id=?',(successor['id'],room_id))
            db().execute('DELETE FROM room_ads WHERE room=?',(room_id,))
    db().commit()
    return jsonify(ok=True,room_deleted=empty)

def reliability_snapshot():
    rows=db().execute('SELECT name,SUM(count) AS samples,SUM(total) AS total,MAX(maximum) AS maximum FROM reliability_metrics WHERE minute>=? GROUP BY name',(int(time.time()//60)-60,)).fetchall()
    return [dict(row) for row in rows]

app.extensions['solace_reliability']=reliability_snapshot

@app.after_request
def reliability_response(response):
    if request.path.startswith('/api/rooms/') and response.status_code==409:
        try:
            db().rollback();reliability_record('command_conflict');db().commit()
        except sqlite3.Error:pass
    return response

@app.errorhandler(sqlite3.OperationalError)
def storage_unavailable(error):
    if 'locked' in str(error).lower() or 'busy' in str(error).lower():
        db().rollback()
        response=jsonify(error='The room is busy. Please retry.',code='storage_busy')
        response.status_code=503;response.headers['Retry-After']='1';return response
    app.logger.error('Room storage operation failed')
    return jsonify(error='Room storage is unavailable.',code='storage_unavailable'),503

from room_game import register_game
register_game(app,db)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), debug=False)
