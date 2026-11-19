"""Platform safety: authorized evidence, named staff actions and durable controls."""
import hashlib,hmac,json,secrets,time
from flask import abort,g,jsonify,redirect,render_template,request,session

CATEGORIES={'harassment','abuse','hate','threats','sexual misconduct','impersonation','scams','spam'}
SWITCHES={'registrations','guest_access','discovery','room_creation','invitations','messaging','uploads'}
FEATURES={'all','discovery','messaging','uploads','invitations','room_creation','connections','games'}

def register_safety(app,db,limited):
    ready=set();last_clean={};social=app.extensions['solace_social'];ops=app.extensions['solace_ops'];staff=app.extensions['solace_staff']
    def payload():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):abort(400,description='Send a JSON object.')
        for key in ('id','code','kind','reference','category','action','feature','name','status','severity','assigned','reason','explanation','restriction','body'):
            if key in value and (not isinstance(value[key],str) or len(value[key])>2000):abort(400,description='Send valid bounded text fields.')
        return value
    def initialize():
        if app.instance_path in ready:return
        db().executescript('''BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS safety_guest_revocations(owner TEXT PRIMARY KEY,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS safety_switches(name TEXT PRIMARY KEY,paused INTEGER NOT NULL DEFAULT 0,reason TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS safety_restrictions(id TEXT PRIMARY KEY,owner TEXT NOT NULL,feature TEXT NOT NULL,kind TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL,expires REAL,revoked INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS restrictions_owner ON safety_restrictions(owner,revoked,expires);
        CREATE TABLE IF NOT EXISTS safety_reports(id TEXT PRIMARY KEY,reporter TEXT NOT NULL,target TEXT NOT NULL,kind TEXT NOT NULL,reference TEXT NOT NULL,category TEXT NOT NULL,explanation TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',severity TEXT NOT NULL DEFAULT 'normal',assigned TEXT NOT NULL DEFAULT '',created REAL NOT NULL,evidence TEXT,evidence_until REAL NOT NULL,resolution TEXT NOT NULL DEFAULT '',UNIQUE(reporter,kind,reference));
        CREATE INDEX IF NOT EXISTS reports_queue ON safety_reports(status,created);
        CREATE TABLE IF NOT EXISTS safety_notes(id INTEGER PRIMARY KEY,report TEXT NOT NULL,actor TEXT NOT NULL,note TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS safety_appeals(id TEXT PRIMARY KEY,owner TEXT NOT NULL,restriction TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',resolution TEXT NOT NULL DEFAULT '',created REAL NOT NULL,UNIQUE(owner,restriction));
        CREATE TABLE IF NOT EXISTS safety_audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL,reason TEXT NOT NULL,outcome TEXT NOT NULL,created REAL NOT NULL,previous TEXT NOT NULL,digest TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS safety_audit_no_update BEFORE UPDATE ON safety_audit BEGIN SELECT RAISE(ABORT,'append-only audit');END;
        CREATE TRIGGER IF NOT EXISTS safety_audit_no_delete BEFORE DELETE ON safety_audit BEGIN SELECT RAISE(ABORT,'append-only audit');END;
        INSERT OR IGNORE INTO launch_migrations VALUES(7,strftime('%s','now'));COMMIT;''')
        db().executemany('INSERT OR IGNORE INTO safety_switches(name) VALUES(?)',[(s,) for s in SWITCHES]);db().commit();ready.add(app.instance_path)
    def audit(actor,action,target,reason,outcome,commit=True):
        if not db().in_transaction:db().execute('BEGIN IMMEDIATE')
        previous=db().execute('SELECT digest FROM safety_audit ORDER BY id DESC LIMIT 1').fetchone();previous=previous[0] if previous else ''
        who=json.dumps(actor,sort_keys=True);now=time.time();values=[who,action,target,reason,outcome,now,previous];digest=hmac.new(str(app.secret_key).encode(),json.dumps(values,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
        db().execute('INSERT INTO safety_audit(actor,action,target,reason,outcome,created,previous,digest) VALUES(?,?,?,?,?,?,?,?)',(*values,digest))
        if commit:db().commit()
    def restricted(owner,feature='all'):
        return db().execute("SELECT * FROM safety_restrictions WHERE owner=? AND revoked=0 AND kind<>'warn' AND (feature='all' OR feature=?) AND (expires IS NULL OR expires>?) ORDER BY created DESC LIMIT 1",(owner,feature,time.time())).fetchone()
    def paused(feature):
        r=db().execute('SELECT * FROM safety_switches WHERE name=?',(feature,)).fetchone();return r if r and r['paused'] else None
    def reason(data):
        value=data.get('reason','')
        if data.get('confirmed') is not True or not isinstance(value,str) or not 12<=len(value.strip())<=500:abort(400,description='Confirm this action and provide a reason of 12–500 characters.')
        return value.strip()
    def admin(permission):
        auth=staff['require'](permission)
        if request.method!='GET' and not ops['csrf_valid']():abort(403)
        return dict(id=auth['staff_id'],username=auth['username'])
    def capture(kind,reference,viewer):
        target='';evidence={}
        if kind in ('profile','user'):
            target=social['resolve'](reference);card=app.extensions['solace_people']['card'](target,viewer) if target else None
            if not card:abort(404)
            evidence=card
        elif kind=='dm':
            row=db().execute('SELECT m.*,c.a,c.b FROM dm_messages m JOIN dm_conversations c ON c.id=m.conversation WHERE m.id=?',(reference,)).fetchone()
            if not row or viewer not in (row['a'],row['b']) or row['deleted']:abort(404)
            target=row['sender']
            if social['blocked'](viewer,target):abort(404)
            evidence={k:row[k] for k in ('body','created','media_id')}
        elif kind=='world_message':
            app.extensions['solace_world']['access']()
            row=db().execute('SELECT * FROM world_messages WHERE id=? AND deleted=0',(reference,)).fetchone()
            if not row or social['blocked'](viewer,row['sender']):abort(404)
            target=row['sender'];evidence={k:row[k] for k in ('body','created','media_id')}
        elif kind=='room_message':
            row=db().execute('SELECT * FROM messages WHERE id=?',(reference,)).fetchone()
            if not row or not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(row['room'],viewer)).fetchone():abort(404)
            target=row['sender'] or '';evidence={k:row[k] for k in ('body','name','created')}
        elif kind=='attachment':
            row=db().execute('SELECT * FROM chat_media WHERE id=? AND deleted=0 AND message IS NOT NULL',(reference,)).fetchone()
            if not row:abort(404)
            if row['scope']=='world':
                app.extensions['solace_world']['access']();allowed=True
            elif row['scope']=='room':allowed=db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(row['scope_id'],viewer)).fetchone()
            else:allowed=db().execute('SELECT 1 FROM dm_conversations WHERE id=? AND (a=? OR b=?)',(row['scope_id'],viewer,viewer)).fetchone()
            if not allowed:abort(404)
            target=row['owner']
            if row['scope'] in ('dm','world') and social['blocked'](viewer,target):abort(404)
            evidence={k:row[k] for k in ('mime','width','height','animated','bytes')};evidence['sha256']=row['digest']
            # A bounded poster, never the original private attachment.
            if row['poster']:
                import base64
                if len(row['poster'])<=65536:evidence['poster']=base64.b64encode(row['poster']).decode()
        elif kind=='room':
            row=db().execute('SELECT r.id,r.name,r.host,s.visibility,s.public_id FROM rooms r JOIN room_settings s ON s.room=r.id WHERE r.id=? OR s.public_id=?',(reference,reference)).fetchone()
            if not row or (row['visibility']!='public' and not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(row['id'],viewer)).fetchone()):abort(404)
            target=row['host'];evidence=dict(name=row['name'],visibility=row['visibility'])
        elif kind=='invitation':
            row=db().execute('SELECT i.*,r.name FROM room_invitations i LEFT JOIN rooms r ON r.id=i.room WHERE i.id=? AND (i.target=? OR i.sender=?)',(reference,viewer,viewer)).fetchone()
            if not row:abort(404)
            target=row['sender'];evidence={k:row[k] for k in ('name','created','status')}
        else:abort(400)
        if target==viewer:abort(400,description='You cannot report yourself.')
        return target,evidence
    @app.route('/api/me/reports',methods=['GET','POST'])
    def reports():
        uid=social['named']()['id']
        if request.method=='POST':
            d=payload();kind=d.get('kind');ref=d.get('reference');explanation=d.get('explanation','')
            if not isinstance(ref,str) or not 1<=len(ref)<=100 or d.get('category') not in CATEGORIES or not isinstance(explanation,str) or len(explanation)>1000:abort(400)
            if limited('reports-ip',12,3600) or limited('reports-user:'+uid,6,3600):abort(429)
            db().execute('BEGIN IMMEDIATE')
            old=db().execute('SELECT id,target FROM safety_reports WHERE reporter=? AND kind=? AND reference=?',(uid,kind,ref)).fetchone()
            if old:
                if d.get('block') is True and old['target'] and social['person'](old['target']):social['block'](uid,old['target'])
                db().commit();return jsonify(ok=True,id=old['id']),200
            target,evidence=capture(kind,ref,uid);identifier=secrets.token_urlsafe(18)
            db().execute('INSERT INTO safety_reports(id,reporter,target,kind,reference,category,explanation,created,evidence,evidence_until) VALUES(?,?,?,?,?,?,?,?,?,?)',(identifier,uid,target,kind,ref,d['category'],explanation,time.time(),json.dumps(evidence),time.time()+30*86400))
            if d.get('block') is True and target:
                social['block'](uid,target)
            db().commit();return jsonify(ok=True,id=identifier),201
        return jsonify(reports=[dict(r) for r in db().execute('SELECT id,kind,category,status,created FROM safety_reports WHERE reporter=? ORDER BY created DESC LIMIT 100',(uid,))])
    @app.get('/safety')
    def safety_page():return render_template('safety.html')
    @app.route('/api/me/safety',methods=['GET','POST'])
    def own_safety():
        uid=session.get('safety_identity') or session['uid']
        if request.method=='POST':
            d=payload();text=d.get('body','');identifier=d.get('restriction')
            if not isinstance(text,str) or not 20<=len(text)<=2000:abort(400)
            if not db().execute('SELECT 1 FROM safety_restrictions WHERE id=? AND owner=?',(identifier,uid)).fetchone():abort(404)
            if limited('appeals:'+uid,4,3600):abort(429)
            db().execute('INSERT OR IGNORE INTO safety_appeals(id,owner,restriction,body,created) VALUES(?,?,?,?,?)',(secrets.token_urlsafe(18),uid,identifier,text,time.time()));db().commit()
        return jsonify(restrictions=[dict(r) for r in db().execute('SELECT id,feature,kind,reason,created,expires,revoked FROM safety_restrictions WHERE owner=? ORDER BY created DESC LIMIT 100',(uid,))],appeals=[dict(r) for r in db().execute('SELECT restriction,status,resolution FROM safety_appeals WHERE owner=?',(uid,))])
    @app.route('/ops/solace/safety/switches',methods=['GET','POST'])
    def switches():
        actor=admin('switches:write' if request.method=='POST' else 'ops:view')
        if request.method=='POST':
            d=payload();why=reason(d)
            if d.get('name') not in SWITCHES or type(d.get('paused')) is not bool:abort(400)
            db().execute('BEGIN IMMEDIATE');db().execute('UPDATE safety_switches SET paused=?,reason=? WHERE name=?',(d['paused'],why,d['name']));audit(actor,'switch',d['name'],why,'paused' if d['paused'] else 'resumed',False);db().commit()
        return jsonify(switches=[dict(r) for r in db().execute('SELECT * FROM safety_switches ORDER BY name')])
    @app.route('/ops/solace/safety/reports',methods=['GET','POST'])
    def queue():
        actor=admin('reports:review' if request.method=='POST' else 'reports:view')
        if request.method=='POST':
            d=payload();why=reason(d)
            if d.get('status') not in ('open','reviewing','resolved','dismissed') or d.get('severity') not in ('normal','high','urgent') or not isinstance(d.get('assigned',''),str) or len(d.get('assigned',''))>80:abort(400)
            if d.get('assigned'):
                with ops['storage']() as c:
                    if not c.execute('SELECT 1 FROM ops_staff WHERE username=? AND enabled=1',(d['assigned'],)).fetchone():abort(400,description='Assign an enabled named staff identity.')
            db().execute('BEGIN IMMEDIATE');changed=db().execute('UPDATE safety_reports SET status=?,severity=?,assigned=?,resolution=? WHERE id=?',(d['status'],d['severity'],d.get('assigned',''),why,d.get('id'))).rowcount
            if not changed:abort(404)
            db().execute('INSERT INTO safety_notes(report,actor,note,created) VALUES(?,?,?,?)',(d['id'],actor['id'],why,time.time()));audit(actor,'report_review',d['id'],why,d['status'],False);db().commit()
        try:page=int(request.args.get('page','0'))
        except ValueError:abort(400)
        if not 0<=page<=100000:abort(400)
        status=request.args.get('status','all')
        if status not in ('all','open','reviewing','resolved','dismissed'):abort(400)
        query='SELECT id,kind,category,status,severity,assigned,created,evidence_until,resolution FROM safety_reports'+(' WHERE status=?' if status!='all' else '')+' ORDER BY created DESC LIMIT 31 OFFSET ?'
        rows=[dict(r) for r in db().execute(query,(status,page*30) if status!='all' else (page*30,))]
        return jsonify(reports=rows[:30],more=len(rows)>30,page=page)
    @app.post('/ops/solace/safety/evidence/<identifier>')
    def evidence(identifier):
        actor=admin('evidence:read');d=payload();why=reason(d)
        row=db().execute('SELECT * FROM safety_reports WHERE id=?',(identifier,)).fetchone()
        if not row:abort(404)
        audit(actor,'evidence_read',identifier,why,'success' if row['evidence_until']>time.time() else 'expired')
        return jsonify(kind=row['kind'],reference=row['reference'],evidence=json.loads(row['evidence']) if row['evidence'] and row['evidence_until']>time.time() else None,explanation=row['explanation'],target=social['social_profile'](row['target'])['code'] if row['target'] and social['person'](row['target']) else None,notes=[dict(r) for r in db().execute('SELECT actor,note,created FROM safety_notes WHERE report=? ORDER BY id',(identifier,))])
    @app.post('/ops/solace/safety/actions')
    def actions():
        d=payload();action=d.get('action');permission='users:ban' if action=='ban' else 'content:remove' if action=='remove' else 'rooms:close' if action=='close_room' else 'users:restrict';actor=admin(permission);why=reason(d);target=social['resolve'](d.get('code'))
        db().execute('BEGIN IMMEDIATE')
        if action in ('warn','mute','restrict','suspend','ban','revoke_sessions'):
            if not target or not social['person'](target):abort(404)
            feature='all' if action in ('suspend','ban','revoke_sessions','warn') else 'messaging' if action=='mute' else d.get('feature');hours=d.get('hours',24)
            if feature not in FEATURES or type(hours) is not int or not 1<=hours<=720:abort(400)
            if action!='revoke_sessions':db().execute('INSERT INTO safety_restrictions VALUES(?,?,?,?,?,?,?,0)',(secrets.token_urlsafe(18),target,feature,action,why,time.time(),None if action=='ban' else time.time()+hours*3600))
            if action=='revoke_sessions' and not db().execute('SELECT 1 FROM accounts WHERE id=?',(target,)).fetchone():db().execute('INSERT OR REPLACE INTO safety_guest_revocations VALUES(?,?)',(target,time.time()))
            if action in ('suspend','ban','revoke_sessions'):
                db().execute('DELETE FROM account_sessions WHERE owner=?',(target,));app.extensions['solace_launch']['leave_identity'](target);db().execute('DELETE FROM discovery_leases WHERE owner=?',(target,));db().execute('DELETE FROM world_presence WHERE owner=?',(target,))
        elif action=='reverse':
            old=db().execute('SELECT * FROM safety_restrictions WHERE id=?',(d.get('id'),)).fetchone()
            if not old:abort(404)
            if old['kind']=='ban':staff['require']('users:ban')
            db().execute('UPDATE safety_restrictions SET revoked=1 WHERE id=?',(old['id'],));target=old['owner']
        elif action=='close_room':
            from app import delete_room_records
            target=d.get('id');room=db().execute('SELECT r.id FROM rooms r JOIN room_settings s ON s.room=r.id WHERE r.id=? OR s.public_id=?',(target,target)).fetchone()
            if not room:abort(404)
            delete_room_records(room['id'])
        elif action=='remove':
            kind=d.get('kind');target=d.get('id')
            if kind=='dm':changed=db().execute("UPDATE dm_messages SET body='',deleted=1 WHERE id=?",(target,));db().execute('UPDATE chat_media SET data=NULL,poster=NULL,bytes=0,deleted=1 WHERE scope=\'dm\' AND message=?',(target,))
            elif kind=='attachment':
                changed=db().execute('UPDATE chat_media SET data=NULL,poster=NULL,bytes=0,deleted=1,uploaded=? WHERE id=?',(time.time(),target));app.extensions['solace_world']['bump']()
            elif kind=='room_message':changed=db().execute("UPDATE messages SET body='[Removed by moderation]' WHERE id=?",(target,))
            elif kind=='world_message':
                changed=db().execute("UPDATE world_messages SET body='',deleted=1 WHERE id=?",(target,));db().execute("UPDATE chat_media SET data=NULL,poster=NULL,bytes=0,deleted=1 WHERE scope='world' AND message=?",(target,));app.extensions['solace_world']['bump']()
            elif kind=='invitation':changed=db().execute("UPDATE room_invitations SET status='declined' WHERE id=?",(target,))
            else:abort(400)
            if not changed.rowcount:abort(404,description='Content unavailable.')
        else:abort(400)
        audit(actor,action,str(target or d.get('id','')),why,'success',False);db().commit();return jsonify(ok=True)
    @app.route('/ops/solace/safety/appeals',methods=['GET','POST'])
    def appeals():
        actor=admin('appeals:review')
        if request.method=='POST':
            d=payload();why=reason(d)
            if d.get('status') not in ('reviewing','accepted','declined'):abort(400)
            if not db().execute('SELECT 1 FROM safety_appeals WHERE id=?',(d.get('id'),)).fetchone():abort(404)
            db().execute('UPDATE safety_appeals SET status=?,resolution=? WHERE id=?',(d['status'],why,d['id']));audit(actor,'appeal_review',d['id'],why,d['status'],False);db().commit()
        return jsonify(appeals=[dict(r) for r in db().execute('SELECT id,restriction,body,status,resolution,created FROM safety_appeals ORDER BY created DESC LIMIT 100')])
    def verify_audit():
        previous=''
        for r in db().execute('SELECT * FROM safety_audit ORDER BY id'):
            values=[r[k] for k in ('actor','action','target','reason','outcome','created','previous')]
            digest=hmac.new(str(app.secret_key).encode(),json.dumps(values,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
            if r['previous']!=previous or not hmac.compare_digest(digest,r['digest']):return False
            previous=r['digest']
        return True
    @app.get('/ops/solace/safety/audit')
    def audit_feed():
        admin('audit:view');return jsonify(verified=verify_audit(),events=[dict(r) for r in db().execute('SELECT * FROM safety_audit ORDER BY id DESC LIMIT 100')])
    @app.get('/ops/solace/safety/overview')
    def overview():
        admin('users:view');counts={table:db().execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['discovery_profiles','connections','dm_conversations','dm_messages','rooms','chat_media','room_invitations','world_messages','world_presence','safety_reports','safety_restrictions']}
        rows=db().execute('SELECT owner,code FROM social_profiles ORDER BY code LIMIT 100').fetchall()
        return jsonify(counts=counts,users=[dict(code=r['code'],name=social['person'](r['owner'])['name'],restricted=bool(restricted(r['owner'])),discovery=bool(app.extensions['solace_people']['settings'](r['owner'])['opted'])) for r in rows if social['person'](r['owner'])])
    @app.get('/ops/solace/safety/inventory/<section>')
    def inventory(section):
        admin('users:view')
        try:page=int(request.args.get('page','0'))
        except ValueError:abort(400)
        if not 0<=page<=100000:abort(400)
        queries={
          'connections':"SELECT sender,target,status,created FROM connections ORDER BY created DESC LIMIT 30 OFFSET ?",
          'messaging':"SELECT c.id,c.a,c.b,c.created,COUNT(m.id) messages FROM dm_conversations c LEFT JOIN dm_messages m ON m.conversation=c.id GROUP BY c.id ORDER BY c.created DESC LIMIT 30 OFFSET ?",
          'rooms':"SELECT s.public_id AS id,CASE WHEN s.visibility='public' THEN r.name ELSE '[Private room]' END name,r.host,s.visibility,s.capacity,COUNT(m.id) participants FROM rooms r JOIN room_settings s ON s.room=r.id LEFT JOIN members m ON m.room=r.id GROUP BY r.id ORDER BY r.updated DESC LIMIT 30 OFFSET ?",
          'media':"SELECT id,owner,scope,mime,width,height,animated,bytes,deleted,uploaded FROM chat_media ORDER BY uploaded DESC LIMIT 30 OFFSET ?",
          'invitations':"SELECT id,sender,target,status,created,expires FROM room_invitations ORDER BY created DESC LIMIT 30 OFFSET ?",
          'discovery':"SELECT owner,opted,visible,avatar,stats FROM discovery_profiles ORDER BY owner LIMIT 30 OFFSET ?",
          'restrictions':"SELECT id,owner,feature,kind,reason,created,expires,revoked FROM safety_restrictions ORDER BY created DESC LIMIT 30 OFFSET ?"}
        if section=='security':
            admin('audit:view')
            with ops['storage']() as c:rows=[dict(r) for r in c.execute('SELECT staff,event,created FROM staff_security ORDER BY id DESC LIMIT 30 OFFSET ?',(page*30,))]
        else:
            if section not in queries:abort(404)
            rows=[dict(r) for r in db().execute(queries[section],(page*30,))]
            for row in rows:
                if section in ('connections','messaging','invitations'):
                    for private_field in ('sender','target','a','b'):row.pop(private_field,None)
                if section=='rooms':row.pop('host',None)
                for field in ('owner','sender','target','a','b','host'):
                    if row.get(field):row[field]=social['social_profile'](row[field])['code'] if social['person'](row[field]) else 'Deleted profile'
            db().commit()
        return jsonify(items=rows,page=page,more=len(rows)==30)

    def gate():
        initialize();path=request.path;uid=session['uid'];
        if time.time()-last_clean.get(app.instance_path,0)>3600:
            db().execute('UPDATE safety_reports SET evidence=NULL WHERE evidence_until<? AND evidence IS NOT NULL',(time.time(),));db().execute('DELETE FROM safety_notes WHERE report IN (SELECT id FROM safety_reports WHERE created<?)',(time.time()-180*86400,));db().execute('DELETE FROM safety_reports WHERE created<?',(time.time()-180*86400,));db().execute('DELETE FROM safety_appeals WHERE created<?',(time.time()-180*86400,));db().commit();last_clean[app.instance_path]=time.time()
        if not g.account and db().execute('SELECT 1 FROM safety_guest_revocations WHERE owner=?',(uid,)).fetchone():
            session['uid']=secrets.token_urlsafe(24);session['identity_expired']=True;session['account_csrf']=secrets.token_urlsafe(32)
            if path.startswith('/api/'):return jsonify(error='Your guest session ended. Continue with a new guest profile or sign in.',code='guest_session_ended',help='/welcome'),401
            if path not in ('/welcome','/signin','/signup','/safety') and not path.startswith(('/static/','/ops/')):return redirect('/welcome',303)
            uid=session['uid']
        sticky=session.get('safety_identity');severe=restricted(sticky or uid)
        if not severe and sticky:session.pop('safety_identity',None)
        if path.startswith(('/ops/','/static/','/api/me/safety','/api/auth/signin','/api/auth/signout','/api/auth/recover','/api/me/history','/api/me/activity')) or path=='/safety':return
        if path=='/api/me' and request.method=='GET':return
        if path in ('/api/me/delete-account','/api/me/avatar') and g.account:return
        if severe and path in ('/home','/world','/messages','/friends','/rooms','/games','/app','/create','/join'):return redirect('/safety',303)
        if severe and path.startswith('/api/'):
            return jsonify(error=severe['reason'],code='platform_restricted',help='/safety'),403
        feature=None
        if path=='/api/auth/signup':feature='registrations'
        elif path.startswith('/api/me/discovery'):feature='discovery'
        elif path.startswith('/api/me/world/messages') and request.method=='POST':feature='messaging'
        elif path=='/api/rooms' and request.method=='POST':feature='room_creation'
        elif '/invit' in path and request.method=='POST':feature='invitations'
        elif path.endswith('/settings') and request.method=='POST' and (request.get_json(silent=True) or {}).get('action')=='regenerate':feature='invitations'
        elif path=='/api/me/media' and request.method=='POST':feature='uploads'
        elif path.startswith('/api/me/conversations') and request.method=='POST':feature='messaging'
        elif path.startswith('/api/me/room-media') and request.method=='POST':feature='messaging'
        elif path.startswith('/api/me/connections') and request.method=='POST':feature='connections'
        elif path.endswith(('/game','/basketball','/ludo')) and request.method=='POST':feature='games'
        elif path.startswith('/api/rooms/') and request.method=='POST':
            d=request.get_json(silent=True)
            if not isinstance(d,dict):abort(400)
            action=d.get('action');feature='messaging' if action=='chat' else None
            if action=='chat' and (limited('room-chat-ip',180,60) or limited('room-chat:'+uid,60,60)):return jsonify(error='Please slow down a little.'),429
        if path in ('/api/me/conversations','/api/me/connections') and request.method=='POST':
            d=payload();other=social['resolve'](d.get('code'))
            if other and restricted(other) and (path.endswith('/conversations') or d.get('action') in ('request','accept')):return jsonify(error='This profile is unavailable.'),403
        if feature=='discovery' and request.method=='POST':
            d={'active':False} if path.endswith('/presence') and request.form.get('active')=='0' else payload()
            if (path=='/api/me/discovery' and d.get('opted') is False) or (path.endswith('/presence') and d.get('active') is False):return
        if feature:
            restriction=restricted(uid,feature);switch=paused(feature)
            if restriction or switch:return jsonify(error=restriction['reason'] if restriction else 'This feature is temporarily paused.',code='feature_paused'),403
        if paused('guest_access') and not g.account and (path.startswith('/api/rooms') or path=='/api/me/profile'):
            app.extensions['solace_launch']['leave_identity'](uid);db().execute('DELETE FROM discovery_leases WHERE owner=?',(uid,));db().commit();return jsonify(error='Guest access is temporarily paused. Sign in to continue.',code='guest_access_paused'),403
    app.extensions['solace_safety']=dict(initialize=initialize,audit=audit,restricted=restricted,paused=paused,gate=gate,verify_audit=verify_audit)
