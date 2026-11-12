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

app = Flask(__name__)
Path(app.instance_path).mkdir(exist_ok=True)
key_file = Path(app.instance_path) / 'secret'
if not key_file.exists():
    key_file.write_text(secrets.token_hex(32))
app.secret_key = os.environ.get('SECRET_KEY') or key_file.read_text()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=16384, PERMANENT_SESSION_LIFETIME=timedelta(days=365))


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
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

with app.app_context():
    db().executescript('''
    CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, name TEXT, host TEXT, video TEXT, playing INTEGER DEFAULT 0, position REAL DEFAULT 0, updated REAL);
    CREATE TABLE IF NOT EXISTS members(room TEXT, id TEXT, name TEXT, seen REAL, PRIMARY KEY(room,id));
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, name TEXT, body TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, video TEXT, title TEXT, added_by TEXT, sort_order INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL, updated REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS typing(room TEXT, id TEXT, updated REAL NOT NULL, PRIMARY KEY(room,id));
    CREATE TABLE IF NOT EXISTS presence(room TEXT, id TEXT, active INTEGER NOT NULL, PRIMARY KEY(room,id));
    CREATE INDEX IF NOT EXISTS message_room_idx ON messages(room,id);
    ''')
    if 'sort_order' not in {column['name'] for column in db().execute('PRAGMA table_info(queue)')}:
        db().execute('ALTER TABLE queue ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0')
        db().execute('UPDATE queue SET sort_order=id')
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


@app.get('/api/health')
def health():
    return jsonify(application='afterglow', protocol=1, status='ok')


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
        return jsonify(error='YouTube search has not been connected on this server. Ask the room owner to finish setup.', code='search_not_configured'),503
    if not query or not key:
        items = [item for item in FEATURED if (category == 'All' or item['category'] == category) and (not query or query.lower() in (item['title']+' '+item['channel']+' '+item['category']).lower())]
        return jsonify(items=items, source='featured', search_enabled=bool(key), notice='')
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

@app.post('/api/rooms')
def create_room():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', 'Late night lounge')).strip()[:60] or 'Late night lounge'
    for _ in range(20):
        room_id = str(secrets.randbelow(900000)+100000)
        try:
            db().execute('INSERT INTO rooms(id,name,host,video,updated) VALUES(?,?,?,?,?)', (room_id,name,session['uid'],'aqz-KE-bpKQ',time.time()))
            break
        except sqlite3.IntegrityError:
            continue
    else:
        return jsonify(error='Could not create a room right now. Please try again.'),503
    db().commit()
    return jsonify(id=room_id), 201

@app.route('/api/rooms/<room_id>', methods=['GET', 'POST'])
def room(room_id):
    room = db().execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        return jsonify(error='Room not found. Create a new room or check your invite link.'), 404
    now = time.time()
    data = request.get_json(silent=True) or {}
    if request.method == 'POST':
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
            if action == 'typing':
                if data.get('active'):
                    db().execute('INSERT INTO typing VALUES(?,?,?) ON CONFLICT(room,id) DO UPDATE SET updated=excluded.updated',(room_id,session['uid'],now))
                else:
                    db().execute('DELETE FROM typing WHERE room=? AND id=?',(room_id,session['uid']))
            elif action == 'chat':
                body = str(data.get('body', '')).strip()[:500]
                if not body:
                    return jsonify(error='Write a message first.'), 400
                recent = db().execute('SELECT created FROM messages WHERE room=? AND name=? ORDER BY id DESC LIMIT 1', (room_id,member['name'])).fetchone()
                if recent and now-recent['created'] < .5:
                    return jsonify(error='Please wait a moment before sending again.'), 429
                db().execute('INSERT INTO messages(room,name,body,created) VALUES(?,?,?,?)', (room_id,member['name'],body,now))
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
                if action == 'transfer_host' and room['host'] != session['uid']:
                    return jsonify(error='Only the host can control playback.'), 403
                if action == 'move':
                    direction = data.get('direction')
                    if direction not in ('up','down'):
                        return jsonify(error='Choose up or down.'),400
                    db().execute('BEGIN IMMEDIATE')
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
                elif action == 'watch':
                    video = video_id(data.get('url',''))
                    if not video:
                        return jsonify(error='Enter a valid YouTube video.'),400
                    db().execute('UPDATE rooms SET video=?,position=0,playing=1,updated=? WHERE id=?',(video,now,room_id))
                elif action == 'playback':
                    if 'expected_updated' in data:
                        db().execute('BEGIN IMMEDIATE')
                        latest=db().execute('SELECT updated FROM rooms WHERE id=?',(room_id,)).fetchone()
                        if data['expected_updated'] != latest['updated']:
                            return jsonify(error='Playback changed. Refreshing room state.',code='stale_playback'),409
                    try:
                        position = float(data.get('position',0))
                        if not math.isfinite(position):
                            raise ValueError()
                        position = max(0, min(position, 864000))
                    except (ValueError, TypeError):
                        return jsonify(error='Invalid playback position.'),400
                    db().execute('UPDATE rooms SET position=?,playing=?,updated=? WHERE id=?',(position,int(bool(data.get('playing'))),now,room_id))
                else:
                    item = db().execute('SELECT * FROM queue WHERE room=? ORDER BY sort_order,id LIMIT 1',(room_id,)).fetchone() if action == 'next' else db().execute('SELECT * FROM queue WHERE room=? AND id=?',(room_id,data.get('id'))).fetchone()
                    if item:
                        if action != 'remove':
                            db().execute('UPDATE rooms SET video=?,position=0,playing=1,updated=? WHERE id=?',(item['video'],now,room_id))
                        db().execute('DELETE FROM queue WHERE id=?',(item['id'],))
                    elif action != 'next':
                        return jsonify(error='That playlist item has already been removed.'),404
                    else:
                        db().execute('UPDATE rooms SET playing=0,updated=? WHERE id=?',(now,room_id))
            else:
                return jsonify(error='Unknown action.'),400
        db().commit()
    db().execute('UPDATE members SET seen=? WHERE room=? AND id=? AND seen<?',(now,room_id,session['uid'],now-1))
    db().commit()
    if request.method == 'POST' and data.get('action') == 'playback' and data.get('compact'):
        return jsonify(ok=True)
    room = dict(db().execute('SELECT * FROM rooms WHERE id=?',(room_id,)).fetchone())
    host_id = room.pop('host')
    room['is_host'] = host_id == session['uid']
    room['can_control'] = db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone() is not None
    host = db().execute('SELECT seen FROM members WHERE room=? AND id=?',(room_id,host_id)).fetchone()
    room['can_claim_host'] = not host or now-host['seen'] >= 30
    room['server_time'] = now
    room['members'] = [dict(x) for x in db().execute('SELECT members.name,members.id,members.seen,COALESCE(presence.active,1) AS presence_active FROM members LEFT JOIN presence ON members.room=presence.room AND members.id=presence.id WHERE members.room=? ORDER BY members.seen DESC LIMIT 100',(room_id,))]
    for member in room['members']:
        member['you'] = member['id'] == session['uid']
        member['is_host'] = member['id'] == host_id
        # Member IDs are room-scoped opaque values, never session credentials.
        member['member_id'] = hashlib.sha256((room_id+member.pop('id')).encode()).hexdigest()[:20]
        age=max(0,now-member.pop('seen'))
        available=bool(member.pop('presence_active'))
        member['status'] = 'inactive' if not available or age>=8 else 'reconnecting' if age>=2.5 else 'active'
        member['active'] = member['status'] != 'inactive'
    room['participants'] = room['members']
    room['members'] = [member for member in room['participants'] if member['active']]
    room['messages'] = list(reversed([dict(x) for x in db().execute('SELECT id,name,body,created FROM messages WHERE room=? ORDER BY id DESC LIMIT 100',(room_id,))]))
    room['typing'] = [row['name'] for row in db().execute('SELECT members.name FROM typing JOIN members ON typing.room=members.room AND typing.id=members.id WHERE typing.room=? AND typing.id<>? AND typing.updated>? AND members.seen>?',(room_id,session['uid'],now-4,now-20))]
    room['queue'] = [dict(x) for x in db().execute('SELECT * FROM queue WHERE room=? ORDER BY sort_order,id',(room_id,))]
    return jsonify(room)


@app.post('/api/rooms/<room_id>/presence')
def room_presence(room_id):
    member=db().execute('SELECT id FROM members WHERE room=? AND id=?',(room_id,session['uid'])).fetchone()
    if not member:
        return jsonify(error='Join the room first.'),403
    active=bool((request.get_json(silent=True) or {}).get('active'))
    db().execute('INSERT INTO presence VALUES(?,?,?) ON CONFLICT(room,id) DO UPDATE SET active=excluded.active',(room_id,session['uid'],int(active)))
    if active:db().execute('UPDATE members SET seen=? WHERE room=? AND id=?',(time.time(),room_id,session['uid']))
    else:db().execute('DELETE FROM typing WHERE room=? AND id=?',(room_id,session['uid']))
    db().commit()
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), debug=False)
