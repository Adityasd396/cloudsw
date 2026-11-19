import unittest
from html.parser import HTMLParser
from app import app,db
import test_app

class Page(HTMLParser):
 def __init__(self,source):super().__init__();self.nodes=[];self.feed(source)
 def handle_starttag(self,tag,attrs):self.nodes.append((tag,dict(attrs)))
 def ids(self):return {a['id']:a for _,a in self.nodes if 'id' in a}
 def links(self,href):return [a for t,a in self.nodes if t=='a' and a.get('href')==href]

class NavigationPageTests(unittest.TestCase):
 setUp=test_app.WatchPartyTests.setUp
 tearDown=test_app.WatchPartyTests.tearDown
 def post(self,path,data):return self.host.post(path,json=data,headers={'X-CSRF-Token':self.host.get('/api/me').json['csrf']})
 def test_navigation_bridge_precedes_room_form_handlers(self):
  html=self.host.get('/create').text
  self.assertLess(html.index('/static/app-space.js'),html.index('/static/app.js'))
  self.assertLess(html.index('/static/app-space.js'),html.index('/static/rooms.js'))
 def test_home_friends_rooms_render_only_their_own_sections(self):
  self.post('/api/me/profile',dict(name='Peach'))
  home=Page(self.host.get('/home').text);friends=Page(self.host.get('/friends').text);rooms=Page(self.host.get('/rooms').text)
  self.assertIn('homeStats',home.ids());self.assertNotIn('connectForm',home.ids());self.assertNotIn('homeStats',friends.ids());self.assertIn('connectForm',friends.ids());self.assertNotIn('homeRooms',friends.ids());self.assertNotIn('homeStats',rooms.ids());self.assertNotIn('connectForm',rooms.ids());self.assertEqual(len(friends.links('/settings#privacy')),1)
 def test_guest_profile_has_one_room_return_and_no_irrelevant_actions(self):
  self.post('/api/me/profile',dict(name='Peach'));page=Page(self.host.get('/account').text)
  self.assertEqual(len([a for _,a in page.nodes if a.get('class')=='return-room']),1);self.assertNotIn('verifyEmail',page.ids());self.assertNotIn('signout',page.ids());self.assertIn('hidden',page.ids()['removePicture']);self.assertFalse(page.links('/account'));self.assertNotIn('Back to watching',self.host.get('/history').text)
 def test_verified_account_hides_verification_and_preserves_profile_data(self):
  self.post('/api/auth/signup',dict(name='Peach',email='navigation@example.test',password='Synthetic-Password-2026!',accept_terms=True))
  self.assertIn('verifyEmail',Page(self.host.get('/account').text).ids())
  with app.app_context():db().execute('UPDATE accounts SET verified=1 WHERE email=?',('navigation@example.test',));db().commit()
  page=Page(self.host.get('/account').text);self.assertNotIn('verifyEmail',page.ids());self.assertIn('signout',page.ids());self.assertIn('deleteAccountForm',page.ids());self.assertEqual(self.host.get('/api/me').json['profile']['name'],'Peach')
