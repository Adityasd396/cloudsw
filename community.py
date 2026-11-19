"""Shared community chat using existing identities, media validation and safety."""
import hashlib,json,re,secrets,time
from flask import abort,g,jsonify,request,session

WORLD='community'

def register_world(app,db,limited):
    ready=set();cleaned={}
    def initialize():
        if app.instance_path in ready:return
        db().executescript('''BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS user_preferences(owner TEXT PRIMARY KEY,world_choice TEXT NOT NULL DEFAULT 'unset',world_visible INTEGER NOT NULL DEFAULT 1,haptics INTEGER NOT NULL DEFAULT 1,rhythm INTEGER NOT NULL DEFAULT 0,rotation INTEGER NOT NULL DEFAULT 1,theme TEXT NOT NULL DEFAULT 'solace',experience_saved INTEGER NOT NULL DEFAULT 0,world_intro_seen INTEGER NOT NULL DEFAULT 0,in_app_alerts INTEGER NOT NULL DEFAULT 1,bpm INTEGER NOT NULL DEFAULT 90);
        CREATE TABLE IF NOT EXISTS world_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL,media_id TEXT,deleted INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS world_sender ON world_messages(sender);
        CREATE INDEX IF NOT EXISTS world_time ON world_messages(created);
        CREATE TABLE IF NOT EXISTS world_receipts(sender TEXT NOT NULL,request_id TEXT NOT NULL,digest TEXT NOT NULL,message INTEGER NOT NULL,created REAL NOT NULL,PRIMARY KEY(sender,request_id));
        CREATE TABLE IF NOT EXISTS world_presence(owner TEXT NOT NULL,tab TEXT NOT NULL,auth TEXT NOT NULL,expires REAL NOT NULL,PRIMARY KEY(owner,tab));
        CREATE INDEX IF NOT EXISTS world_expiry ON world_presence(expires,owner);
        CREATE TABLE IF NOT EXISTS world_state(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL DEFAULT 0);
        INSERT OR IGNORE INTO world_state VALUES(1,0);
        INSERT OR IGNORE INTO launch_migrations VALUES(8,strftime('%s','now'));COMMIT;''')
        if 'experience_saved' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:
            db().execute('BEGIN IMMEDIATE')
            if 'experience_saved' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:db().execute('ALTER TABLE user_preferences ADD COLUMN experience_saved INTEGER NOT NULL DEFAULT 0')
            db().commit()
        if 'world_intro_seen' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:
            db().execute('BEGIN IMMEDIATE')
            if 'world_intro_seen' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:db().execute('ALTER TABLE user_preferences ADD COLUMN world_intro_seen INTEGER NOT NULL DEFAULT 0')
            db().commit()
        if 'in_app_alerts' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:
            db().execute('BEGIN IMMEDIATE')
            if 'in_app_alerts' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:db().execute('ALTER TABLE user_preferences ADD COLUMN in_app_alerts INTEGER NOT NULL DEFAULT 1')
            db().commit()
        if 'bpm' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:
            db().execute('BEGIN IMMEDIATE')
            if 'bpm' not in {r['name'] for r in db().execute('PRAGMA table_info(user_preferences)')}:db().execute('ALTER TABLE user_preferences ADD COLUMN bpm INTEGER NOT NULL DEFAULT 90')
            db().commit()
        ready.add(app.instance_path)
    def prefs(owner):
        row=db().execute('SELECT * FROM user_preferences WHERE owner=?',(owner,)).fetchone()
        return dict(row) if row else dict(owner=owner,world_choice='unset',world_visible=1,haptics=1,rhythm=0,rotation=1,theme='solace',experience_saved=0,world_intro_seen=0,in_app_alerts=1,bpm=90)
    def access(write=False):
        uid=app.extensions['solace_social']['named']()['id'];safety=app.extensions['solace_safety']
        if safety['restricted'](uid,'discovery') or safety['paused']('discovery'):abort(403,description='Open World is temporarily unavailable.')
        if safety['paused']('guest_access') and not g.account:abort(403,description='Sign in to use Open World while guest access is paused.')
        if write:
            if prefs(uid)['world_choice']!='joined':abort(403,description='Join the community before sending a message.')
            if safety['restricted'](uid,'messaging') or safety['paused']('messaging'):abort(403,description='Sending messages is temporarily paused.')
        return uid
    def bump():db().execute('UPDATE world_state SET revision=revision+1 WHERE id=1')
    def cleanup():
        if time.time()-cleaned.get(app.instance_path,0)<60:return
        db().execute('BEGIN IMMEDIATE');cutoff=time.time()-30*86400
        ids=[r[0] for r in db().execute('SELECT id FROM world_messages WHERE created<? OR id<COALESCE((SELECT id FROM world_messages ORDER BY id DESC LIMIT 1 OFFSET 9999),0)',(cutoff,))]
        if ids:
            # The chat window is bounded; evidence captured for reports is independent.
            for offset in range(0,len(ids),500):
                batch=ids[offset:offset+500];marks=','.join('?' for _ in batch)
                db().execute("DELETE FROM chat_media WHERE scope='world' AND message IN ("+marks+')',batch);db().execute('DELETE FROM world_messages WHERE id IN ('+marks+')',batch)
            bump()
        db().execute('DELETE FROM world_receipts WHERE created<?',(cutoff,));db().execute('DELETE FROM world_receipts WHERE rowid IN (SELECT rowid FROM world_receipts ORDER BY created DESC LIMIT -1 OFFSET 100000)');db().execute('DELETE FROM world_presence WHERE expires<?',(time.time(),));db().commit();cleaned[app.instance_path]=time.time()
    def online(uid):
        if app.extensions['solace_safety']['paused']('discovery'):return 0
        return db().execute('''SELECT COUNT(DISTINCT w.owner) FROM world_presence w JOIN user_preferences p ON p.owner=w.owner WHERE p.world_choice='joined' AND p.world_visible=1 AND w.expires>?
        AND (w.auth='' OR EXISTS(SELECT 1 FROM account_sessions a WHERE a.owner=w.owner AND a.token=w.auth AND a.expires>?))
        AND NOT EXISTS(SELECT 1 FROM safety_restrictions r WHERE r.owner=w.owner AND r.revoked=0 AND r.kind<>'warn' AND r.feature IN ('all','discovery') AND (r.expires IS NULL OR r.expires>?))
        AND NOT EXISTS(SELECT 1 FROM blocks b WHERE (b.owner=? AND b.target=w.owner) OR (b.target=? AND b.owner=w.owner))
        AND (?=0 OR EXISTS(SELECT 1 FROM accounts a WHERE a.id=w.owner))''',(time.time(),time.time(),time.time(),uid,uid,int(bool(app.extensions['solace_safety']['paused']('guest_access'))))).fetchone()[0]
    def serialize(row,uid):
        social=app.extensions['solace_social'];person=social['person'](row['sender']);profile=app.extensions['solace_people']['card'](row['sender'],uid) if person else None
        result=dict(id=row['id'],body='' if row['deleted'] else row['body'],created=row['created'],deleted=bool(row['deleted']),you=row['sender']==uid,name=person['name'] if person else 'Former participant',code=profile['code'] if profile else None,avatar=profile['avatar'] if profile else '/static/default-avatar.svg')
        if row['media_id'] and not row['deleted']:
            media=db().execute('SELECT id,owner,width,height,animated,deleted FROM chat_media WHERE id=?',(row['media_id'],)).fetchone()
            if media:result['media']=app.extensions['solace_messaging']['media_info'](media)
        return result
    @app.route('/api/me/preferences',methods=['GET','POST'])
    def preferences():
        uid=app.extensions['solace_social']['named']()['id'];app.extensions['solace_social']['social_profile'](uid);db().commit()
        if request.method=='POST':
            d=request.get_json(silent=True)
            if not isinstance(d,dict) or set(d)-{'world_choice','world_visible','in_app_alerts','haptics','rhythm','rotation','theme','bpm'}:abort(400)
            if any(type(d[k]) is not bool for k in ['world_visible','in_app_alerts','haptics','rhythm','rotation'] if k in d) or ('world_choice' in d and d['world_choice'] not in ['joined','skipped']) or ('theme' in d and d['theme'] not in ['solace','rose','ocean','forest']):abort(400)
            if 'bpm' in d and (type(d['bpm']) is not int or not 60<=d['bpm']<=160):abort(400)
            if limited('preferences:'+uid,40,60):abort(429)
            if d.get('world_choice')=='joined':access(False)
            db().execute('BEGIN IMMEDIATE');db().execute('INSERT OR IGNORE INTO user_preferences(owner) VALUES(?)',(uid,))
            for key,value in d.items():db().execute('UPDATE user_preferences SET '+key+'=? WHERE owner=?',(value,uid))
            if any(k in d for k in ('haptics','rhythm','rotation','theme','bpm')):db().execute('UPDATE user_preferences SET experience_saved=1 WHERE owner=?',(uid,))
            if d.get('world_choice')=='skipped' or d.get('world_visible') is False:db().execute('DELETE FROM world_presence WHERE owner=?',(uid,))
            db().commit()
        return jsonify(preferences={k:v for k,v in prefs(uid).items() if k!='owner'})
    @app.post('/api/me/preferences/world-intro')
    def world_intro():
        uid=app.extensions['solace_social']['named']()['id']
        if limited('world-intro:'+uid,20,60):abort(429)
        db().execute('BEGIN IMMEDIATE');db().execute('INSERT OR IGNORE INTO user_preferences(owner) VALUES(?)',(uid,));old=prefs(uid)
        changed=db().execute("UPDATE user_preferences SET world_intro_seen=1,world_choice=CASE WHEN world_choice='unset' THEN 'skipped' ELSE world_choice END WHERE owner=? AND world_intro_seen=0",(uid,)).rowcount;db().commit()
        return jsonify(show_intro=bool(changed and old['world_choice']=='unset'),preferences={k:v for k,v in prefs(uid).items() if k!='owner'})
    @app.post('/api/me/world/presence')
    def world_presence():
        uid=app.extensions['solace_social']['named']()['id'];d={'tab':request.form.get('tab'),'active':False} if request.form.get('active')=='0' else request.get_json(silent=True)
        if not isinstance(d,dict) or not isinstance(d.get('tab'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',d['tab']) or type(d.get('active')) is not bool:abort(400)
        if limited('world-presence:'+uid,120,60):abort(429)
        active=d['active'] and prefs(uid)['world_choice']=='joined' and prefs(uid)['world_visible']
        if active:access(False)
        db().execute('BEGIN IMMEDIATE');db().execute('DELETE FROM world_presence WHERE expires<?',(time.time(),))
        if not active:db().execute('DELETE FROM world_presence WHERE owner=? AND tab=?',(uid,d['tab']))
        else:
            if db().execute('SELECT COUNT(*) FROM world_presence WHERE owner=? AND tab<>?',(uid,d['tab'])).fetchone()[0]>=8:db().commit();abort(429)
            auth=hashlib.sha256(request.cookies.get('solace_account','').encode()).hexdigest() if g.account else ''
            db().execute('INSERT INTO world_presence VALUES(?,?,?,?) ON CONFLICT(owner,tab) DO UPDATE SET auth=excluded.auth,expires=excluded.expires',(uid,d['tab'],auth,time.time()+32))
        db().commit();return jsonify(ok=True,online=online(uid))
    @app.route('/api/me/world/messages',methods=['GET','POST'])
    def world_messages():
        uid=access(request.method=='POST')
        if request.method=='POST' and not isinstance(request.get_json(silent=True),dict):abort(400)
        cleanup();message=app.extensions['solace_messaging']
        if request.method=='POST':
            if limited('world-send:'+uid,40,60) or limited('world-send-ip',180,60):abort(429)
            d,text,media,rid=message['body']()
            if not text and not media:abort(400,description='Write a message or attach a picture.')
            digest=hashlib.sha256((text+'\0'+str(media)).encode()).hexdigest();db().execute('BEGIN IMMEDIATE');old=db().execute('SELECT * FROM world_receipts WHERE sender=? AND request_id=?',(uid,rid)).fetchone()
            if old:
                if old['digest']!=digest:abort(409)
                row=db().execute('SELECT * FROM world_messages WHERE id=?',(old['message'],)).fetchone();db().commit()
                if not row:abort(410,description='This message is outside the retained chat window.')
                return jsonify(message=serialize(row,uid))
            quota=app.extensions['solace_user_storage']
            if quota['usage'](uid)+len(text.encode())+128>quota['limit'](uid):abort(413,description='Your storage limit is reached.')
            if media:message['staged_media'](media,'world',WORLD,uid)
            mid=db().execute('INSERT INTO world_messages(sender,body,created,media_id) VALUES(?,?,?,?)',(uid,text,time.time(),media)).lastrowid
            if media:db().execute('UPDATE chat_media SET message=?,uploaded=? WHERE id=?',(mid,time.time(),media))
            db().execute('INSERT INTO world_receipts VALUES(?,?,?,?,?)',(uid,rid,digest,mid,time.time()));db().commit();return jsonify(message=serialize(db().execute('SELECT * FROM world_messages WHERE id=?',(mid,)).fetchone(),uid)),201
        try:after=int(request.args.get('after','0'));before=int(request.args.get('before','0'))
        except ValueError:abort(400)
        if not 0<=after<2**63 or not 0<=before<2**63:abort(400)
        sql='SELECT m.* FROM world_messages m WHERE NOT EXISTS(SELECT 1 FROM blocks b WHERE (b.owner=? AND b.target=m.sender) OR (b.target=? AND b.owner=m.sender))';args=[uid,uid]
        if after:sql+=' AND m.id>?';args.append(after)
        if before:sql+=' AND m.id<?';args.append(before)
        rows=db().execute(sql+' ORDER BY m.id '+('ASC' if after else 'DESC')+' LIMIT 51',args).fetchall();has_more=len(rows)>50;rows=rows[:50]
        if not after:rows=list(reversed(rows))
        filtering=[tuple(r) for r in db().execute('SELECT owner,target FROM blocks WHERE owner=? OR target=? ORDER BY owner,target',(uid,uid))];revision=str(db().execute('SELECT revision FROM world_state WHERE id=1').fetchone()[0])+':'+hashlib.sha256(json.dumps(filtering).encode()).hexdigest()[:16]
        return jsonify(messages=[serialize(r,uid) for r in rows],has_more=has_more,online=online(uid),revision=revision,participation=prefs(uid)['world_choice'],can_send=prefs(uid)['world_choice']=='joined' and not app.extensions['solace_safety']['restricted'](uid,'messaging') and not app.extensions['solace_safety']['paused']('messaging'))
    @app.delete('/api/me/world/messages/<int:mid>')
    def world_remove(mid):
        uid=access();row=db().execute('SELECT * FROM world_messages WHERE id=? AND sender=?',(mid,uid)).fetchone()
        if not row:abort(404)
        db().execute('BEGIN IMMEDIATE');db().execute("UPDATE world_messages SET body='',deleted=1 WHERE id=?",(mid,))
        if row['media_id']:app.extensions['solace_messaging']['erase_media'](row['media_id'])
        bump();db().commit();return jsonify(ok=True)
    app.extensions['solace_world']=dict(initialize=initialize,access=access,prefs=prefs,bump=bump,online=online,cleanup=cleanup)
