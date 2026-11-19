"""Returning identities, private guest data and server-enforced room invitations."""
import io,time,unittest
from unittest.mock import patch
from PIL import Image
import test_app
from app import app,db

class SocialTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,c,path,data=None,method='POST',**kw):
  return c.open(path,method=method,json=data,headers={'X-CSRF-Token':c.get('/api/me').json['csrf']},**kw)
 def code(self,c):return c.get('/api/me/connections').json['friend_code']
 def connect(self):
  self.assertEqual(self.post(self.host,'/api/me/connections',{'action':'request','code':self.code(self.guest)}).status_code,200)
  self.assertEqual(self.post(self.guest,'/api/me/connections',{'action':'accept','code':self.code(self.host)}).status_code,200)
 def settings(self,c,**data):return self.post(c,self.url+'/settings',data)
 def test_saved_guest_home_profile_picture_and_upgrade_are_same_identity(self):
  self.assertEqual(self.host.get('/').location,'/home');self.assertEqual(self.host.get('/welcome').location,'/home')
  fresh=app.test_client();self.assertEqual(fresh.get('/home').location,'/welcome');self.assertEqual(fresh.get('/api/me/history').status_code,401)
  self.assertEqual(self.post(fresh,'/api/me/profile',{'name':'Fresh'}).status_code,200);self.assertEqual(fresh.get('/home').status_code,200)
  self.post(self.host,'/api/me/profile',{'name':'Peach'});picture=io.BytesIO();Image.new('RGB',(20,20),'pink').save(picture,'PNG');picture.seek(0)
  response=self.host.post('/api/me/avatar',data={'picture':(picture,'photo.png')},headers={'X-CSRF-Token':self.host.get('/api/me').json['csrf']});self.assertEqual(response.status_code,200)
  original=self.host.get('/api/me/avatar').data
  with self.host.session_transaction() as s:uid=s['uid']
  before=self.host.get('/api/me/history').json
  result=self.post(self.host,'/api/auth/signup',{'name':'Peach','email':'peach@example.test','password':'unique strong password','accept_terms':True});self.assertEqual(result.status_code,200)
  with self.host.session_transaction() as s:self.assertEqual(s['uid'],uid)
  self.assertEqual(self.host.get('/api/me/avatar').data,original);self.assertEqual(self.host.get('/api/me/history').json,before)
  self.assertEqual(self.guest.get('/api/me').json['profile']['avatar'],'/static/default-avatar.svg');self.assertEqual(self.guest.get('/api/me').json['profile']['name'],'Guest')
 def test_friends_are_explicit_and_sharing_opt_in_block_enforced(self):
  self.assertEqual(self.host.get('/api/me/connections').json['friends'],[]);self.connect()
  friend=self.guest.get('/api/me/connections').json['friends'][0];self.assertIsNone(friend['online']);self.assertIsNone(friend['stats']);self.assertNotIn('email',friend)
  self.post(self.host,'/api/me/privacy',{'share_presence':True,'share_stats':True});self.post(self.host,'/api/me/activity',{'active':True})
  friend=self.guest.get('/api/me/connections').json['friends'][0];self.assertTrue(friend['online']);self.assertEqual(friend['stats']['sessions'],0)
  self.host.post(self.url+'/presence',json={'active':False});self.post(self.host,'/api/me/activity',{'active':False});self.assertFalse(self.guest.get('/api/me/connections').json['friends'][0]['online'])
  self.post(self.host,'/api/me/connections',{'action':'block','code':self.code(self.guest)})
  self.assertEqual(self.guest.get(self.url).status_code,403);self.assertEqual(self.guest.post(self.url,json={'action':'join'}).status_code,403)
  self.assertEqual(self.guest.get('/api/me/connections').json['friends'],[])
 def test_visibility_discovery_capacity_and_host_permissions(self):
  s=self.host.get(self.url+'/settings').json;self.assertEqual(s['visibility'],'private');self.assertEqual(self.host.get('/api/public/rooms').json['rooms'],[])
  self.assertEqual(self.settings(self.guest,action='update',visibility='public',confirm_public=True).status_code,403)
  self.assertEqual(self.settings(self.host,action='update',visibility='public').status_code,400)
  self.assertEqual(self.settings(self.host,action='update',visibility='public',confirm_public=True,capacity=2).status_code,200)
  listing=self.guest.get('/api/public/rooms').json['rooms'][0];self.assertEqual(set(listing),{'public_id','name','label','capacity','participants'});self.assertNotIn(self.url.split('/')[-1],str(listing))
  extra=app.test_client();self.post(extra,'/api/me/profile',{'name':'Extra'});self.assertEqual(extra.post(self.url,json={'action':'join'}).status_code,409)
  self.settings(self.host,action='update',visibility='private');self.assertEqual(self.guest.get(self.url).status_code,200);self.assertEqual(extra.get('/api/public/rooms').json['rooms'],[])
 def test_invite_link_destination_survives_setup_and_revocation(self):
  link=self.host.get(self.url+'/settings').json['invite_link'];token=link.split('token=')[1];fresh=app.test_client()
  self.assertEqual(self.post(fresh,'/api/me/invites/link',{'token':token}).json['next'],'/welcome')
  self.assertEqual(self.post(fresh,'/api/me/profile',{'name':'New friend'}).json['next'],'/join?room='+self.url.split('/')[-1])
  self.settings(self.host,action='revoke');self.assertEqual(fresh.post(self.url,json={'action':'join'}).status_code,410);self.assertEqual(self.post(fresh,'/api/me/invites/link',{'token':token}).status_code,410)
  self.assertEqual(self.guest.get(self.url).status_code,200)
  new=self.settings(self.host,action='regenerate').json['invite_link'];self.assertNotEqual(new,link)
 def test_friend_invitations_target_only_duplicates_expiry_and_decline(self):
  self.connect();body={'action':'send','room':self.url.split('/')[-1],'code':self.code(self.guest)}
  # Leave first so an actual invitation is needed.
  self.guest.post(self.url+'/leave',json={})
  self.assertEqual(self.post(self.host,'/api/me/invitations',body).status_code,200);self.assertEqual(self.post(self.host,'/api/me/invitations',body).status_code,409)
  invite=self.guest.get('/api/me/invitations').json['invitations'][0];self.assertEqual(self.post(self.host,'/api/me/invitations',{'action':'accept','id':invite['id']}).status_code,404)
  self.assertEqual(self.post(self.guest,'/api/me/invitations',{'action':'decline','id':invite['id']}).status_code,200);self.assertEqual(self.guest.get('/api/me/invitations').json['invitations'][0]['status'],'declined')
  self.post(self.host,'/api/me/invitations',body);invite=self.guest.get('/api/me/invitations').json['invitations'][0]
  self.assertEqual(self.post(self.guest,'/api/me/invitations',{'action':'accept','id':invite['id']}).status_code,200);self.assertEqual(self.guest.post(self.url,json={'action':'join'}).status_code,200)
 def test_settings_and_private_pages_no_cache_guest_csrf(self):
  for path in ['/home','/account','/history','/room-control?room='+self.url.split('/')[-1]]:
   r=self.host.get(path);self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['Cache-Control']);self.assertIn('noindex',r.headers['X-Robots-Tag'])
  self.assertEqual(self.host.post(self.url+'/settings',json={'action':'revoke'}).status_code,403)
  self.assertEqual(self.host.post('/api/me/profile',json={'name':'bad'}).status_code,403)
 def test_native_identity_handoff_is_one_use_short_lived_and_preserves_authority(self):
  native=app.test_client();token=self.post(self.host,'/api/me/native-handoff',{}).json['token']
  self.assertEqual(native.post('/api/native/handoff',json={'token':token}).status_code,200)
  self.assertEqual(native.get('/api/me').json['profile']['name'],'Host');self.assertEqual(native.get(self.url).status_code,200)
  self.assertEqual(app.test_client().post('/api/native/handoff',json={'token':token}).status_code,401)
  token=self.post(self.host,'/api/me/native-handoff',{}).json['token']
  with app.app_context():db().execute('UPDATE native_handoffs SET expires=0');db().commit()
  self.assertEqual(app.test_client().post('/api/native/handoff',json={'token':token}).status_code,401)
  self.post(self.host,'/api/auth/signup',{'name':'Host','email':'host@example.test','password':'unique strong password','accept_terms':True})
  token=self.post(self.host,'/api/me/native-handoff',{}).json['token'];self.assertEqual(native.post('/api/native/handoff',json={'token':token}).status_code,200)
  self.assertFalse(native.get('/api/me').json['guest']);self.assertFalse(self.host.get('/api/me').json['guest'])
 def test_expired_account_session_never_exposes_previous_history_or_avatar(self):
  self.post(self.host,'/api/auth/signup',{'name':'Host','email':'host@example.test','password':'unique strong password','accept_terms':True})
  with app.app_context():db().execute('UPDATE account_sessions SET expires=0');db().commit()
  self.assertIsNone(self.host.get('/api/me').json['profile']);self.assertEqual(self.host.get('/home').location,'/welcome');self.assertEqual(self.host.get('/api/me/history').status_code,401)
  self.assertIn(b'previous session ended',self.host.get('/welcome').data)
 def test_guest_handoff_replaces_old_native_account_cookie(self):
  native=app.test_client();self.post(native,'/api/auth/signup',{'name':'Old account','email':'old@example.test','password':'unique strong password','accept_terms':True});self.assertFalse(native.get('/api/me').json['guest'])
  token=self.post(self.host,'/api/me/native-handoff',{}).json['token'];self.assertEqual(native.post('/api/native/handoff',json={'token':token}).status_code,200)
  me=native.get('/api/me').json;self.assertTrue(me['guest']);self.assertEqual(me['profile']['name'],'Host');self.assertIsNone(native.get_cookie('solace_account'))
 def test_bad_social_inputs_and_repeated_requests_do_not_break_state(self):
  self.assertEqual(self.post(self.host,'/api/me/connections',{'action':'request','code':{'bad':1}}).status_code,400)
  self.assertEqual(self.post(self.host,self.url+'/settings',{'action':'update','name':['bad']}).status_code,400)
  self.assertEqual(self.host.get(self.url).status_code,200)
 def test_public_create_confirmation_rolls_back_and_bans_can_be_lifted(self):
  with app.app_context():before=db().execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
  self.assertEqual(self.host.post('/api/rooms',json={'visibility':'public'}).status_code,400)
  with app.app_context():self.assertEqual(db().execute('SELECT COUNT(*) FROM rooms').fetchone()[0],before)
  peer=next(p for p in self.host.get(self.url+'/settings').json['participants'] if not p['you'])
  self.assertEqual(self.post(self.guest,self.url+'/moderation',{'action':'ban','member_id':peer['member_id']}).status_code,403)
  self.assertEqual(self.post(self.host,self.url+'/moderation',{'action':'ban','member_id':peer['member_id']}).status_code,200)
  self.assertEqual(self.guest.post(self.url,json={'action':'join'}).status_code,403)
  self.assertEqual(self.post(self.host,self.url+'/moderation',{'action':'unban','member_id':peer['member_id']}).status_code,200)
  self.assertEqual(self.guest.post(self.url,json={'action':'join'}).status_code,200)
 def test_expired_or_closed_invitation_cannot_join(self):
  self.connect();self.guest.post(self.url+'/leave',json={});body={'action':'send','room':self.url.split('/')[-1],'code':self.code(self.guest)};self.post(self.host,'/api/me/invitations',body)
  invitation=self.guest.get('/api/me/invitations').json['invitations'][0]
  with app.app_context():db().execute('UPDATE room_invitations SET expires=0');db().commit()
  self.assertEqual(self.post(self.guest,'/api/me/invitations',{'action':'accept','id':invitation['id']}).status_code,410)
  self.post(self.host,'/api/me/invitations',body);invitation=self.guest.get('/api/me/invitations').json['invitations'][0];self.host.post(self.url+'/leave',json={})
  self.assertIn(self.post(self.guest,'/api/me/invitations',{'action':'accept','id':invitation['id']}).status_code,(404,410))
