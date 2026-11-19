"""Persisted guest profiles, consensual connections and room invitations."""
import hashlib,io,json,re,secrets,time
from urllib.parse import quote
from flask import abort,g,jsonify,redirect,render_template,request,send_file,session


def register_social(app,db,limited,csrf_valid):
    ready=set()
    alphabet='23456789ABCDEFGHJKMNPQRSTUVWXYZ'
    def friend_code():
        for _ in range(100):
            value=''.join(secrets.choice(alphabet) for _ in range(8))
            if not db().execute('SELECT 1 FROM social_profiles WHERE code=?',(value,)).fetchone():return value
        raise RuntimeError('Friend code allocation unavailable')
    def resolve(code):
        if not isinstance(code,str):return None
        legacy=re.sub(r'\s','',code).upper();code=re.sub(r'[\s-]','',code).upper()
        if not 4<=len(code)<=32:return None
        row=db().execute('SELECT owner FROM social_profiles WHERE code=? UNION ALL SELECT owner FROM friend_code_aliases WHERE code=? LIMIT 1',(code,legacy)).fetchone()
        return row['owner'] if row else None
    def initialize():
        if app.instance_path in ready:return
        db().executescript('''BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS friend_code_aliases(code TEXT PRIMARY KEY,owner TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS guest_data(owner TEXT PRIMARY KEY,avatar BLOB,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS social_profiles(owner TEXT PRIMARY KEY,code TEXT NOT NULL UNIQUE,share_presence INTEGER NOT NULL DEFAULT 0,share_stats INTEGER NOT NULL DEFAULT 0,share_avatar INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS identity_activity(owner TEXT PRIMARY KEY,last REAL NOT NULL,active INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS native_handoffs(token TEXT PRIMARY KEY,owner TEXT NOT NULL,expires REAL NOT NULL,source_session TEXT);
        CREATE TABLE IF NOT EXISTS connections(sender TEXT NOT NULL,target TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(sender,target));
        CREATE INDEX IF NOT EXISTS connection_target ON connections(target,status);
        CREATE TABLE IF NOT EXISTS connection_cooldowns(sender TEXT NOT NULL,target TEXT NOT NULL,until REAL NOT NULL,PRIMARY KEY(sender,target));
        CREATE TABLE IF NOT EXISTS blocks(owner TEXT NOT NULL,target TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(owner,target));
        CREATE INDEX IF NOT EXISTS block_target ON blocks(target,owner);
        CREATE TABLE IF NOT EXISTS room_settings(room TEXT PRIMARY KEY REFERENCES rooms(id) ON DELETE CASCADE,public_id TEXT NOT NULL UNIQUE,visibility TEXT NOT NULL DEFAULT 'private',label TEXT NOT NULL DEFAULT 'General',capacity INTEGER NOT NULL DEFAULT 20,epoch INTEGER NOT NULL DEFAULT 1,link_hash TEXT,link_token TEXT,listed REAL NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS public_room_listing ON room_settings(visibility,listed);
        CREATE TABLE IF NOT EXISTS room_bans(room TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,person TEXT NOT NULL,name TEXT NOT NULL,PRIMARY KEY(room,person));
        CREATE TABLE IF NOT EXISTS room_invitations(id TEXT PRIMARY KEY,room TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,sender TEXT NOT NULL,target TEXT NOT NULL,epoch INTEGER NOT NULL,created REAL NOT NULL,expires REAL NOT NULL,status TEXT NOT NULL DEFAULT 'pending',UNIQUE(room,sender,target));
        CREATE INDEX IF NOT EXISTS invitation_target ON room_invitations(target,status,expires);
        INSERT OR IGNORE INTO launch_migrations VALUES(4,strftime('%s','now'));
        COMMIT;''')
        for item in db().execute('SELECT owner,code FROM social_profiles').fetchall():
            if len(item['code'])!=8 or any(c not in alphabet for c in item['code']):
                db().execute('INSERT OR IGNORE INTO friend_code_aliases VALUES(?,?)',(item['code'].upper(),item['owner']))
                db().execute('UPDATE social_profiles SET code=? WHERE owner=?',(friend_code(),item['owner']))
        db().commit()
        # Existing rooms remain private. No private source/title is copied into discovery.
        for row in db().execute('SELECT id FROM rooms WHERE id NOT IN (SELECT room FROM room_settings)').fetchall():
            db().execute('INSERT OR IGNORE INTO room_settings(room,public_id) VALUES(?,?)',(row['id'],secrets.token_urlsafe(16)))
        db().commit();ready.add(app.instance_path)

    def person(owner):
        row=db().execute('SELECT id,name,email,created,verified,avatar IS NOT NULL AS avatar FROM accounts WHERE id=?',(owner,)).fetchone()
        if row:return {**dict(row),'guest':False}
        row=db().execute('''SELECT profiles.id,profiles.name,COALESCE(guest_data.created,profiles.updated) AS created,guest_data.avatar IS NOT NULL AS avatar
            FROM profiles LEFT JOIN guest_data ON guest_data.owner=profiles.id WHERE profiles.id=?''',(owner,)).fetchone()
        return {**dict(row),'guest':True,'email':'','verified':False} if row else None

    def named():
        profile=person(session['uid'])
        if not profile:abort(401,description='Save your guest name or sign in first.')
        return profile

    @app.post('/api/me/native-handoff')
    def native_handoff():
        named()
        if limited('native-handoff',30,60):return jsonify(error='Please wait before reconnecting.'),429
        token=secrets.token_urlsafe(40);source=hashlib.sha256(request.cookies.get('solace_account','').encode()).hexdigest() if g.account else None
        db().execute('DELETE FROM native_handoffs WHERE expires<?',(time.time(),))
        db().execute('INSERT INTO native_handoffs VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),session['uid'],time.time()+30,source));db().commit()
        return jsonify(token=token)

    @app.post('/api/native/handoff')
    def consume_native_handoff():
        data=request.get_json(silent=True) or {};token=data.get('token')
        if not isinstance(token,str) or not 40<=len(token)<=100:return jsonify(error='Invalid identity handoff.'),400
        if limited('native-handoff-consume',40,60):return jsonify(error='Please wait before reconnecting.'),429
        db().execute('BEGIN IMMEDIATE')
        row=db().execute('DELETE FROM native_handoffs WHERE token=? RETURNING *',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row or row['expires']<time.time() or not person(row['owner']):db().commit();return jsonify(error='Identity handoff expired. Reopen your home screen.'),401
        if row['source_session']:
            valid=db().execute('SELECT 1 FROM account_sessions WHERE token=? AND owner=? AND expires>?',(row['source_session'],row['owner'],time.time())).fetchone()
            account=db().execute('SELECT * FROM accounts WHERE id=?',(row['owner'],)).fetchone()
            if not valid or not account:db().commit();return jsonify(error='Sign in again to continue.'),401
            return app.extensions['solace_launch']['issue'](account,False)
        if db().execute('SELECT 1 FROM accounts WHERE id=?',(row['owner'],)).fetchone():db().commit();return jsonify(error='Reopen your signed-in home screen.'),401
        if session['uid']!=row['owner']:app.extensions['solace_launch']['leave_identity'](session['uid'])
        db().execute('DELETE FROM account_sessions WHERE token=?',(hashlib.sha256(request.cookies.get('solace_account','').encode()).hexdigest(),))
        db().commit();session['uid']=row['owner'];session.pop('account_uid',None);session['account_csrf']=secrets.token_urlsafe(32)
        response=jsonify(ok=True);response.delete_cookie('solace_account',httponly=True,samesite='Lax');return response

    @app.before_request
    def social_inputs():
        path=request.path
        if request.method!='POST' or not (path.startswith('/api/me/') or path=='/api/native/handoff' or path.endswith(('/settings','/moderation'))):return
        data=request.get_json(silent=True)
        if not isinstance(data,dict):return
        if path.startswith('/api/me/') and path not in ['/api/me/connections','/api/me/invitations','/api/me/invites/link','/api/me/rooms/public']:return
        for key in ['action','code','room','token','member_id','id','name','visibility','label','public_id']:
            if key in data and (not isinstance(data[key],str) or len(data[key])>200):return jsonify(error='Enter valid text fields.'),400

    def social_profile(owner):
        row=db().execute('SELECT * FROM social_profiles WHERE owner=?',(owner,)).fetchone()
        if row:return dict(row)
        for _ in range(100):
            db().execute('INSERT OR IGNORE INTO social_profiles(owner,code) VALUES(?,?)',(owner,friend_code()))
            row=db().execute('SELECT * FROM social_profiles WHERE owner=?',(owner,)).fetchone()
            if row:return dict(row)
        raise RuntimeError('Friend code allocation unavailable')

    def blocked(a,b):return bool(db().execute('SELECT 1 FROM blocks WHERE (owner=? AND target=?) OR (owner=? AND target=?)',(a,b,b,a)).fetchone())
    def friends(a,b):return bool(db().execute("SELECT 1 FROM connections WHERE status='accepted' AND ((sender=? AND target=?) OR (sender=? AND target=?))",(a,b,b,a)).fetchone())
    def stats(owner):
        row=db().execute('SELECT COUNT(*) AS sessions,COALESCE(SUM(seconds),0) AS seconds,MAX(last) AS last FROM watch_history WHERE owner=?',(owner,)).fetchone()
        return dict(row)

    def card(owner,viewer,accepted=False):
        p=person(owner)
        if not p or blocked(owner,viewer):return None
        s=social_profile(owner);result={'code':s['code'],'name':p['name'],'avatar':'/api/me/people/'+s['code']+'/avatar' if accepted and s['share_avatar'] and p['avatar'] else '/static/default-avatar.svg','online':None,'stats':None}
        if accepted and s['share_presence']:
            a=db().execute('SELECT * FROM identity_activity WHERE owner=?',(owner,)).fetchone();result['online']=bool(a and a['active'] and a['last']>time.time()-35) or bool(db().execute('SELECT 1 FROM members m LEFT JOIN presence p ON p.room=m.room AND p.id=m.id WHERE m.id=? AND m.seen>? AND COALESCE(p.active,1)=1 LIMIT 1',(owner,time.time()-3)).fetchone())
        if accepted and s['share_stats']:
            values=stats(owner);result['stats']={'sessions':values['sessions'],'seconds':values['seconds']}
        return result

    def metadata(room):
        row=db().execute('SELECT * FROM room_settings WHERE room=?',(room,)).fetchone()
        return dict(row) if row else None

    def create_settings(room,data):
        visibility=data.get('visibility','private');label=data.get('label','General');capacity=data.get('capacity',20)
        if visibility not in ('private','public') or label not in ('General','Music','Film & TV','Gaming') or type(capacity) is not int or not 2<=capacity<=100:return 'Choose valid room visibility, content label and capacity (2–100).'
        if visibility=='public' and data.get('confirm_public') is not True:return 'Confirm that this room will be discoverable.'
        token=secrets.token_urlsafe(32)
        db().execute('INSERT INTO room_settings(room,public_id,visibility,label,capacity,listed,link_token,link_hash) VALUES(?,?,?,?,?,?,?,?)',(room,secrets.token_urlsafe(16),visibility,label,capacity,time.time(),token,hashlib.sha256(token.encode()).hexdigest()))

    def join_guard(room,data,check_grant=True):
        owner=session['uid'];rid=room['id'];m=metadata(rid)
        if not m:return None
        if db().execute('SELECT 1 FROM room_bans WHERE room=? AND person=?',(rid,owner)).fetchone():return 'You cannot join this room.',403
        if any(blocked(owner,row['id']) for row in db().execute('SELECT id FROM members WHERE room=? AND id<>?',(rid,owner))):return 'This room is unavailable because of a block.',403
        existing=db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(rid,owner)).fetchone()
        if not existing and db().execute('SELECT count(*) FROM members WHERE room=?',(rid,)).fetchone()[0]>=m['capacity']:return 'This room is full. Try again when a place is free.',409
        grant=session.get('pending_room')
        if check_grant and grant and grant.get('room')==rid and not existing:
            if grant.get('epoch')!=m['epoch']:return 'This invitation was revoked. Ask for a new one.',410
            if grant.get('expires',0)<time.time():return 'This invitation expired. Ask for a new one.',410
        profile=person(owner)
        if not profile:
            name=str(data.get('name','')).strip()
            if not 1<=len(name)<=24 or any(ord(c)<32 for c in name):return 'Save a display name before joining.',400
        return None

    def member(room,host=False):
        row=db().execute('SELECT * FROM rooms WHERE id=?',(room,)).fetchone()
        if not row:abort(404,description='This room has closed.')
        if not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room,session['uid'])).fetchone():abort(403)
        if host and row['host']!=session['uid']:abort(403)
        return row

    def remove_member(room,owner):
        from app import prune_participant_games,delete_room_records
        for table in ('members','presence','typing','participant_ads'):db().execute('DELETE FROM '+table+' WHERE room=? AND id=?',(room,owner))
        prune_participant_games(room,owner)
        successor=db().execute('SELECT id FROM members WHERE room=? ORDER BY seen DESC LIMIT 1',(room,)).fetchone()
        if not successor:delete_room_records(room)
        else:db().execute('UPDATE rooms SET host=? WHERE id=? AND host=?',(successor['id'],room,owner))

    @app.get('/friends')
    @app.get('/rooms')
    @app.get('/home')
    @app.get('/welcome')
    def home_page():
        p=person(session['uid'])
        if request.path!='/welcome' and not p:return redirect('/welcome',303)
        if request.path=='/welcome' and p:return redirect('/home',303)
        return render_template('home.html',person=p,welcome=not bool(p),section=request.path.strip('/'))

    @app.get('/invite')
    def invite_page():return render_template('home.html',person=person(session['uid']),welcome=False,invite_landing=True)

    @app.get('/room-control')
    def room_control_page():
        room=request.args.get('room','');member(room)
        return render_template('room-control.html',room=room)

    @app.get('/api/me/dashboard')
    def dashboard():
        p=named();owner=session['uid'];settings=social_profile(owner)
        recent=[]
        for row in db().execute('SELECT id,title,video,started,seconds FROM watch_history WHERE owner=? ORDER BY started DESC LIMIT 4',(owner,)):
            recent.append({**dict(row),'people':[r['name'] for r in db().execute('SELECT name FROM watch_people WHERE entry=?',(row['id'],))]})
        p.pop('id',None);p.pop('email',None);db().commit();return jsonify(profile=p,stats=stats(owner),recent=recent,privacy={k:bool(settings[k]) for k in ['share_presence','share_stats','share_avatar','share_read']},friend_code=settings['code'],guest=p['guest'])

    @app.post('/api/me/activity')
    def activity():
        named();active=(request.get_json(silent=True) or {}).get('active') is True or request.form.get('active')=='1';now=time.time()
        db().execute('INSERT INTO identity_activity VALUES(?,?,?) ON CONFLICT(owner) DO UPDATE SET last=excluded.last,active=excluded.active',(session['uid'],now,int(active)));db().commit();return jsonify(ok=True)

    @app.route('/api/me/privacy',methods=['GET','POST'])
    def privacy_settings():
        named();s=social_profile(session['uid'])
        if request.method=='POST':
            data=request.get_json(silent=True) or {}
            if set(data)-{'share_presence','share_stats','share_avatar','share_read'} or any(type(v) is not bool for v in data.values()):return jsonify(error='Choose on or off for each privacy option.'),400
            for key,value in data.items():db().execute('UPDATE social_profiles SET '+key+'=? WHERE owner=?',(int(value),session['uid']))
            s=social_profile(session['uid'])
        db().commit();return jsonify(**{k:bool(s[k]) for k in ['share_presence','share_stats','share_avatar','share_read']})

    def block_person(owner,other):
        db().execute('INSERT OR IGNORE INTO blocks VALUES(?,?,?)',(owner,other,time.time()))
        db().execute('DELETE FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(owner,other,other,owner))
        db().execute("UPDATE room_invitations SET status='declined' WHERE (sender=? AND target=?) OR (sender=? AND target=?)",(owner,other,other,owner))
        shared=db().execute('SELECT a.room,r.host FROM members a JOIN members b ON a.room=b.room JOIN rooms r ON r.id=a.room WHERE a.id=? AND b.id=?',(owner,other)).fetchall()
        for row in shared:
            if row['host']==owner:
                db().execute('INSERT OR IGNORE INTO room_bans VALUES(?,?,?)',(row['room'],other,person(other)['name']));remove_member(row['room'],other)
            else:remove_member(row['room'],owner)

    @app.route('/api/me/connections',methods=['GET','POST'])
    def connections():
        named();owner=session['uid']
        if request.method=='POST':
            if limited('connections:'+owner,30,600):return jsonify(error='Please wait before sending more connection actions.'),429
            data=request.get_json(silent=True) or {};action=data.get('action');code=data.get('code')
            resolved=resolve(code);target={'owner':resolved} if resolved else None
            if target and target['owner']==owner:return jsonify(error='That is your own friend code.'),400
            if not target or not person(target['owner']):return jsonify(error='That friend code is unavailable.'),404
            other=target['owner'];db().execute('BEGIN IMMEDIATE')
            if action=='block':
                block_person(owner,other)
            elif action=='unblock':db().execute('DELETE FROM blocks WHERE owner=? AND target=?',(owner,other))
            elif blocked(owner,other):db().rollback();return jsonify(error='This connection is unavailable.'),403
            elif action=='request':
                if db().execute('SELECT 1 FROM connection_cooldowns WHERE sender=? AND target=? AND until>?',(owner,other,time.time())).fetchone():db().rollback();return jsonify(error='This request was recently declined. Please wait before requesting again.'),429
                previous=db().execute('SELECT * FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(owner,other,other,owner)).fetchone()
                if previous and (previous['status']!='declined' or previous['created']>time.time()-60):db().rollback();return jsonify(error='A connection or request already exists, or was recently declined.'),409
                if previous:db().execute('DELETE FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(owner,other,other,owner))
                if any(db().execute('SELECT COUNT(*) FROM connections WHERE sender=? OR target=?',(p,p)).fetchone()[0]>=100 for p in (owner,other)):db().rollback();return jsonify(error='This circle has reached its connection limit. Remove an old request first.'),409
                db().execute("INSERT INTO connections VALUES(?,?,'pending',?)",(owner,other,time.time()))
            elif action=='accept':
                if db().execute("UPDATE connections SET status='accepted' WHERE sender=? AND target=? AND status='pending'",(other,owner)).rowcount!=1:db().rollback();return jsonify(error='This request is no longer available.'),409
            elif action=='decline':
                if db().execute("UPDATE connections SET status='declined',created=? WHERE sender=? AND target=? AND status='pending'",(time.time(),other,owner)).rowcount!=1:db().rollback();return jsonify(error='This request is no longer pending.'),409
                db().execute('INSERT INTO connection_cooldowns VALUES(?,?,?) ON CONFLICT(sender,target) DO UPDATE SET until=MAX(until,excluded.until)',(other,owner,time.time()+86400))
            elif action=='remove':
                db().execute('DELETE FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(owner,other,other,owner))
                db().execute("UPDATE room_invitations SET status='declined' WHERE (sender=? AND target=?) OR (sender=? AND target=?)",(owner,other,other,owner))
            else:db().rollback();return jsonify(error='Choose a valid connection action.'),400
            db().commit()
        mine=social_profile(owner);accepted=[];incoming=[];outgoing=[];declined=[]
        for row in db().execute('SELECT * FROM connections WHERE sender=? OR target=? ORDER BY created DESC LIMIT 100',(owner,owner)):
            other=row['target'] if row['sender']==owner else row['sender'];item=card(other,owner,row['status']=='accepted')
            if item:
                item['status']=row['status'];(declined if row['status']=='declined' else accepted if row['status']=='accepted' else incoming if row['target']==owner else outgoing).append(item)
        companions=[]
        for row in db().execute('''SELECT p.person,MAX(p.name) AS name,MAX(h.last) AS last FROM watch_people p JOIN watch_history h ON h.id=p.entry WHERE h.owner=? GROUP BY p.person ORDER BY last DESC LIMIT 12''',(owner,)):
            if friends(owner,row['person']):continue
            item=card(row['person'],owner)
            if item:item['name']=row['name'];companions.append(item)
        blocked_list=[]
        for row in db().execute('SELECT target FROM blocks WHERE owner=? LIMIT 50',(owner,)):
            p=person(row['target'])
            if p:blocked_list.append({'name':p['name'],'code':social_profile(row['target'])['code']})
        db().commit();return jsonify(declined=declined,friends=accepted,incoming=incoming,outgoing=outgoing,companions=companions,blocked=blocked_list,friend_code=mine['code'])

    @app.get('/api/me/people/<code>/avatar')
    def friend_avatar(code):
        named();other=resolve(code);row=db().execute('SELECT owner,share_avatar FROM social_profiles WHERE owner=?',(other,)).fetchone()
        if not row or not row['share_avatar'] or blocked(session['uid'],row['owner']) or not friends(session['uid'],row['owner']):abort(404)
        table='accounts' if db().execute('SELECT 1 FROM accounts WHERE id=?',(row['owner'],)).fetchone() else 'guest_data';column='id' if table=='accounts' else 'owner'
        picture=db().execute('SELECT avatar FROM '+table+' WHERE '+column+'=?',(row['owner'],)).fetchone()
        if not picture or not picture[0]:return redirect('/static/default-avatar.svg')
        return send_file(io.BytesIO(picture[0]),mimetype='image/png',max_age=0)

    @app.get('/api/public/rooms')
    def discovery():
        rows=db().execute('''SELECT r.id,r.name,r.host,s.public_id,s.label,s.capacity,COUNT(m.id) AS participants FROM room_settings s JOIN rooms r ON r.id=s.room JOIN members m ON m.room=r.id WHERE s.visibility='public' AND m.seen>? GROUP BY r.id ORDER BY s.listed DESC LIMIT 30''',(time.time()-30,)).fetchall()
        rooms=[]
        for row in rows:
            if blocked(session['uid'],row['host']) or db().execute('SELECT 1 FROM room_bans WHERE room=? AND person=?',(row['id'],session['uid'])).fetchone():continue
            rooms.append({k:row[k] for k in ['public_id','name','label','capacity','participants']})
        return jsonify(rooms=rooms)

    @app.post('/api/me/rooms/public')
    def join_public():
        named();data=request.get_json(silent=True) or {};row=db().execute("SELECT room,epoch FROM room_settings WHERE public_id=? AND visibility='public'",(data.get('public_id'),)).fetchone()
        if not row:return jsonify(error='This public room is no longer available.'),404
        session['pending_room']={'room':row['room'],'epoch':row['epoch'],'expires':time.time()+600};return jsonify(next='/join?room='+row['room'])

    @app.post('/api/me/invites/link')
    def redeem_link():
        if limited('invite-links',30,60):return jsonify(error='Please wait before trying another invitation.'),429
        data=request.get_json(silent=True) or {};token=data.get('token','')
        if not isinstance(token,str) or not 30<=len(token)<=100:return jsonify(error='This invitation is invalid or revoked.'),410
        row=db().execute('SELECT room,epoch FROM room_settings WHERE link_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row:return jsonify(error='This invitation is invalid or revoked.'),410
        session['pending_room']={'room':row['room'],'epoch':row['epoch'],'expires':time.time()+600};return jsonify(next='/join?room='+row['room'] if person(session['uid']) else '/welcome')

    @app.route('/api/rooms/<room>/settings',methods=['GET','POST'])
    def room_settings(room):
        r=member(room,request.method=='POST');s=metadata(room)
        if request.method=='POST':
            if not csrf_valid():abort(403)
            data=request.get_json(silent=True) or {};action=data.get('action');db().execute('BEGIN IMMEDIATE');r=member(room,True);s=metadata(room)
            if action in ('regenerate','revoke'):
                token=secrets.token_urlsafe(32) if action=='regenerate' else None
                db().execute('UPDATE room_settings SET epoch=epoch+1,link_hash=?,link_token=? WHERE room=?',(hashlib.sha256(token.encode()).hexdigest() if token else None,token,room))
                db().execute("UPDATE room_invitations SET status='revoked' WHERE room=? AND status='pending'",(room,))
            elif action=='update':
                visibility=data.get('visibility',s['visibility']);capacity=data.get('capacity',s['capacity']);label=data.get('label',s['label']);name=str(data.get('name',r['name'])).strip()
                if visibility not in ('public','private') or label not in ('General','Music','Film & TV','Gaming') or type(capacity) is not int or not 2<=capacity<=100 or not 1<=len(name)<=60:db().rollback();return jsonify(error='Enter valid room details.'),400
                if visibility=='public' and s['visibility']!='public' and data.get('confirm_public') is not True:db().rollback();return jsonify(error='Confirm that anyone can discover this room.'),400
                if capacity<db().execute('SELECT count(*) FROM members WHERE room=?',(room,)).fetchone()[0]:db().rollback();return jsonify(error='Capacity cannot be below the current member count.'),409
                db().execute('UPDATE room_settings SET visibility=?,capacity=?,label=?,listed=? WHERE room=?',(visibility,capacity,label,time.time(),room));db().execute('UPDATE rooms SET name=? WHERE id=?',(name,room))
            else:db().rollback();return jsonify(error='Choose a valid setting action.'),400
            db().commit();s=metadata(room);r=member(room)
        return jsonify(participants=[{'member_id':hashlib.sha256((room+p['id']).encode()).hexdigest()[:20],'name':p['name'],'you':p['id']==session['uid']} for p in db().execute('SELECT id,name FROM members WHERE room=?',(room,))] if r['host']==session['uid'] else [],bans=[{'member_id':hashlib.sha256((room+p['person']).encode()).hexdigest()[:20],'name':p['name']} for p in db().execute('SELECT person,name FROM room_bans WHERE room=?',(room,))] if r['host']==session['uid'] else [],name=r['name'],visibility=s['visibility'],capacity=s['capacity'],label=s['label'],is_host=r['host']==session['uid'],invite_link='/invite#token='+s['link_token'] if s['link_token'] else None,room=room)

    @app.post('/api/rooms/<room>/moderation')
    def moderation(room):
        r=member(room,True)
        if not csrf_valid():abort(403)
        data=request.get_json(silent=True) or {};action=data.get('action');token=data.get('member_id')
        targets=[dict(row) for row in db().execute('SELECT id,name FROM members WHERE room=?',(room,))]
        targets += [{'id':row['person'],'name':row['name']} for row in db().execute('SELECT * FROM room_bans WHERE room=?',(room,))]
        target=next((row for row in targets if hashlib.sha256((room+row['id']).encode()).hexdigest()[:20]==token),None)
        if not target or target['id']==session['uid']:return jsonify(error='Choose another participant.'),400
        if action not in ('ban','kick','unban'):return jsonify(error='Choose a moderation action.'),400
        db().execute('BEGIN IMMEDIATE');member(room,True)
        if action=='unban':db().execute('DELETE FROM room_bans WHERE room=? AND person=?',(room,target['id']))
        else:
            if action=='ban':db().execute('INSERT OR IGNORE INTO room_bans VALUES(?,?,?)',(room,target['id'],target['name']))
            remove_member(room,target['id'])
        db().commit();return jsonify(ok=True)

    @app.route('/api/me/invitations',methods=['GET','POST'])
    def invitations():
        named();owner=session['uid'];data=request.get_json(silent=True) or {}
        if request.method=='POST':
            if limited('invitations:'+owner,20,600):return jsonify(error='Please wait before sending more invitations.'),429
            action=data.get('action')
            db().execute('BEGIN IMMEDIATE')
            if action=='send':
                room=str(data.get('room',''));member(room);s=metadata(room);target_owner=resolve(data.get('code'));target={'owner':target_owner} if target_owner else None
                if not target or not friends(owner,target['owner']) or blocked(owner,target['owner']):return jsonify(error='Invite an accepted friend who has not blocked you.'),403
                if db().execute('SELECT 1 FROM room_bans WHERE room=? AND person=?',(room,target['owner'])).fetchone():return jsonify(error='This person cannot join this room.'),403
                if db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(room,target['owner'])).fetchone():return jsonify(ok=True,message='Already in the room.')
                old=db().execute('SELECT * FROM room_invitations WHERE room=? AND sender=? AND target=?',(room,owner,target['owner'])).fetchone()
                if old and old['status']=='pending' and old['expires']>time.time() and old['epoch']==s['epoch']:return jsonify(error='An invitation is already pending.'),409
                db().execute("INSERT INTO room_invitations VALUES(?,?,?,?,?,?,?,'pending') ON CONFLICT(room,sender,target) DO UPDATE SET id=excluded.id,epoch=excluded.epoch,created=excluded.created,expires=excluded.expires,status='pending'",(secrets.token_urlsafe(16),room,owner,target['owner'],s['epoch'],time.time(),time.time()+86400));db().commit()
            elif action in ('accept','decline'):
                row=db().execute('SELECT * FROM room_invitations WHERE id=? AND target=?',(data.get('id'),owner)).fetchone()
                if not row:return jsonify(error='This invitation is unavailable.'),404
                s=metadata(row['room'])
                if row['status']!='pending' or row['expires']<time.time() or not s or row['epoch']!=s['epoch']:return jsonify(error='This invitation expired, was revoked, or the room closed.'),410
                if blocked(owner,row['sender']) or not friends(owner,row['sender']):return jsonify(error='This invitation is unavailable.'),403
                if action=='accept':
                    room= db().execute('SELECT * FROM rooms WHERE id=?',(row['room'],)).fetchone();problem=join_guard(room,{},False)
                    if problem:return jsonify(error=problem[0]),problem[1]
                    session['pending_room']={'room':row['room'],'epoch':s['epoch'],'expires':time.time()+600}
                db().execute('UPDATE room_invitations SET status=? WHERE id=?',('accepted' if action=='accept' else 'declined',row['id']));db().commit()
                return jsonify(ok=True,next='/join?room='+row['room'] if action=='accept' else None)
            else:return jsonify(error='Choose an invitation action.'),400
        items=[]
        for row in db().execute("SELECT i.*,r.name,s.epoch AS current_epoch FROM room_invitations i LEFT JOIN rooms r ON r.id=i.room LEFT JOIN room_settings s ON s.room=i.room WHERE i.target=? ORDER BY i.created DESC LIMIT 30",(owner,)):
            if blocked(owner,row['sender']):continue
            inviter=person(row['sender']);status=row['status'] if row['name'] else 'closed'
            if status=='pending' and (row['expires']<time.time() or row['epoch']!=row['current_epoch']):status='expired'
            items.append({'id':row['id'],'name':row['name'] or 'Closed room','inviter':inviter['name'] if inviter else 'Former participant','status':status})
        return jsonify(ok=True,invitations=items)

    @app.post('/api/me/connections/preview')
    def preview_connection():
        named()
        if limited('friend-preview',30,60):return jsonify(error='Please wait before looking up another code.'),429
        uid=session['uid'];other=resolve((request.get_json(silent=True) or {}).get('code'))
        if other==uid:return jsonify(error='That is your own friend code.'),400
        if not other or blocked(uid,other) or not person(other):return jsonify(error='That friend code is unavailable.'),404
        relation=db().execute('SELECT status,sender FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(uid,other,other,uid)).fetchone()
        result=card(other,uid,friends(uid,other));result['status']=relation['status'] if relation else 'none';result['incoming']=bool(relation and relation['sender']==other)
        if not relation and db().execute('SELECT 1 FROM connection_cooldowns WHERE sender=? AND target=? AND until>?',(uid,other,time.time())).fetchone():result['status']='cooldown'
        db().commit();return jsonify(profile=result)

    def erase(owner):
        app.extensions['solace_messaging']['erase_owner'](owner)
        db().execute('DELETE FROM discovery_profiles WHERE owner=?',(owner,));db().execute('DELETE FROM discovery_leases WHERE owner=?',(owner,))
        db().execute('DELETE FROM friend_code_aliases WHERE owner=?',(owner,))
        db().execute('DELETE FROM connection_cooldowns WHERE sender=? OR target=?',(owner,owner))
        for table,column in [('guest_data','owner'),('social_profiles','owner'),('identity_activity','owner'),('native_handoffs','owner')]:db().execute('DELETE FROM '+table+' WHERE '+column+'=?',(owner,))
        for table,columns in [('connections',('sender','target')),('blocks',('owner','target')),('room_invitations',('sender','target'))]:db().execute('DELETE FROM '+table+' WHERE '+columns[0]+'=? OR '+columns[1]+'=?',(owner,owner))

    app.extensions['solace_social']={'initialize':initialize,'person':person,'named':named,'join_guard':join_guard,'create_settings':create_settings,'metadata':metadata,'erase':erase,'social_profile':social_profile,'resolve':resolve,'blocked':blocked,'friends':friends,'card':card,'block':block_person}
