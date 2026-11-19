import io,unittest,uuid,time
from unittest.mock import patch
from PIL import Image
import test_app
from app import app,db

class MessagingTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,c,path,data=None,method='POST',**kw):return c.open(path,method=method,json=data,headers={'X-CSRF-Token':c.get('/api/me').json['csrf']},**kw)
 def code(self,c):return c.get('/api/me/connections').json['friend_code']
 def connect(self):
  self.post(self.host,'/api/me/connections',{'action':'request','code':self.code(self.guest)})
  self.assertEqual(self.post(self.guest,'/api/me/connections',{'action':'accept','code':self.code(self.host)}).status_code,200)
 def chat(self):
  self.connect();r=self.post(self.host,'/api/me/conversations',{'code':self.code(self.guest)});self.assertEqual(r.status_code,200);return '/api/me/conversations/'+r.json['id']
 def send(self,path,text='Hello',c=None,rid=None,media=None):return self.post(c or self.host,path,{'body':text,'request_id':rid or uuid.uuid4().hex,'media_id':media})
 def image(self,animated=False):
  out=io.BytesIO()
  if animated:Image.new('RGB',(40,30),'red').save(out,'GIF',save_all=True,append_images=[Image.new('RGB',(40,30),'blue')],duration=[120,180],loop=0)
  else:Image.new('RGB',(50,40),'pink').save(out,'PNG')
  return out.getvalue()
 def upload(self,c,scope,sid,raw=None,key=None):return c.post('/api/me/media',data={'scope':scope,'scope_id':sid,'upload_key':key or uuid.uuid4().hex,'picture':(io.BytesIO(raw if raw is not None else self.image()),'anything.exe')},headers={'X-CSRF-Token':c.get('/api/me').json['csrf']})
 def test_unnamed_room_default_and_later_host_rename(self):
  for visibility in ['private','public']:
   r=self.host.post('/api/rooms',json={'name':'','visibility':visibility,'confirm_public':True});self.assertEqual(r.status_code,201);path='/api/rooms/'+r.json['id'];self.host.post(path,json={'action':'join'});self.assertEqual(self.host.get(path).json['name'],'Host’s room')
   r=self.post(self.host,path+'/settings',{'action':'update','name':'Moonlit movie night'});self.assertEqual(r.json['name'],'Moonlit movie night')
 def test_short_codes_case_insensitive_preview_and_states(self):
  code=self.code(self.guest);self.assertEqual(len(code),8);self.assertNotRegex(code,'[01ILO]')
  preview=self.post(self.host,'/api/me/connections/preview',{'code':code[:4].lower()+'-'+code[4:].lower()});self.assertEqual(preview.json['profile']['name'],'Guest');self.assertEqual(preview.json['profile']['status'],'none')
  self.assertEqual(self.host.get('/api/me/connections').json['friends'],[])
  self.assertEqual(self.post(self.host,'/api/me/connections',{'action':'request','code':self.code(self.host)}).status_code,400)
  self.assertEqual(self.post(self.host,'/api/me/connections/preview',{'code':'BAD-CODE'}).status_code,404)
  self.post(self.host,'/api/me/connections',{'action':'request','code':code.lower()});self.assertEqual(self.post(self.host,'/api/me/connections',{'action':'request','code':code}).status_code,409)
  self.post(self.guest,'/api/me/connections',{'action':'decline','code':self.code(self.host)});self.assertEqual(self.host.get('/api/me/connections').json['declined'][0]['status'],'declined')
  self.post(self.host,'/api/me/connections',{'action':'remove','code':code});self.assertEqual(self.post(self.host,'/api/me/connections',{'action':'request','code':code}).status_code,429)
 def test_only_friends_open_one_conversation_and_room_independent(self):
  self.assertEqual(self.post(self.host,'/api/me/conversations',{'code':self.code(self.guest)}).status_code,403);path=self.chat();other=self.post(self.guest,'/api/me/conversations',{'code':self.code(self.host)});self.assertTrue(path.endswith(other.json['id']))
  self.host.post(self.url+'/leave',json={});self.guest.post(self.url+'/leave',json={});self.assertEqual(self.send(path).status_code,201)
  for c in [self.host,self.guest]:self.assertEqual(len(c.get('/api/me/conversations').json['conversations']),1)
 def test_empty_conversation_inbox_and_first_message_after_hiding(self):
  path=self.chat()
  for c in [self.host,self.guest]:
   inbox=c.get('/api/me/conversations');self.assertEqual(inbox.status_code,200);self.assertEqual(inbox.json['conversations'][0]['preview'],'Say hello')
  self.post(self.guest,path,method='DELETE');self.assertEqual(self.guest.get('/api/me/conversations').json['conversations'],[])
  self.send(path,'First hello');self.assertEqual(self.guest.get('/api/me/conversations').json['conversations'][0]['preview'],'First hello')
 def test_private_text_unread_typing_receipts_and_idempotent_retry(self):
  path=self.chat();rid=uuid.uuid4().hex;one=self.send(path,'A little hello',rid=rid);self.assertEqual(one.status_code,201);mid=one.json['message']['id'];self.assertEqual(self.send(path,'A little hello',rid=rid).json['message']['id'],mid);self.assertEqual(self.send(path,'Different',rid=rid).status_code,409)
  self.assertEqual(self.guest.get('/api/me/conversations').json['conversations'][0]['unread'],1)
  self.post(self.guest,path+'/state',{'typing':True,'read_id':mid});self.assertTrue(self.host.get(path).json['typing']);self.assertIsNone(self.host.get(path).json['read_id']);self.assertEqual(self.guest.get('/api/me/conversations').json['conversations'][0]['unread'],0)
  for c in [self.host,self.guest]:self.post(c,'/api/me/privacy',{'share_read':True})
  self.assertEqual(self.host.get(path).json['read_id'],mid);self.post(self.guest,path+'/state',{'typing':False});self.assertFalse(self.host.get(path).json['typing'])
 def test_unrelated_client_and_blocks_deny_reads_writes_and_media(self):
  path=self.chat();outsider=app.test_client();self.post(outsider,'/api/me/profile',{'name':'Outsider'});up=self.upload(self.host,'dm',path.rsplit('/',1)[1]);self.assertEqual(up.status_code,201);media=up.json['media'];self.send(path,media=media['id'])
  self.assertEqual(outsider.get(path).status_code,404);self.assertEqual(self.send(path,c=outsider).status_code,404);self.assertEqual(outsider.get(media['url']).status_code,404)
  self.assertEqual(self.guest.get(media['url']).status_code,200);self.post(self.host,'/api/me/connections',{'action':'block','code':self.code(self.guest)})
  self.assertEqual(self.guest.get(path).status_code,403);self.assertEqual(self.send(path,c=self.guest).status_code,403);self.assertEqual(self.guest.get(media['url']).status_code,403)
  self.assertEqual(self.post(self.host,media['url'],method='DELETE').status_code,200)
  mid=self.host.get('/api/me/conversations').json['conversations']
  self.assertEqual(mid,[])
 def test_room_media_permission_gif_animation_poster_and_host_removal(self):
  up=self.upload(self.guest,'room',self.url.rsplit('/',1)[1],self.image(True));self.assertEqual(up.status_code,201);m=up.json['media'];self.assertTrue(m['animated']);self.assertEqual(self.host.get(m['url']).status_code,404)
  body={'body':'Our GIF','media_id':m['id'],'request_id':uuid.uuid4().hex};endpoint='/api/me/room-media/'+self.url.rsplit('/',1)[1]+'/send';self.assertEqual(self.post(self.guest,endpoint,body).status_code,201);self.assertEqual(self.post(self.guest,endpoint,body).status_code,200)
  response=self.host.get(m['url']);self.assertIn('no-store',response.headers['Cache-Control'])
  with Image.open(io.BytesIO(response.data)) as img:self.assertEqual(img.n_frames,2);self.assertEqual(img.format,'GIF')
  self.assertEqual(self.host.get(m['poster']).mimetype,'image/jpeg');self.assertEqual(self.host.get(self.url).json['media_items'][0]['message'],self.guest.get(self.url).json['messages'][0]['id'])
  self.assertEqual(self.post(self.host,m['url'],method='DELETE').status_code,200);self.assertEqual(self.guest.get(m['url']).status_code,410)
 def test_file_content_dimensions_type_quota_and_upload_retry(self):
  path=self.chat();cid=path.rsplit('/',1)[1];self.assertEqual(self.upload(self.host,'dm',cid,b'<svg onload=alert(1)>').status_code,400)
  key=uuid.uuid4().hex;one=self.upload(self.host,'dm',cid,key=key);two=self.upload(self.host,'dm',cid,key=key);self.assertEqual(one.json['media']['id'],two.json['media']['id'])
  self.assertEqual(self.upload(self.host,'dm',cid,self.image(True),key).status_code,409)
  with self.host.session_transaction() as s:uid=s['uid']
  with app.app_context():db().execute('INSERT OR REPLACE INTO user_quotas VALUES(?,?)',(uid,1048576));db().execute('UPDATE chat_media SET bytes=1048576 WHERE id=?',(one.json['media']['id'],));db().commit()
  self.assertEqual(self.upload(self.host,'dm',cid).status_code,413)
 def test_sender_delete_and_inbox_hide_are_separate_and_paginated(self):
  path=self.chat();mid=self.send(path).json['message']['id'];self.assertEqual(self.post(self.guest,path+'/messages/'+str(mid),method='DELETE').status_code,403)
  self.assertEqual(self.post(self.host,path+'/messages/'+str(mid),method='DELETE').status_code,200);self.assertTrue(self.guest.get(path).json['messages'][0]['deleted'])
  self.post(self.host,path,method='DELETE');self.assertEqual(self.host.get('/api/me/conversations').json['conversations'],[]);self.assertEqual(len(self.guest.get('/api/me/conversations').json['conversations']),1)
  self.send(path,'New hello',c=self.guest);self.assertEqual(len(self.host.get('/api/me/conversations').json['conversations']),1)
  for i in range(52):self.send(path,str(i),c=self.guest)
  page=self.host.get(path).json;self.assertEqual(len(page['messages']),50);self.assertTrue(page['has_more']);older=self.host.get(path+'?before='+str(page['messages'][0]['id'])).json;self.assertTrue(older['messages']);self.assertLess(older['messages'][-1]['id'],page['messages'][0]['id'])
 def test_guest_upgrade_preserves_messages_profile_codes_and_attachments(self):
  path=self.chat();code=self.code(self.host);media=self.upload(self.host,'dm',path.rsplit('/',1)[1]).json['media'];self.send(path,media=media['id']);self.assertEqual(self.post(self.host,'/api/auth/signup',{'name':'Peach','email':'peach@example.test','password':'long unique password','accept_terms':True}).status_code,200)
  self.assertEqual(self.code(self.host),code);self.assertEqual(len(self.host.get(path).json['messages']),1);self.assertEqual(self.host.get(media['url']).status_code,200)
 def test_private_pages_no_index_no_cache_and_auth_csrf(self):
  for route in ['/messages','/settings','/friends','/rooms','/games']:
   r=self.host.get(route);self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['Cache-Control']);self.assertIn('noindex',r.headers['X-Robots-Tag']);self.assertNotIn(b'>Open Solace<',r.data)
  self.assertEqual(self.host.post('/api/me/conversations',json={'code':self.code(self.guest)}).status_code,403)
 def test_room_media_revision_omits_unchanged_payload_and_refreshes_removals(self):
  room=self.url.rsplit('/',1)[1];m=self.upload(self.host,'room',room).json['media'];self.post(self.host,'/api/me/room-media/'+room+'/send',{'body':'','media_id':m['id'],'request_id':uuid.uuid4().hex})
  first=self.host.get(self.url).json;small=self.host.get(self.url+'?after=0&media_after='+first['media_revision']).json;self.assertNotIn('media_items',small)
  self.post(self.host,m['url'],method='DELETE');changed=self.host.get(self.url+'?media_after='+first['media_revision']).json;self.assertTrue(changed['media_items'][0]['deleted'])
 def test_invalid_pixels_frames_and_unauthorized_room_uploads(self):
  path=self.chat();cid=path.rsplit('/',1)[1];raw=io.BytesIO();Image.new('RGB',(5000,4000),'black').save(raw,'PNG');self.assertEqual(self.upload(self.host,'dm',cid,raw.getvalue()).status_code,400)
  frames=[Image.new('RGB',(4,4),'red' if i%2 else 'blue') for i in range(181)];raw=io.BytesIO();frames[0].save(raw,'GIF',save_all=True,append_images=frames[1:],duration=100);self.assertEqual(self.upload(self.host,'dm',cid,raw.getvalue()).status_code,400)
  outsider=app.test_client();self.post(outsider,'/api/me/profile',{'name':'Outsider'});self.assertEqual(self.upload(outsider,'room',self.url.rsplit('/',1)[1]).status_code,403)
 def test_dm_content_never_enters_operations_archive(self):
  import sqlite3
  from contextlib import closing
  from pathlib import Path
  path=self.chat();secret='private-test-'+uuid.uuid4().hex;self.send(path,secret)
  with closing(sqlite3.connect(Path(app.instance_path)/'solace-admin.db')) as connection:self.assertNotIn(secret,'\n'.join(connection.iterdump()))
 def test_deleting_an_account_removes_its_private_text_and_media(self):
  path=self.chat();m=self.upload(self.host,'dm',path.rsplit('/',1)[1]).json['media'];self.send(path,'Remove my private text',media=m['id']);self.post(self.host,'/api/auth/signup',{'name':'Peach','email':'peach@example.test','password':'long unique password','accept_terms':True})
  self.assertEqual(self.post(self.host,'/api/me/delete-account',{'password':'long unique password'}).status_code,200)
  remaining=self.guest.get(path).json['messages'];self.assertTrue(remaining[0]['deleted']);self.assertEqual(remaining[0]['body'],'');self.assertEqual(self.guest.get(m['url']).status_code,410)
