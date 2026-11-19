import io,time,uuid,unittest
from PIL import Image
from app import app,db
import test_app
import test_safety

class CommunityTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,c,path,data=None,method='POST'):return c.open(path,method=method,json=data,headers={'X-CSRF-Token':c.get('/api/me').json['csrf']})
 code=test_safety.SafetyTests.code
 staff=test_safety.SafetyTests.staff
 action=test_safety.SafetyTests.action
 def join(self,c):return self.post(c,'/api/me/preferences',{'world_choice':'joined'})
 def send(self,c,text='Hello everyone',key=None,media=None):return self.post(c,'/api/me/world/messages',dict(body=text,request_id=key or uuid.uuid4().hex,media_id=media))
 def pulse(self,c,tab=None,active=True):return self.post(c,'/api/me/world/presence',dict(tab=tab or uuid.uuid4().hex,active=active))
 def test_default_once_choice_and_saved_preferences_upgrade(self):
  self.assertEqual(self.host.get('/api/me/preferences').json['preferences']['world_choice'],'unset');self.assertEqual(self.send(self.host).status_code,403)
  self.post(self.host,'/api/me/preferences',dict(world_choice='skipped',haptics=False,rhythm=False,rotation=False,theme='rose',in_app_alerts=False));self.assertEqual(self.host.get('/api/me/preferences').json['preferences']['world_choice'],'skipped');self.assertEqual(self.send(self.host).status_code,403)
  self.post(self.host,'/api/auth/signup',dict(name='Host',email='community@example.test',password='Synthetic-Password-2026!',accept_terms=True));p=self.host.get('/api/me/preferences').json['preferences'];self.assertEqual(p['theme'],'rose');self.assertEqual(p['world_choice'],'skipped');self.assertFalse(p['rotation']);self.assertTrue(p['experience_saved']);self.assertFalse(p['in_app_alerts'])
 def test_strangers_chat_and_retry_private_messages_still_require_friends(self):
  for c in [self.host,self.guest]:self.join(c)
  key=uuid.uuid4().hex;r=self.send(self.host,key=key);self.assertEqual(r.status_code,201);self.assertEqual(self.send(self.host,key=key).json['message']['id'],r.json['message']['id']);self.assertEqual(self.send(self.host,'different',key=key).status_code,409)
  self.assertEqual(self.guest.get('/api/me/world/messages').json['messages'][0]['body'],'Hello everyone');self.assertEqual(self.post(self.host,'/api/me/conversations',dict(code=self.code(self.guest))).status_code,403)
  self.assertNotIn('email',r.json['message']);self.assertNotIn('sender',r.json['message'])
 def test_presence_unique_tabs_hide_expiry_and_visibility(self):
  for c in [self.host,self.guest]:self.join(c)
  a=uuid.uuid4().hex;b=uuid.uuid4().hex;self.pulse(self.host,a);self.pulse(self.host,b);self.pulse(self.guest);self.assertEqual(self.host.get('/api/me/world/messages').json['online'],2)
  self.pulse(self.host,a,False);self.assertEqual(self.host.get('/api/me/world/messages').json['online'],2);self.pulse(self.host,b,False);self.assertEqual(self.host.get('/api/me/world/messages').json['online'],1)
  self.post(self.guest,'/api/me/preferences',dict(world_visible=False));self.assertEqual(self.host.get('/api/me/world/messages').json['online'],0)
  self.post(self.guest,'/api/me/preferences',dict(world_visible=True));self.pulse(self.guest)
  with app.app_context():db().execute('UPDATE world_presence SET expires=0');db().commit()
  self.assertEqual(self.host.get('/api/me/world/messages').json['online'],0)
 def test_block_hides_history_count_and_public_media(self):
  for c in [self.host,self.guest]:self.join(c);self.pulse(c)
  self.send(self.host);before=self.guest.get('/api/me/world/messages').json['revision'];self.post(self.guest,'/api/me/connections',dict(action='block',code=self.code(self.host)));r=self.guest.get('/api/me/world/messages').json;self.assertEqual(r['messages'],[]);self.assertEqual(r['online'],1);self.assertNotEqual(r['revision'],before)
 def upload(self,c,animated=False):
  raw=io.BytesIO();Image.new('RGB',(24,20),'pink').save(raw,'GIF' if animated else 'PNG',**({'save_all':True,'append_images':[Image.new('RGB',(24,20),'purple')],'duration':150,'loop':0} if animated else {}))
  return c.post('/api/me/media',data=dict(scope='world',scope_id='community',upload_key=uuid.uuid4().hex,picture=(io.BytesIO(raw.getvalue()),'photo.gif' if animated else 'photo.png')),headers={'X-CSRF-Token':c.get('/api/me').json['csrf']})
 def test_upload_uses_existing_validation_gif_permissions_and_removal(self):
  self.assertEqual(self.upload(self.host).status_code,403);self.join(self.host);r=self.upload(self.host,True);self.assertEqual(r.status_code,201,r.text);media=r.json['media'];self.assertEqual(self.guest.get(media['url']).status_code,404)
  sent=self.send(self.host,'A GIF',media=media['id']);self.assertEqual(sent.status_code,201);self.assertEqual(self.guest.get(media['url']).status_code,200)
  with Image.open(io.BytesIO(self.guest.get(media['url']).data)) as image:self.assertEqual(image.n_frames,2)
  anonymous=app.test_client();self.assertEqual(anonymous.get(media['url']).status_code,401);self.assertEqual(self.post(self.guest,media['url'],method='DELETE').status_code,403)
  revision=self.guest.get('/api/me/world/messages').json['revision'];self.post(self.host,media['url'],method='DELETE');self.assertNotEqual(self.guest.get('/api/me/world/messages').json['revision'],revision)
 def test_reporting_and_moderation_use_existing_dashboard(self):
  self.join(self.host);r=self.send(self.host,'Reported public message');mid=r.json['message']['id'];report=self.post(self.guest,'/api/me/reports',dict(kind='world_message',reference=str(mid),category='harassment'));self.assertEqual(report.status_code,201,report.text)
  staff,csrf,_=self.staff();ev=staff.post('/ops/solace/safety/evidence/'+report.json['id'],json=dict(confirmed=True,reason='Review synthetic community report'),headers={'X-CSRF-Token':csrf});self.assertEqual(ev.json['evidence']['body'],'Reported public message')
  self.assertEqual(self.action(staff,csrf,dict(action='remove',kind='world_message',id=str(mid))).status_code,200);self.assertTrue(self.guest.get('/api/me/world/messages').json['messages'][0]['deleted'])
  self.assertEqual(self.action(staff,csrf,dict(action='mute',code=self.code(self.host))).status_code,200);self.assertEqual(self.send(self.host).status_code,403);self.assertEqual(self.host.get('/api/me/world/messages').status_code,200)
 def test_unauthorized_delete_preferences_validation_and_csrf(self):
  self.join(self.host);mid=self.send(self.host).json['message']['id'];self.assertEqual(self.post(self.guest,'/api/me/world/messages/'+str(mid),method='DELETE').status_code,404)
  for value in [[],{'world_visible':1},{'owner':'someone'},{'theme':'bad'}]:self.assertEqual(self.post(self.host,'/api/me/preferences',value).status_code,400)
  self.assertEqual(self.post(self.host,'/api/me/world/messages',[]).status_code,400);self.assertEqual(self.host.post('/api/me/world/messages',json={}).status_code,403)
  r=self.host.get('/world');self.assertIn('noindex',r.headers['X-Robots-Tag']);self.assertIn('no-store',r.headers['Cache-Control'])
 def test_public_chat_does_not_change_stream_or_room_chat(self):
  self.host.post(self.url,json=dict(action='playback',playing=True,position=42));before=self.host.get(self.url).json;self.join(self.host);self.send(self.host,'Public hello');after=self.guest.get(self.url).json;self.assertEqual(before['playback_revision'],after['playback_revision']);self.assertEqual(before['playback_id'],after['playback_id']);self.assertEqual(after['messages'],[]);self.assertTrue(after['playing'])
 def test_history_pagination_cleanup_and_owned_tombstones(self):
  self.join(self.host)
  for i in range(3):self.send(self.host,'Message '+str(i))
  messages=self.guest.get('/api/me/world/messages').json['messages'];self.assertEqual(len(self.guest.get('/api/me/world/messages?before='+str(messages[-1]['id'])).json['messages']),2);self.assertEqual(len(self.guest.get('/api/me/world/messages?after='+str(messages[0]['id'])).json['messages']),2)
  self.post(self.host,'/api/me/world/messages/'+str(messages[0]['id']),method='DELETE');self.assertTrue(self.guest.get('/api/me/world/messages').json['messages'][0]['deleted'])
  with app.app_context():db().execute('UPDATE world_messages SET created=0');db().commit()
  from tools.maintenance import cleanup
  self.assertEqual(cleanup(app.instance_path)['world_messages'],3);self.assertEqual(self.host.get('/api/me/world/messages').json['messages'],[])
 def test_session_revocation_removes_account_presence(self):
  self.join(self.host);self.post(self.host,'/api/auth/signup',dict(name='Host',email='presence@example.test',password='Synthetic-Password-2026!',accept_terms=True));self.pulse(self.host);self.assertEqual(self.guest.get('/api/me/world/messages').json['online'],1)
  with app.app_context():db().execute('DELETE FROM account_sessions');db().commit()
  self.assertEqual(self.guest.get('/api/me/world/messages').json['online'],0)

 def test_intro_claim_is_once_even_after_refresh_or_parallel_tabs(self):
  from concurrent.futures import ThreadPoolExecutor
  token=self.host.get('/api/me').json['csrf'];cookie=self.host.get_cookie('session').value
  def claim(_):
   c=app.test_client();c.set_cookie('session',cookie);return c.post('/api/me/preferences/world-intro',json={},headers={'X-CSRF-Token':token}).json
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,range(2)))
  self.assertEqual(sum(r['show_intro'] for r in results),1);self.assertEqual(self.host.get('/api/me/preferences').json['preferences']['world_choice'],'skipped');self.assertFalse(self.post(self.host,'/api/me/preferences/world-intro',{}).json['show_intro']);self.assertEqual(self.send(self.host).status_code,403)

 def test_community_works_without_a_room_or_friendship(self):
  outsider=app.test_client();self.post(outsider,'/api/me/profile',dict(name='A visitor'));self.join(outsider);self.assertEqual(self.send(outsider,'A room is optional').status_code,201);self.assertEqual(self.host.get('/api/me/world/messages').json['messages'][0]['body'],'A room is optional');self.assertEqual(outsider.get('/api/me/connections').json['friends'],[])

if __name__=='__main__':unittest.main()
