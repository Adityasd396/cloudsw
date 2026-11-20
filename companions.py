"""Shared chat actions, private in-app notices and room-independent game sessions."""
import io,json,secrets,time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from flask import abort,g,jsonify,redirect,render_template,request,session,send_file

GAMES={'hearts':('tictactoe.html','room_game'),'hoops':('game.html','basketball'),'ludo':('ludo.html','room_ludo')}
REACTIONS=('❤️','🥰','😂','👏','✨','😮')

def register_companions(app,db,limited):
 ready=set()
 def social():return app.extensions['solace_social']
 def safety():return app.extensions['solace_safety']
 def payload():
  d=request.get_json(silent=True)
  if not isinstance(d,dict):abort(400)
  return d
 def owner():return social()['named']()['id']
 def profile(uid):
  cache=g.__dict__.setdefault('_companion_profiles',{})
  if uid not in cache:
   row=db().execute('SELECT * FROM social_profiles WHERE owner=?',(uid,)).fetchone();cache[uid]=dict(row) if row else social()['social_profile'](uid)
  return cache[uid]
 def initialize():
  if app.instance_path in ready:return
  db().executescript('''BEGIN IMMEDIATE;
  CREATE TABLE IF NOT EXISTS chat_reactions(scope TEXT,target TEXT,message INTEGER,owner TEXT,emoji TEXT,created REAL,PRIMARY KEY(scope,target,message,owner));
  CREATE INDEX IF NOT EXISTS chat_reaction_target ON chat_reactions(scope,target,message);
  CREATE TABLE IF NOT EXISTS chat_reads(scope TEXT,target TEXT,owner TEXT,read_id INTEGER NOT NULL DEFAULT 0,updated REAL,PRIMARY KEY(scope,target,owner));
  CREATE TABLE IF NOT EXISTS notice_receipts(owner TEXT,event TEXT,seen REAL,PRIMARY KEY(owner,event));
  CREATE TABLE IF NOT EXISTS play_sessions(id TEXT PRIMARY KEY,creator TEXT,kind TEXT,created REAL,expires REAL);
  CREATE TABLE IF NOT EXISTS play_members(game TEXT,owner TEXT,joined REAL,PRIMARY KEY(game,owner));
  CREATE TABLE IF NOT EXISTS play_invitations(id TEXT PRIMARY KEY,game TEXT,sender TEXT,target TEXT,status TEXT,created REAL,expires REAL,UNIQUE(game,sender,target));
  CREATE INDEX IF NOT EXISTS play_invite_target ON play_invitations(target,status,expires);
  INSERT OR IGNORE INTO launch_migrations VALUES(9,strftime('%s','now'));COMMIT;''')
  ready.add(app.instance_path)
 def access(scope,target,write=False):
  uid=owner()
  if not isinstance(target,str) or not 1<=len(target)<=120:abort(400)
  if scope=='world' and target=='community':app.extensions['solace_world']['access'](write)
  elif scope=='room':
   if not db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(target,uid)).fetchone():abort(403)
  elif scope=='dm':app.extensions['solace_messaging']['conversation'](target,write)
  else:abort(400)
  if write and (safety()['restricted'](uid,'messaging') or safety()['paused']('messaging')):abort(403)
  return uid
 def messages(scope,target,ids):
  table,column={'room':('messages','room'),'world':('world_messages',None),'dm':('dm_messages','conversation')}[scope]
  sql='SELECT id,sender FROM '+table+' WHERE id IN ('+','.join('?' for _ in ids)+')';args=list(ids)
  if column:sql+=' AND '+column+'=?';args.append(target)
  if scope!='room':sql+=' AND deleted=0'
  return [r for r in db().execute(sql,args) if r['sender'] and not social()['blocked'](session['uid'],r['sender']) and not safety()['restricted'](r['sender'])]
 def picture_url(uid,scope,target):
  person=social()['person'](uid)
  if not person or not person['avatar'] or social()['blocked'](uid,session['uid']):return '/static/default-avatar.svg'
  cache=g.__dict__.setdefault('_companion_avatars',{});key=(uid,scope,target)
  if key in cache:return cache[key]
  s=profile(uid);allowed=bool(s['share_avatar'])
  if scope=='world':
   p=db().execute('SELECT opted,avatar FROM discovery_profiles WHERE owner=?',(uid,)).fetchone();allowed=bool(p and p['opted'] and p['avatar'])
  updated=db().execute('SELECT updated FROM profiles WHERE id=?',(uid,)).fetchone();version=str(int((updated['updated'] if updated else 0)*1000))
  cache[key]='/api/me/chat/avatar/'+s['code']+'?scope='+scope+'&target='+target+'&v='+version if allowed else '/static/default-avatar.svg'
  return cache[key]
 @app.get('/api/me/chat/avatar/<code>')
 def chat_avatar(code):
  scope=request.args.get('scope');target=request.args.get('target','');access(scope,target);who=social()['resolve'](code)
  if not who:abort(404)
  if scope=='room':allowed=db().execute('SELECT 1 FROM members WHERE room=? AND id=? UNION SELECT 1 FROM messages WHERE room=? AND sender=?',(target,who,target,who)).fetchone()
  elif scope=='dm':c,_=app.extensions['solace_messaging']['conversation'](target);allowed=who in (c['a'],c['b'])
  else:allowed=db().execute('SELECT 1 FROM world_messages WHERE sender=? AND deleted=0 LIMIT 1',(who,)).fetchone()
  if not allowed or picture_url(who,scope,target).startswith('/static/'):return redirect('/static/default-avatar.svg')
  table,column=('accounts','id') if db().execute('SELECT 1 FROM accounts WHERE id=?',(who,)).fetchone() else ('guest_data','owner')
  row=db().execute('SELECT avatar FROM '+table+' WHERE '+column+'=?',(who,)).fetchone()
  if not row or not row['avatar']:return redirect('/static/default-avatar.svg')
  return send_file(io.BytesIO(row['avatar']),mimetype='image/png',max_age=0)
 @app.route('/api/me/chat/actions',methods=['GET','POST'])
 def chat_actions():
  d=request.get_json(silent=True) if request.method=='POST' else request.args
  if not isinstance(d,(dict,type(request.args))):abort(400)
  scope=d.get('scope');target=d.get('target','');uid=access(scope,target,request.method=='POST' and 'emoji' in d)
  raw=d.get('ids','');ids=raw if isinstance(raw,list) else raw.split(',')
  try:ids=list(dict.fromkeys(int(v) for v in ids if str(v)))
  except (ValueError,TypeError):abort(400)
  if not ids or len(ids)>100 or any(v<1 or v>=2**63 for v in ids):abort(400)
  rows=messages(scope,target,ids);found={r['id']:r for r in rows}
  if request.method=='POST':
   if limited('chat-actions:'+uid,90,60):abort(429)
   db().execute('BEGIN IMMEDIATE')
   if 'emoji' in d:
    mid=d.get('message');emoji=d.get('emoji')
    if type(mid) is not int or mid not in found or emoji not in REACTIONS:abort(400)
    db().execute('INSERT INTO chat_reactions VALUES(?,?,?,?,?,?) ON CONFLICT(scope,target,message,owner) DO UPDATE SET emoji=CASE WHEN emoji=excluded.emoji THEN NULL ELSE excluded.emoji END,created=excluded.created',(scope,target,mid,uid,emoji,time.time()))
    db().execute('DELETE FROM chat_reactions WHERE emoji IS NULL')
   elif d.get('read') is True:
    if scope=='world' and app.extensions['solace_world']['prefs'](uid)['world_choice']!='joined':abort(403)
    if found:db().execute('INSERT INTO chat_reads VALUES(?,?,?,?,?) ON CONFLICT(scope,target,owner) DO UPDATE SET read_id=MAX(read_id,excluded.read_id),updated=excluded.updated',(scope,target,uid,max(found),time.time()))
   else:abort(400)
   db().commit()
  own_pref=profile(uid);result=[]
  for mid,m in found.items():
   reactions={}
   for row in db().execute('SELECT owner,emoji FROM chat_reactions WHERE scope=? AND target=? AND message=?',(scope,target,mid)):
    if social()['blocked'](uid,row['owner']) or safety()['restricted'](row['owner']):continue
    value=reactions.setdefault(row['emoji'],dict(emoji=row['emoji'],count=0,you=False));value['count']+=1;value['you']|=row['owner']==uid
   count=0
   if m['sender']==uid and own_pref['share_read']:
    for r in db().execute('SELECT owner FROM chat_reads WHERE scope=? AND target=? AND owner<>? AND read_id>=?',(scope,target,uid,mid)):
     if social()['person'](r['owner']) and not social()['blocked'](uid,r['owner']) and profile(r['owner'])['share_read']:
      if scope=='dm' and not social()['friends'](uid,r['owner']):continue
      if scope=='world' and app.extensions['solace_world']['prefs'](r['owner'])['world_choice']!='joined':continue
      if scope!='room' or db().execute('SELECT 1 FROM members WHERE room=? AND id=?',(target,r['owner'])).fetchone():count+=1
   result.append(dict(id=mid,reactions=list(reactions.values()),read_count=count,code=profile(m['sender'])['code'] if social()['person'](m['sender']) else None,avatar=picture_url(m['sender'],scope,target)))
  db().commit();return jsonify(messages=result)
 def play_context(gid):
  row=db().execute('SELECT * FROM play_sessions WHERE id=? AND expires>?',(gid,time.time())).fetchone()
  if not row:abort(404)
  uid=owner()
  if GAMES[row['kind']][1]!=request.endpoint:abort(404)
  members={r['owner']:social()['person'](r['owner'])['name'] for r in db().execute('SELECT owner FROM play_members WHERE game=?',(gid,)) if social()['person'](r['owner']) and not safety()['restricted'](r['owner'])}
  if uid not in members or any(social()['blocked'](uid,other) for other in members):abort(403)
  if safety()['restricted'](uid,'rooms'):abort(403)
  if request.method=='POST' and limited('play-actions:'+uid,2400,60):abort(429)
  return members
 def game_record(gid):
  uid=owner();row=db().execute('SELECT s.* FROM play_sessions s JOIN play_members m ON m.game=s.id AND m.owner=? WHERE s.id=? AND s.expires>?',(uid,gid,time.time())).fetchone()
  if not row:abort(404)
  members=[r['owner'] for r in db().execute('SELECT owner FROM play_members WHERE game=?',(gid,))]
  if any(social()['blocked'](uid,v) for v in members):abort(403)
  return row
 @app.post('/api/me/play')
 def create_play():
  uid=owner();d=payload();kind=d.get('kind')
  if kind not in GAMES:abort(400)
  if safety()['paused']('room_creation') or safety()['restricted'](uid,'rooms'):abort(403)
  if limited('play-create:'+uid,12,600):abort(429)
  gid='g_'+secrets.token_urlsafe(16);now=time.time();db().execute('BEGIN IMMEDIATE')
  expired=[r['id'] for r in db().execute('SELECT id FROM play_sessions WHERE expires<? LIMIT 200',(now,))]
  for old in expired:
   for table,col in [('room_games','room'),('play_members','game'),('play_invitations','game'),('play_sessions','id')]:db().execute('DELETE FROM '+table+' WHERE '+col+'=?',(old,))
  db().execute('INSERT INTO play_sessions VALUES(?,?,?,?,?)',(gid,uid,kind,now,now+86400));db().execute('INSERT INTO play_members VALUES(?,?,?)',(gid,uid,now));db().commit();return jsonify(next='/play/'+gid),201
 @app.get('/play/<gid>')
 def play_page(gid):
  game=game_record(gid);return render_template('play-session.html',play_id=gid,game_file=GAMES[game['kind']][0],app_space=True)
 @app.route('/api/me/play/<gid>',methods=['GET','POST'])
 def play_details(gid):
  game=game_record(gid);uid=session['uid'];members=db().execute('SELECT owner FROM play_members WHERE game=?',(gid,)).fetchall()
  if request.method=='POST':
   if safety()['paused']('invitations') or safety()['restricted'](uid,'invitations'):abort(403)
   d=payload();other=social()['resolve'](str(d.get('code','')))
   if not other or other==uid or not social()['friends'](uid,other) or social()['blocked'](uid,other) or safety()['restricted'](other):abort(403)
   if len(members)>=2:abort(409,description='This game already has two players.')
   if limited('play-invite:'+uid,12,60):abort(429)
   old=db().execute('SELECT status,expires FROM play_invitations WHERE game=? AND sender=? AND target=?',(gid,uid,other)).fetchone()
   if old and old['expires']>time.time():abort(409,description='This invitation has already been sent.')
   now=time.time();db().execute('INSERT INTO play_invitations VALUES(?,?,?,?,?,?,?) ON CONFLICT(game,sender,target) DO UPDATE SET id=excluded.id,status=excluded.status,created=excluded.created,expires=excluded.expires',(secrets.token_urlsafe(18),gid,uid,other,'pending',now,now+900));db().commit()
  return jsonify(kind=game['kind'],participants=[social()['card'](r['owner'],uid,social()['friends'](uid,r['owner'])) for r in members],can_invite=len(members)<2)
 @app.get('/api/me/play-invitations')
 def incoming_play():
  uid=owner();items=[]
  for row in db().execute("SELECT i.*,s.kind FROM play_invitations i JOIN play_sessions s ON s.id=i.game WHERE i.target=? AND i.status='pending' AND i.expires>? AND s.expires>? ORDER BY i.created DESC LIMIT 20",(uid,time.time(),time.time())):
   if social()['friends'](uid,row['sender']) and not social()['blocked'](uid,row['sender']) and not safety()['restricted'](row['sender']):items.append(dict(id=row['id'],kind=row['kind'],person=social()['card'](row['sender'],uid,True)))
  db().commit();return jsonify(invitations=items)
 @app.post('/api/me/play-invitations/<iid>')
 def respond_play(iid):
  uid=owner();d=payload();action=d.get('action')
  if action not in ('accept','decline'):abort(400)
  if safety()['paused']('invitations') or safety()['restricted'](uid,'invitations'):abort(403)
  if limited('play-reply:'+uid,30,60):abort(429)
  db().execute('BEGIN IMMEDIATE');row=db().execute('SELECT i.* FROM play_invitations i JOIN play_sessions s ON s.id=i.game WHERE i.id=? AND i.target=? AND i.expires>? AND s.expires>?',(iid,uid,time.time(),time.time())).fetchone()
  if not row:abort(410)
  if row['status']!='pending':
   if row['status']=='accepted' and db().execute('SELECT 1 FROM play_members WHERE game=? AND owner=?',(row['game'],uid)).fetchone():db().commit();return jsonify(next='/play/'+row['game'])
   abort(409)
  if not social()['friends'](uid,row['sender']) or social()['blocked'](uid,row['sender']) or safety()['restricted'](row['sender']):abort(403)
  if action=='accept':
   if db().execute('SELECT COUNT(*) FROM play_members WHERE game=?',(row['game'],)).fetchone()[0]>=2:abort(409)
   db().execute('INSERT OR IGNORE INTO play_members VALUES(?,?,?)',(row['game'],uid,time.time()))
  db().execute('UPDATE play_invitations SET status=? WHERE id=?',(action+'ed' if action=='accept' else 'declined',iid));db().commit();return jsonify(next='/play/'+row['game'] if action=='accept' else None)
 def notices(uid):
  result=[];cut=time.time()-86400
  def add(key,kind,other,created,destination,reference=None):
   person=social()['person'](other)
   if not person or social()['blocked'](uid,other) or safety()['restricted'](other):return
   if db().execute('SELECT 1 FROM notice_receipts WHERE owner=? AND event=?',(uid,key)).fetchone():return
   card=social()['card'](other,uid,social()['friends'](uid,other));result.append(dict(id=key,kind=kind,name=person['name'],avatar=card['avatar'],created=created,path=destination,reference=reference))
  for r in db().execute("SELECT * FROM connections WHERE target=? AND status='pending' AND created>? ORDER BY created DESC LIMIT 15",(uid,cut)):add('request:'+r['sender']+':'+str(r['created']),'request',r['sender'],r['created'],'/friends')
  for r in db().execute("SELECT i.* FROM room_invitations i JOIN rooms r ON r.id=i.room JOIN room_settings s ON s.room=r.id WHERE i.target=? AND i.status='pending' AND i.expires>? AND i.epoch=s.epoch ORDER BY i.created DESC LIMIT 15",(uid,time.time())):add('room:'+r['id'],'room',r['sender'],r['created'],'/rooms',r['id'])
  for r in db().execute('''SELECT m.* FROM dm_messages m JOIN dm_inbox i ON i.conversation=m.conversation AND i.owner=? WHERE m.sender<>? AND m.id>MAX(i.read_id,i.hidden_until) AND m.deleted=0 AND m.created>? ORDER BY m.id DESC LIMIT 15''',(uid,uid,cut)):
   if social()['friends'](uid,r['sender']):add('dm:'+str(r['id']),'message',r['sender'],r['created'],'/messages?chat='+r['conversation'])
  for r in db().execute("SELECT i.* FROM play_invitations i JOIN play_sessions s ON s.id=i.game WHERE i.target=? AND i.status='pending' AND i.expires>? AND s.expires>? ORDER BY i.created DESC LIMIT 15",(uid,time.time(),time.time())):add('game:'+r['id'],'game',r['sender'],r['created'],'/games',r['id'])
  return sorted(result,key=lambda r:r['created'],reverse=True)[:20]
 @app.route('/api/me/notifications',methods=['GET','POST'])
 def notifications():
  uid=owner()
  if limited('notices:'+uid,90,60):abort(429)
  if request.method=='POST':
   d=payload();event=d.get('id');db().execute('BEGIN IMMEDIATE');available=next((n for n in notices(uid) if n['id']==event),None)
   if not available:db().commit();return jsonify(claimed=False)
   db().execute('INSERT INTO notice_receipts VALUES(?,?,?)',(uid,event,time.time()));db().execute('DELETE FROM notice_receipts WHERE seen<?',(time.time()-30*86400,));db().commit();return jsonify(claimed=True)
  values=notices(uid);db().commit();return jsonify(events=values)
 @app.get('/api/me/moments')
 def moments():
  uid=owner()
  try:zone=ZoneInfo(request.args.get('timezone','UTC'))
  except (ValueError,ZoneInfoNotFoundError):abort(400)
  end=datetime.now(zone).date();start=end-timedelta(days=13);days={str(start+timedelta(days=i)):0 for i in range(14)}
  for row in db().execute('SELECT started FROM watch_history WHERE owner=? AND started>=?',(uid,datetime.combine(start,datetime.min.time(),zone).timestamp())):
   date=str(datetime.fromtimestamp(row['started'],zone).date())
   if date in days:days[date]+=1
  songs=[dict(title=r['title'],sessions=r['sessions'],seconds=r['seconds']) for r in db().execute('SELECT title,COUNT(*) AS sessions,SUM(seconds) AS seconds FROM watch_history WHERE owner=? GROUP BY video ORDER BY sessions DESC,seconds DESC LIMIT 12',(uid,))]
  people=[dict(name=r['name'],sessions=r['sessions']) for r in db().execute('SELECT p.name,COUNT(DISTINCT h.id) AS sessions FROM watch_people p JOIN watch_history h ON h.id=p.entry WHERE h.owner=? GROUP BY p.person ORDER BY sessions DESC LIMIT 12',(uid,))]
  return jsonify(days=[dict(date=k,sessions=v) for k,v in days.items()],songs=songs,people=people,timezone=str(zone))
 def erase_owner(uid):
  for table in ['chat_reactions','chat_reads','notice_receipts','play_members']:db().execute('DELETE FROM '+table+' WHERE owner=?',(uid,))
  db().execute('DELETE FROM play_invitations WHERE sender=? OR target=?',(uid,uid))
  for row in db().execute('SELECT id FROM play_sessions WHERE creator=?',(uid,)).fetchall():
   for table,column in [('room_games','room'),('play_members','game'),('play_invitations','game')]:db().execute('DELETE FROM '+table+' WHERE '+column+'=?',(row['id'],))
  db().execute('DELETE FROM play_sessions WHERE creator=?',(uid,))
 app.extensions['solace_companions']=dict(initialize=initialize,game_context=play_context,erase_owner=erase_owner)
