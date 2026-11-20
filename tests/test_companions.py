import io,time,unittest,uuid
from PIL import Image
from app import app,db
import test_app

class CompanionTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,c,path,data):return c.post(path,json=data,headers={'X-CSRF-Token':c.get('/api/me').json['csrf']})
 def code(self,c):return c.get('/api/me/connections').json['friend_code']
 def friends(self):
  self.post(self.host,'/api/me/connections',dict(action='request',code=self.code(self.guest)))
  self.post(self.guest,'/api/me/connections',dict(action='accept',code=self.code(self.host)))
 def test_room_reactions_receipts_and_authorization(self):
  for c in [self.host,self.guest]:self.post(c,'/api/me/privacy',dict(share_read=True))
  self.host.post(self.url,json=dict(action='chat',body='Hello'));mid=self.host.get(self.url).json['messages'][-1]['id'];data=dict(scope='room',target=self.url.split('/')[-1],ids=[mid])
  self.assertEqual(self.post(self.guest,'/api/me/chat/actions',{**data,'read':True}).status_code,200)
  self.assertEqual(self.host.get('/api/me/chat/actions',query_string={**data,'ids':str(mid)}).json['messages'][0]['read_count'],1)
  self.assertEqual(self.post(self.guest,'/api/me/chat/actions',{**data,'message':mid,'emoji':'❤️'}).json['messages'][0]['reactions'][0]['count'],1)
  self.assertEqual(self.post(self.guest,'/api/me/chat/actions',{**data,'message':mid,'emoji':'❤️'}).json['messages'][0]['reactions'],[])
  outsider=app.test_client();self.post(outsider,'/api/me/profile',dict(name='Outsider'));self.assertEqual(self.post(outsider,'/api/me/chat/actions',data).status_code,403)
  self.assertEqual(self.post(self.host,'/api/me/chat/actions',{**data,'message':mid,'emoji':'bad'}).status_code,400)
 def test_receipts_respect_saved_choice(self):
  self.host.post(self.url,json=dict(action='chat',body='Private read'));mid=self.host.get(self.url).json['messages'][-1]['id'];d=dict(scope='room',target=self.url.split('/')[-1],ids=[mid],read=True)
  self.post(self.guest,'/api/me/chat/actions',d);self.assertEqual(self.post(self.host,'/api/me/chat/actions',d).json['messages'][0]['read_count'],0)
 def test_standalone_games_reuse_authoritative_rules_without_stream_room(self):
  self.friends()
  with app.app_context():before=db().execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
  for kind,endpoint in [('hearts','game'),('hoops','basketball'),('ludo','ludo')]:
   r=self.post(self.host,'/api/me/play',dict(kind=kind));self.assertEqual(r.status_code,201,r.text);gid=r.json['next'].split('/')[-1];url='/api/rooms/'+gid+'/'+endpoint
   self.assertEqual(self.guest.get(url).status_code,403)
   self.assertEqual(self.post(self.host,'/api/me/play/'+gid,dict(code=self.code(self.guest))).status_code,200)
   notices=self.guest.get('/api/me/notifications').json['events'];inv=next(n for n in notices if n['kind']=='game' and n['id'])
   self.assertEqual(self.post(self.guest,'/api/me/play-invitations/'+inv['reference'],dict(action='accept')).status_code,200)
   self.assertEqual(self.host.post(url,json=dict(action='join')).status_code,200);self.assertEqual(self.guest.post(url,json=dict(action='join')).status_code,200)
   self.assertEqual(len(self.host.get(url).json['players']),2)
   self.assertEqual(self.host.get('/play/'+gid).status_code,200)
  with app.app_context():self.assertEqual(db().execute('SELECT COUNT(*) FROM rooms').fetchone()[0],before)
 def test_game_invites_require_friends_and_enforce_blocks(self):
  gid=self.post(self.host,'/api/me/play',dict(kind='hearts')).json['next'].split('/')[-1]
  self.assertEqual(self.post(self.host,'/api/me/play/'+gid,dict(code=self.code(self.guest))).status_code,403);self.friends();self.post(self.host,'/api/me/play/'+gid,dict(code=self.code(self.guest)));self.assertEqual(self.post(self.host,'/api/me/play/'+gid,dict(code=self.code(self.guest))).status_code,409)
  notice=next(n for n in self.guest.get('/api/me/notifications').json['events'] if n['kind']=='game');self.post(self.guest,'/api/me/notifications',dict(id=notice['id']));self.assertEqual(len(self.guest.get('/api/me/play-invitations').json['invitations']),1);self.post(self.guest,'/api/me/connections',dict(action='block',code=self.code(self.host)));self.assertEqual(self.post(self.guest,'/api/me/play-invitations/'+notice['reference'],dict(action='accept')).status_code,403)
 def test_notification_claims_private_and_deduplicated(self):
  self.post(self.host,'/api/me/connections',dict(action='request',code=self.code(self.guest)));events=self.guest.get('/api/me/notifications').json['events'];self.assertEqual(events[0]['kind'],'request');self.assertNotIn('email',events[0]);self.assertNotIn('body',events[0]);key=events[0]['id']
  self.assertFalse(self.post(self.host,'/api/me/notifications',dict(id=key)).json['claimed']);self.assertTrue(self.post(self.guest,'/api/me/notifications',dict(id=key)).json['claimed']);self.assertFalse(self.post(self.guest,'/api/me/notifications',dict(id=key)).json['claimed'])
 def test_moments_private_empty_and_timezone(self):
  d=self.host.get('/api/me/moments?timezone=Asia/Kolkata');self.assertEqual(d.status_code,200);self.assertEqual(len(d.json['days']),14);self.assertEqual(d.json['songs'],[]);self.assertEqual(self.host.get('/api/me/moments?timezone=bad/zone').status_code,400);self.assertEqual(app.test_client().get('/api/me/moments').status_code,401)
  for _ in range(2):
   self.host.post(self.url,json=dict(action='watch',url='aqz-KE-bpKQ'));self.post(self.host,'/api/me/watch',dict(room=self.url.split('/')[-1],active=True,title='Synthetic clip'));self.post(self.host,'/api/me/watch',dict(room=self.url.split('/')[-1],active=True,title='Synthetic clip'))
  d=self.host.get('/api/me/moments?timezone=Asia/Kolkata').json;self.assertEqual(sum(day['sessions'] for day in d['days']),2);self.assertEqual(d['songs'][0]['sessions'],2);self.assertEqual(d['people'][0]['name'],'Guest');self.assertEqual(d['people'][0]['sessions'],2)
 def test_world_reactions_and_gif_still_use_shared_pipeline(self):
  self.post(self.host,'/api/me/preferences',dict(world_choice='joined'));self.post(self.guest,'/api/me/preferences',dict(world_choice='joined'))
  raw=io.BytesIO();Image.new('RGB',(20,20),'pink').save(raw,'GIF',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')],duration=100,loop=0)
  uploaded=self.host.post('/api/me/media',data=dict(scope='world',scope_id='community',upload_key=uuid.uuid4().hex,picture=(io.BytesIO(raw.getvalue()),'sample.gif')),headers={'X-CSRF-Token':self.host.get('/api/me').json['csrf']});self.assertEqual(uploaded.status_code,201,uploaded.text)
  mid=self.post(self.host,'/api/me/world/messages',dict(body='GIF',media_id=uploaded.json['media']['id'],request_id=uuid.uuid4().hex)).json['message']['id']
  r=self.post(self.guest,'/api/me/chat/actions',dict(scope='world',target='community',ids=[mid],message=mid,emoji='✨'));self.assertEqual(r.status_code,200,r.text)
 def test_bad_payloads_and_csrf(self):
  for path in ['/api/me/play','/api/me/notifications','/api/me/chat/actions']:
   self.assertEqual(self.post(self.host,path,[]).status_code,400)
   self.assertEqual(self.host.post(path,json={}).status_code,403)
 def test_guest_upgrade_keeps_games_reactions_and_receipt_preferences(self):
  gid=self.post(self.host,'/api/me/play',dict(kind='hearts')).json['next'].split('/')[-1]
  self.post(self.host,'/api/me/privacy',dict(share_read=True));self.host.post(self.url,json=dict(action='chat',body='Saved reaction'));mid=self.host.get(self.url).json['messages'][-1]['id'];d=dict(scope='room',target=self.url.split('/')[-1],ids=[mid],message=mid,emoji='❤️');self.post(self.host,'/api/me/chat/actions',d)
  self.assertEqual(self.post(self.host,'/api/auth/signup',dict(name='Host',email='play-upgrade@example.test',password='Synthetic-Password-2026!',accept_terms=True)).status_code,200)
  self.assertEqual(self.host.get('/play/'+gid).status_code,200);self.assertTrue(self.host.get('/api/me/privacy').json['share_read']);self.assertEqual(self.post(self.host,'/api/me/chat/actions',{**d,'emoji':'✨'}).json['messages'][0]['reactions'][0]['emoji'],'✨')
 def test_multi_tab_notification_claim_is_atomic(self):
  from concurrent.futures import ThreadPoolExecutor
  self.post(self.host,'/api/me/connections',dict(action='request',code=self.code(self.guest)));event=self.guest.get('/api/me/notifications').json['events'][0]['id'];token=self.guest.get('/api/me').json['csrf'];cookie=self.guest.get_cookie('session').value
  def claim(_):
   c=app.test_client();c.set_cookie('session',cookie);return c.post('/api/me/notifications',json=dict(id=event),headers={'X-CSRF-Token':token}).json['claimed']
  with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(claim,range(2)))
  self.assertEqual(sum(values),1)
 def test_chat_avatars_enforce_membership_and_sharing(self):
  raw=io.BytesIO();Image.new('RGB',(20,20),'pink').save(raw,'PNG');self.host.post('/api/me/avatar',data=dict(picture=(io.BytesIO(raw.getvalue()),'avatar.png')),headers={'X-CSRF-Token':self.host.get('/api/me').json['csrf']});self.host.post(self.url,json=dict(action='chat',body='Photo'));mid=self.host.get(self.url).json['messages'][-1]['id'];query=dict(scope='room',target=self.url.split('/')[-1],ids=str(mid));photo=self.guest.get('/api/me/chat/actions',query_string=query).json['messages'][0]['avatar']
  self.assertEqual(self.guest.get(photo).mimetype,'image/png');self.assertEqual(app.test_client().get(photo).status_code,401)
  self.post(self.host,'/api/me/privacy',dict(share_avatar=False));self.assertEqual(self.guest.get('/api/me/chat/actions',query_string=query).json['messages'][0]['avatar'],'/static/default-avatar.svg');self.assertEqual(self.guest.get(photo).status_code,302)
 def test_settings_have_one_script_owner_and_room_tools_are_management_only(self):
  html=self.host.get('/settings').text
  for name in ['haptic-core.js','haptics.js','chat-themes.js']:self.assertEqual(html.count('/static/'+name),1)
  self.assertIn('id="spaceThemes"',html);self.assertIn('id="prefAlerts"',html)
  tools=self.host.get('/room-control?room='+self.url.split('/')[-1]).text;self.assertNotIn('mode=room',tools);self.assertNotIn('id="spaceThemes"',tools);self.assertIn('id="roomSettingsForm"',tools)
