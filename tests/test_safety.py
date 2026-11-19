import base64,io,json,re,time,unittest,uuid,sqlite3
from unittest.mock import patch
from contextlib import closing
from pathlib import Path
from app import app,db
from staff_auth import totp
import test_app

class SafetyTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,c,path,data=None):return c.post(path,json=data,headers={'X-CSRF-Token':c.get('/api/me').json['csrf']})
 def code(self,c):return c.get('/api/me/connections').json['friend_code']
 def opt(self,c,**kw):
  d=dict(opted=True,visible=True,avatar=False,stats=False,bio='Hello',interests='Music');d.update(kw);return self.post(c,'/api/me/discovery',d)
 def pulse(self,c,tab=None,active=True):return self.post(c,'/api/me/discovery/presence',dict(tab=tab or uuid.uuid4().hex,active=active))
 def staff(self,role='administrator',name='owner'):
  secret=base64.b32encode(b'12345678901234567890').decode()
  with app.app_context():sid,_=app.extensions['solace_staff']['create'](name,'Synthetic-Staff-Password-2026!',role,secret)
  c=app.test_client();page=c.get('/ops/solace');csrf=re.search(r'name="csrf" value="([^"]+)"',page.text)[1]
  response=c.post('/ops/solace',data=dict(username=name,password='Synthetic-Staff-Password-2026!',otp=totp(secret),csrf=csrf));self.assertEqual(response.status_code,303,response.text)
  with c.session_transaction() as s:token=s['ops_csrf']
  return c,token,sid
 def action(self,c,csrf,data):return c.post('/ops/solace/safety/actions',json=dict(confirmed=True,reason='Synthetic investigation test',**data),headers={'X-CSRF-Token':csrf})
 def test_consent_independent_presence_multiple_tabs_expiry_and_fields(self):
  self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])
  self.post(self.guest,'/api/me/privacy',{'share_presence':True});self.pulse(self.guest);self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])
  self.assertEqual(self.opt(self.guest).status_code,200);a=uuid.uuid4().hex;b=uuid.uuid4().hex;self.pulse(self.guest,a);self.pulse(self.guest,b);self.pulse(self.guest,a,False)
  rows=self.host.get('/api/me/discovery/people').json['people'];self.assertEqual(len(rows),1);p=rows[0];self.assertEqual(p['name'],'Guest');self.assertIsNone(p['stats']);self.assertEqual(p['avatar'],'/static/default-avatar.svg');self.assertNotIn('email',json.dumps(p));self.assertNotIn('owner',p)
  with app.app_context():db().execute('UPDATE discovery_leases SET expires=0');db().commit()
  self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])
 def test_leave_and_block_hide_discovery_and_profile(self):
  self.opt(self.guest);self.pulse(self.guest);code=self.code(self.guest);self.assertEqual(self.host.get('/api/me/profiles/'+code).status_code,200)
  self.post(self.host,'/api/me/connections',dict(action='block',code=code));self.assertEqual(self.host.get('/api/me/profiles/'+code).status_code,404);self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])
  self.opt(self.guest,opted=False)
  with app.app_context():self.assertEqual(db().execute('SELECT COUNT(*) FROM discovery_leases').fetchone()[0],0)
 def test_reports_authorization_dedup_private_evidence_and_deleted_source(self):
  self.host.post(self.url,json=dict(action='chat',body='Reported synthetic text'));mid=self.guest.get(self.url).json['messages'][0]['id'];payload=dict(kind='room_message',reference=str(mid),category='harassment',explanation='Synthetic case')
  other=app.test_client();self.post(other,'/api/me/profile',dict(name='Other'));self.assertEqual(self.post(other,'/api/me/reports',payload).status_code,404)
  r=self.post(self.guest,'/api/me/reports',payload);self.assertEqual(r.status_code,201,r.text);identifier=r.json['id'];self.assertEqual(self.post(self.guest,'/api/me/reports',payload).json['id'],identifier)
  self.assertEqual(self.guest.post('/ops/solace/safety/evidence/'+identifier,json={}).status_code,404)
  c,csrf,_=self.staff();e=c.post('/ops/solace/safety/evidence/'+identifier,json=dict(confirmed=True,reason='Review reported message content'),headers={'X-CSRF-Token':csrf});self.assertEqual(e.status_code,200,e.text);self.assertEqual(e.json['evidence']['body'],'Reported synthetic text')
  self.host.post(self.url+'/leave',json={});self.guest.post(self.url+'/leave',json={});e=c.post('/ops/solace/safety/evidence/'+identifier,json=dict(confirmed=True,reason='Verify evidence after deletion'),headers={'X-CSRF-Token':csrf});self.assertEqual(e.json['evidence']['body'],'Reported synthetic text')
 def test_named_staff_roles_totp_replay_last_admin_and_audit(self):
  self.assertEqual(totp(base64.b32encode(b'12345678901234567890').decode(),59,8),'94287082')
  c,csrf,sid=self.staff();self.assertEqual(c.get('/ops/solace/safety/audit').status_code,200)
  r=c.post('/ops/solace/staff',json=dict(id=sid,role='moderator',enabled=True,confirmed=True,reason='Try removing final administrator'),headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,409)
  other,token,_=self.staff('operations','operator');self.assertEqual(other.get('/ops/solace/safety/reports').status_code,403);self.assertEqual(self.action(other,token,dict(action='ban',code=self.code(self.host))).status_code,403)
  with app.app_context():
   with self.assertRaises(sqlite3.IntegrityError):db().execute('DELETE FROM safety_audit')
   db().rollback()
 def test_moderation_emergency_switches_appeal_and_reverse(self):
  c,csrf,_=self.staff();code=self.code(self.guest)
  self.assertEqual(self.action(c,csrf,dict(action='mute',code=code)).status_code,200)
  self.assertEqual(self.guest.post(self.url,json=dict(action='chat',body='blocked')).status_code,403);self.assertEqual(self.host.post(self.url,json=dict(action='chat',body='allowed')).status_code,200)
  own=self.guest.get('/api/me/safety').json['restrictions'];self.assertEqual(len(own),1)
  self.assertEqual(self.post(self.guest,'/api/me/safety',dict(restriction=own[0]['id'],body='Please reconsider this synthetic restriction')).status_code,200)
  self.assertEqual(self.action(c,csrf,dict(action='reverse',id=own[0]['id'])).status_code,200);self.assertEqual(self.guest.post(self.url,json=dict(action='chat',body='allowed')).status_code,200)
  r=c.post('/ops/solace/safety/switches',json=dict(name='room_creation',paused=True,confirmed=True,reason='Temporary capacity maintenance'),headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200);self.assertEqual(self.host.post('/api/rooms',json={}).status_code,403);self.assertEqual(self.host.get(self.url).status_code,200)
 def test_ban_removes_members_and_discovery(self):
  self.opt(self.guest);self.pulse(self.guest);c,csrf,_=self.staff();self.assertEqual(self.action(c,csrf,dict(action='ban',code=self.code(self.guest))).status_code,200)
  self.assertEqual(self.guest.get(self.url).status_code,403);self.assertEqual(self.guest.get('/api/me/safety').status_code,200);self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])
 def test_new_public_pages_metadata_and_private_exclusions(self):
  old=app.config.get('SOLACE_PUBLIC_URL');app.config['SOLACE_PUBLIC_URL']='https://solace.example'
  try:
   for path in ['/watch-together','/watch-rooms','/friends-messaging','/open-world','/play-together','/community-guidelines']:
    r=self.host.get(path);self.assertEqual(r.status_code,200);self.assertIn('https://solace.example'+path,r.text);self.assertIn('index,follow',r.text)
   site=self.host.get('/sitemap.xml');self.assertIn('/open-world',site.text);self.assertNotIn('/world<',site.text);self.assertNotIn('/messages',site.text);self.assertIn('noindex',self.host.get('/world').text)
  finally:
   if old is None:app.config.pop('SOLACE_PUBLIC_URL',None)
   else:app.config['SOLACE_PUBLIC_URL']=old

 def test_all_report_target_types_and_staff_evidence_privacy(self):
  hc=self.code(self.host);gc=self.code(self.guest);self.post(self.host,'/api/me/connections',dict(action='request',code=gc));self.post(self.guest,'/api/me/connections',dict(action='accept',code=hc));cid=self.post(self.host,'/api/me/conversations',dict(code=gc)).json['id'];path='/api/me/conversations/'+cid
  mid=self.post(self.host,path,dict(body='Private synthetic evidence',request_id=uuid.uuid4().hex)).json['message']['id']
  from PIL import Image
  raw=io.BytesIO();Image.new('RGB',(30,20),'pink').save(raw,'PNG');up=self.host.post('/api/me/media',data={'scope':'dm','scope_id':cid,'upload_key':uuid.uuid4().hex,'picture':(io.BytesIO(raw.getvalue()),'synthetic.png')},headers={'X-CSRF-Token':self.host.get('/api/me').json['csrf']});self.assertEqual(up.status_code,201)
  media=up.json['media']['id'];self.post(self.host,path,dict(body='Picture',request_id=uuid.uuid4().hex,media_id=media))
  invitation_room=self.host.post('/api/rooms',json={}).json['id'];self.host.post('/api/rooms/'+invitation_room,json={'action':'join'});invitation=self.post(self.host,'/api/me/invitations',dict(action='send',room=invitation_room,code=gc));self.assertEqual(invitation.status_code,200)
  invite=self.guest.get('/api/me/invitations').json['invitations'][0]['id'];self.host.post(self.url,json=dict(action='chat',body='Room evidence'));roommid=self.guest.get(self.url).json['messages'][0]['id']
  targets=[('profile',hc),('user',hc),('dm',str(mid)),('attachment',media),('room',self.url.rsplit('/',1)[1]),('invitation',invite),('room_message',str(roommid))]
  from contextlib import nullcontext
  with nullcontext():
   for kind,reference in targets[:6]:self.assertIn(self.post(self.guest,'/api/me/reports',dict(kind=kind,reference=reference,category='spam')).status_code,[200,201])
  # Seventh report exceeds the identity budget, never produces automatic punishment.
  self.assertEqual(self.post(self.guest,'/api/me/reports',dict(kind=targets[-1][0],reference=targets[-1][1],category='spam')).status_code,429)
  self.assertEqual(self.host.get(self.url).status_code,200)
  outsider=app.test_client();self.post(outsider,'/api/me/profile',dict(name='Outsider'));self.assertEqual(self.post(outsider,'/api/me/reports',dict(kind='dm',reference=str(mid),category='spam')).status_code,404)
  c,csrf,_=self.staff();listed=c.get('/ops/solace/safety/reports');self.assertNotIn('Private synthetic evidence',listed.text);self.assertEqual(c.get('/ops/solace/safety/inventory/messaging').status_code,200);self.assertNotIn('Private synthetic evidence',c.get('/ops/solace/safety/inventory/messaging').text);self.assertNotIn('a',c.get('/ops/solace/safety/inventory/messaging').json['items'][0]);self.assertNotIn('sender',c.get('/ops/solace/safety/inventory/connections').json['items'][0]);self.assertNotIn(self.url.rsplit('/',1)[1],c.get('/ops/solace/safety/inventory/rooms').text)
 def test_report_block_separates_rooms_and_disconnects_messages(self):
  hc=self.code(self.host);gc=self.code(self.guest);self.post(self.host,'/api/me/connections',dict(action='request',code=gc));self.post(self.guest,'/api/me/connections',dict(action='accept',code=hc))
  r=self.post(self.guest,'/api/me/reports',dict(kind='profile',reference=hc,category='harassment',block=True));self.assertEqual(r.status_code,201);retry=self.post(self.guest,'/api/me/reports',dict(kind='profile',reference=hc,category='harassment',block=True));self.assertEqual(retry.status_code,200);self.assertEqual(retry.json['id'],r.json['id']);self.assertEqual(self.guest.get(self.url).status_code,403);self.assertEqual(self.post(self.host,'/api/me/conversations',dict(code=gc)).status_code,403)
 def test_invalid_payloads_are_rejected_not_server_errors(self):
  for path in ['/api/me/discovery','/api/me/discovery/presence','/api/me/reports','/api/me/safety']:
   self.assertEqual(self.post(self.host,path,[]).status_code,400,path)
  self.assertEqual(self.post(self.host,'/api/me/reports',dict(kind='profile',reference=self.code(self.guest),category=[])).status_code,400)
 def test_switches_and_feature_restrictions_independent(self):
  c,csrf,_=self.staff()
  for name in ['messaging','uploads','discovery','invitations','registrations']:
   r=c.post('/ops/solace/safety/switches',json=dict(name=name,paused=True,confirmed=True,reason='Synthetic independent emergency pause'),headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200)
  self.assertEqual(self.host.post(self.url,json=dict(action='chat',body='paused')).status_code,403);self.assertEqual(self.host.get(self.url).status_code,200);self.assertEqual(self.opt(self.host,opted=False).status_code,200);self.assertEqual(self.host.get('/api/me/discovery/people').status_code,403)
  self.assertEqual(self.post(self.host,'/api/auth/signup',dict(name='Host',email='synthetic@example.test',password='Synthetic-Password-2026',accept_terms=True)).status_code,403)
  # Host still controls playback while messages are paused.
  self.assertEqual(self.host.post(self.url,json=dict(action='playback',position=15,playing=True)).status_code,200)
 def test_account_revocation_keeps_banned_identity_for_appeal(self):
  self.assertEqual(self.post(self.guest,'/api/auth/signup',dict(name='Guest',email='guest@example.test',password='Synthetic-Password-2026!',accept_terms=True)).status_code,200);code=self.code(self.guest);c,csrf,_=self.staff();self.assertEqual(self.action(c,csrf,dict(action='ban',code=code)).status_code,200)
  self.assertEqual(self.guest.get(self.url).status_code,403);self.assertEqual(self.guest.get('/home').status_code,303);restrictions=self.guest.get('/api/me/safety').json['restrictions'];self.assertEqual(restrictions[0]['kind'],'ban')
  self.assertEqual(self.post(self.guest,'/api/me/safety',dict(restriction=restrictions[0]['id'],body='Please reconsider this test-only account ban')).status_code,200)
 def test_guest_upgrade_preserves_discovery_identity(self):
  self.opt(self.guest);code=self.code(self.guest);self.pulse(self.guest)
  self.assertEqual(self.post(self.guest,'/api/auth/signup',dict(name='Guest',email='upgrade@example.test',password='Synthetic-Password-2026!',accept_terms=True)).status_code,200);self.assertEqual(self.code(self.guest),code);self.assertTrue(self.guest.get('/api/me/discovery').json['settings']['opted'])
 def test_totp_replay_and_staff_session_revocation(self):
  c,csrf,sid=self.staff();secret=base64.b32encode(b'12345678901234567890').decode();other=app.test_client();page=other.get('/ops/solace');token=re.search(r'name="csrf" value="([^"]+)"',page.text)[1];self.assertEqual(other.post('/ops/solace',data=dict(username='owner',password='Synthetic-Staff-Password-2026!',otp=totp(secret),csrf=token)).status_code,401)
  operator,_,oid=self.staff('operations','worker');r=c.post('/ops/solace/staff',json=dict(id=oid,role='operations',enabled=False,confirmed=True,reason='Revoke synthetic staff access'),headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200);self.assertEqual(operator.get('/ops/solace/data').status_code,401)
  self.assertTrue(c.get('/ops/solace/safety/audit').json['verified'])
 def test_evidence_expiry_and_maintenance(self):
  r=self.post(self.guest,'/api/me/reports',dict(kind='profile',reference=self.code(self.host),category='spam'));identifier=r.json['id'];c,csrf,_=self.staff()
  with app.app_context():db().execute('UPDATE safety_reports SET evidence_until=0');db().commit()
  e=c.post('/ops/solace/safety/evidence/'+identifier,json=dict(reason='Review expired evidence snapshot',confirmed=True),headers={'X-CSRF-Token':csrf});self.assertIsNone(e.json['evidence'])
  from tools.maintenance import cleanup
  result=cleanup(app.instance_path);self.assertEqual(result['expired_evidence'],1)
 def test_presence_cap_and_revoked_account_lease(self):
  self.opt(self.guest)
  for _ in range(8):self.assertEqual(self.pulse(self.guest).status_code,200)
  self.assertEqual(self.pulse(self.guest).status_code,429)
  self.post(self.guest,'/api/auth/signup',dict(name='Guest',email='lease@example.test',password='Synthetic-Password-2026!',accept_terms=True));self.opt(self.guest,opted=False);self.opt(self.guest);self.pulse(self.guest)
  with app.app_context():db().execute('DELETE FROM account_sessions');db().commit()
  self.assertEqual(self.host.get('/api/me/discovery/people').json['people'],[])

 def test_simultaneous_reports_are_idempotent(self):
  from concurrent.futures import ThreadPoolExecutor
  csrf=self.guest.get('/api/me').json['csrf'];cookie=self.guest.get_cookie('session').value;code=self.code(self.host)
  def submit(_):
   c=app.test_client();c.set_cookie('session',cookie);r=c.post('/api/me/reports',json=dict(kind='profile',reference=code,category='spam'),headers={'X-CSRF-Token':csrf});return r.status_code,r.json
  with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(submit,range(2)))
  self.assertEqual(sorted(r[0] for r in results),[200,201]);self.assertEqual(results[0][1]['id'],results[1][1]['id'])

 def test_direct_world_entry_initializes_profile_without_visiting_friends(self):
  newcomer=app.test_client();self.post(newcomer,'/api/me/profile',dict(name='Newcomer'));self.assertEqual(self.opt(newcomer).status_code,200);self.assertEqual(self.pulse(newcomer).status_code,200);self.assertIn('Newcomer',[p['name'] for p in self.host.get('/api/me/discovery/people').json['people']])
 def test_discovery_avatar_and_stats_are_separate_explicit_grants(self):
  from PIL import Image
  raw=io.BytesIO();Image.new('RGB',(30,20),'pink').save(raw,'PNG');r=self.guest.post('/api/me/avatar',data={'picture':(io.BytesIO(raw.getvalue()),'picture.png')},headers={'X-CSRF-Token':self.guest.get('/api/me').json['csrf']});self.assertEqual(r.status_code,200,r.text)
  self.opt(self.guest);self.pulse(self.guest);code=self.code(self.guest);p=self.host.get('/api/me/profiles/'+code).json['profile'];self.assertEqual(p['avatar'],'/static/default-avatar.svg');self.assertIsNone(p['stats']);self.assertEqual(self.host.get('/api/me/profiles/'+code+'/avatar').status_code,404)
  self.opt(self.guest,avatar=True,stats=True);p=self.host.get('/api/me/profiles/'+code).json['profile'];self.assertIn('/profiles/',p['avatar']);self.assertEqual(self.host.get(p['avatar']).status_code,200);self.assertEqual(set(p['stats']),{'sessions','seconds'})
  self.opt(self.guest,opted=False);self.assertEqual(self.host.get(p['avatar']).status_code,404)

 def test_pagination_cursor_is_bound_without_disclosing_identity(self):
  from itsdangerous import URLSafeTimedSerializer
  for number in range(13):
   c=app.test_client();self.post(c,'/api/me/profile',dict(name='Person '+str(number)));self.opt(c);self.pulse(c)
  first=self.host.get('/api/me/discovery/people').json;self.assertEqual(len(first['people']),12);cursor=first['cursor'];self.assertTrue(cursor);second=self.host.get('/api/me/discovery/people?cursor='+cursor).json;self.assertEqual(len(second['people']),1);self.assertFalse(set(p['code'] for p in first['people'])&set(p['code'] for p in second['people']))
  self.assertEqual(self.guest.get('/api/me/discovery/people?cursor='+cursor).status_code,400);self.assertEqual(self.host.get('/api/me/discovery/people?cursor='+cursor+'x').status_code,400)
  decoded=URLSafeTimedSerializer(app.secret_key,salt='people-cursor').loads(cursor)
  with self.host.session_transaction() as state:self.assertNotEqual(decoded['viewer'],state['uid']);self.assertNotIn(state['uid'],json.dumps(decoded))
 def test_background_beacon_removes_only_its_tab(self):
  self.opt(self.guest);a=uuid.uuid4().hex;b=uuid.uuid4().hex;self.pulse(self.guest,a);self.pulse(self.guest,b);token=self.guest.get('/api/me').json['csrf'];r=self.guest.post('/api/me/discovery/presence',data=dict(csrf=token,tab=a,active='0'));self.assertEqual(r.status_code,200);self.assertEqual(len(self.host.get('/api/me/discovery/people').json['people']),1)

 def test_revoke_guest_sessions_invalidates_copied_guest_identity(self):
  code=self.code(self.guest);token=self.guest.get('/api/me').json['csrf'];cookie=self.guest.get_cookie('session').value;c,csrf,_=self.staff();self.assertEqual(self.action(c,csrf,dict(action='revoke_sessions',code=code)).status_code,200)
  copied=app.test_client();copied.set_cookie('session',cookie)
  self.assertEqual(copied.get('/api/me/connections').status_code,401);self.assertEqual(self.guest.get(self.url).status_code,401);self.assertIsNone(copied.get('/api/me').json['profile'])

 def test_existing_storage_change_and_audit_commit_together(self):
  c,csrf,_=self.staff();old=c.get('/ops/solace/storage').json['default_mib']
  def unavailable(*args,**kwargs):raise RuntimeError('Synthetic audit failure')
  with patch.dict(app.extensions['solace_safety'],{'audit':unavailable}):
   with self.assertRaises(RuntimeError):c.post('/ops/solace/storage',json=dict(limit_mib=75,confirmed=True,reason='Synthetic atomic settings check'),headers={'X-CSRF-Token':csrf})
  self.assertEqual(c.get('/ops/solace/storage').json['default_mib'],old)
  r=c.post('/ops/solace/storage',json=dict(limit_mib=75,confirmed=True,reason='Synthetic atomic settings check'),headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200);self.assertEqual(r.json['default_mib'],75);self.assertEqual(c.get('/ops/solace/safety/audit').json['events'][0]['action'],'operations_setting')

if __name__=='__main__':unittest.main()
