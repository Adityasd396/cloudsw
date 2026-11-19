"""Opt-in, expiring discovery presence and permission-filtered profile cards."""
import hashlib,hmac,io,re,time
from flask import abort,g,jsonify,redirect,render_template,request,send_file,session
from itsdangerous import URLSafeTimedSerializer,BadSignature

def register_people(app,db,limited):
    ready=set();social=app.extensions['solace_social'];signer=URLSafeTimedSerializer(app.secret_key,salt='people-cursor')
    def payload():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):abort(400,description='Send a JSON object.')
        return value
    def initialize():
        if app.instance_path in ready:return
        db().executescript('''BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS discovery_profiles(owner TEXT PRIMARY KEY,opted INTEGER NOT NULL DEFAULT 0,visible INTEGER NOT NULL DEFAULT 1,avatar INTEGER NOT NULL DEFAULT 0,stats INTEGER NOT NULL DEFAULT 0,bio TEXT NOT NULL DEFAULT '',interests TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS discovery_leases(owner TEXT NOT NULL,tab TEXT NOT NULL,auth TEXT NOT NULL,expires REAL NOT NULL,PRIMARY KEY(owner,tab));
        CREATE INDEX IF NOT EXISTS discovery_expiry ON discovery_leases(expires,owner);
        INSERT OR IGNORE INTO launch_migrations VALUES(6,strftime('%s','now'));COMMIT;''');ready.add(app.instance_path)
    def eligible(owner):
        safety=app.extensions.get('solace_safety');return not safety or (not safety['restricted'](owner,'discovery') and not safety['paused']('discovery') and not (safety['paused']('guest_access') and not db().execute('SELECT 1 FROM accounts WHERE id=?',(owner,)).fetchone()))
    def settings(owner):
        r=db().execute('SELECT * FROM discovery_profiles WHERE owner=?',(owner,)).fetchone()
        return dict(r) if r else dict(owner=owner,opted=0,visible=1,avatar=0,stats=0,bio='',interests='')
    def online(owner):
        return bool(db().execute('''SELECT 1 FROM discovery_leases l WHERE l.owner=? AND l.expires>? AND (l.auth='' OR EXISTS(SELECT 1 FROM account_sessions a WHERE a.token=l.auth AND a.owner=l.owner AND a.expires>?)) LIMIT 1''',(owner,time.time(),time.time())).fetchone())
    def card(owner,viewer):
        if app.extensions.get('solace_safety') and app.extensions['solace_safety']['restricted'](owner):return None
        accepted=social['friends'](owner,viewer);result=social['card'](owner,viewer,accepted)
        if not result:return None
        prefs=settings(owner);discoverable=prefs['opted'] and prefs['visible'] and eligible(owner) and online(owner)
        # Room membership is permission to see a name, not private friends-only fields.
        if accepted or discoverable or owner==viewer:result.update(bio=prefs['bio'],interests=prefs['interests'])
        if discoverable:
            result['online']=True
            if prefs['avatar'] and social['person'](owner)['avatar']:result['avatar']='/api/me/profiles/'+result['code']+'/avatar'
            if prefs['stats']:
                r=db().execute('SELECT COUNT(*) sessions,COALESCE(SUM(seconds),0) seconds FROM watch_history WHERE owner=?',(owner,)).fetchone();result['stats']=dict(r)
        relation=db().execute('SELECT status,sender FROM connections WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(viewer,owner,owner,viewer)).fetchone()
        result.update(status=relation['status'] if relation else 'none',incoming=bool(relation and relation['sender']==owner),you=owner==viewer)
        return result
    @app.get('/profile')
    @app.get('/report')
    def people_panel_page():
        social['named']();return render_template('profile-panel.html')
    @app.get('/world')
    def world():
        
        if not social['person'](session['uid']):return redirect('/welcome',303)
        return render_template('world.html')
    @app.route('/api/me/discovery',methods=['GET','POST'])
    def discovery_settings():
        uid=social['named']()['id'];social['social_profile'](uid)
        if request.method=='POST':
            d=payload()
            if any(type(d.get(k)) is not bool for k in ['opted','visible','avatar','stats']) or any(not isinstance(d.get(k),str) or len(d[k])>n for k,n in [('bio',240),('interests',120)]):abort(400)
            if limited('discovery-settings',20,60):abort(429)
            db().execute('INSERT INTO discovery_profiles VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner) DO UPDATE SET opted=excluded.opted,visible=excluded.visible,avatar=excluded.avatar,stats=excluded.stats,bio=excluded.bio,interests=excluded.interests',(uid,d['opted'],d['visible'],d['avatar'],d['stats'],d['bio'].strip(),d['interests'].strip()))
            if not d['opted'] or not d['visible']:db().execute('DELETE FROM discovery_leases WHERE owner=?',(uid,))
            db().commit()
        db().commit();return jsonify(settings={k:v for k,v in settings(uid).items() if k!='owner'})
    @app.post('/api/me/discovery/presence')
    def presence():
        uid=social['named']()['id'];d={'tab':request.form.get('tab'),'active':False} if request.form.get('active')=='0' else payload();tab=d.get('tab')
        if not isinstance(tab,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{16,80}',tab) or type(d.get('active')) is not bool:abort(400)
        if limited('discovery-presence',180,60):abort(429)
        db().execute('DELETE FROM discovery_leases WHERE expires<?',(time.time(),));prefs=settings(uid)
        if not d['active'] or not prefs['opted'] or not prefs['visible'] or not eligible(uid):db().execute('DELETE FROM discovery_leases WHERE owner=? AND tab=?',(uid,tab))
        else:
            if db().execute('SELECT COUNT(*) FROM discovery_leases WHERE owner=? AND tab<>?',(uid,tab)).fetchone()[0]>=8:db().commit();abort(429)
            auth=hashlib.sha256(request.cookies.get('solace_account','').encode()).hexdigest() if g.account else ''
            db().execute('INSERT INTO discovery_leases VALUES(?,?,?,?) ON CONFLICT(owner,tab) DO UPDATE SET auth=excluded.auth,expires=excluded.expires',(uid,tab,auth,time.time()+32))
        db().commit();return jsonify(ok=True)
    @app.get('/api/me/discovery/people')
    def people():
        uid=social['named']()['id']
        if limited('discovery-list',60,60):abort(429)
        after='';cursor=request.args.get('cursor')
        if cursor:
            try:
                value=signer.loads(cursor,max_age=300)
                if value['viewer']!=hmac.new(str(app.secret_key).encode(),('discovery-cursor:'+uid).encode(),hashlib.sha256).hexdigest():abort(400)
                after=value['after']
            except (BadSignature,KeyError,TypeError):abort(400)
        rows=db().execute('''SELECT p.owner,p.code FROM social_profiles p JOIN discovery_profiles d ON d.owner=p.owner WHERE d.opted=1 AND d.visible=1 AND p.code>? AND p.owner<>? AND EXISTS(SELECT 1 FROM discovery_leases l WHERE l.owner=p.owner AND l.expires>?) ORDER BY p.code LIMIT 100''',(after,uid,time.time())).fetchall();items=[];last=after
        for row in rows:
            last=row['code']
            if eligible(row['owner']) and online(row['owner']):
                item=card(row['owner'],uid)
                if item:items.append(item)
            if len(items)==12:break
        db().commit();return jsonify(people=items,cursor=signer.dumps(dict(viewer=hmac.new(str(app.secret_key).encode(),('discovery-cursor:'+uid).encode(),hashlib.sha256).hexdigest(),after=last)) if len(rows)==100 or len(items)==12 else None)
    @app.get('/api/me/profiles/<code>')
    def people_profile(code):
        uid=social['named']()['id'];other=social['resolve'](code)
        if not other:abort(404)
        if limited('profile-view-ip',120,60) or limited('profile-view:'+uid,60,60):abort(429)
        result=card(other,uid)
        if not result:abort(404)
        db().commit();return jsonify(profile=result)
    @app.get('/api/me/profiles/<code>/avatar')
    def people_avatar(code):
        uid=social['named']()['id'];other=social['resolve'](code);p=card(other,uid) if other else None
        if not p or p['avatar']!='/api/me/profiles/'+p['code']+'/avatar':abort(404)
        row=db().execute('SELECT avatar FROM accounts WHERE id=? UNION ALL SELECT avatar FROM guest_data WHERE owner=? LIMIT 1',(other,other)).fetchone()
        if not row or not row['avatar']:abort(404)
        return send_file(io.BytesIO(row['avatar']),mimetype='image/png',max_age=0)
    app.extensions['solace_people']=dict(initialize=initialize,card=card,settings=settings,online=online)
